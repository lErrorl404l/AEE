#!/usr/bin/env python3
"""Engine mass calibration gate tests.

The census tool pairs the in-engine mass census with the held real masses,
and the validator is the gate on the artefact. These tests prove the tool
fails closed when the census is absent or incomplete, that it writes the
calibration when the census is complete, and that the validator accepts a
clean artefact and rejects a tampered one.

Run: python3 -m unittest tools.tests.test_mass_calibration -v
"""

from __future__ import annotations

import copy
import json
import statistics
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import build_mass_calibration as build  # noqa: E402
from tools.validation import validate_mass_calibration as v  # noqa: E402

BINDINGS = REPO / "data" / "vehicle" / "class_bindings.json"
CALIBRATION = REPO / "data" / "vehicle" / "mass_model_calibration.json"


def _classes() -> list[str]:
    return build.bound_classes(BINDINGS)


def _sample_log(classes: list[str], drop: str | None = None) -> str:
    """Return a census log with a distinct live mass per class."""
    lines = []
    for index, name in enumerate(classes):
        if name == drop:
            continue
        config = 1000.0 + index
        live = 2000.0 + (index * 10)
        lines.append(f"[P72] MASS {name} config={config} live={live}")
    lines.append("[P72] [PASS] engine mass census")
    return "\n".join(lines) + "\n"


class BuildMassCalibrationTest(unittest.TestCase):
    """The tool fails closed on a bad census and writes on a good one."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.classes = _classes()
        cls.held = build.held_masses(CALIBRATION)

    def _run(self, log_text: str | None, tmp: str) -> tuple[int, Path]:
        out = Path(tmp) / "mass_calibration.json"
        argv = [
            "--log",
            str(Path(tmp) / "run.log"),
            "--bindings",
            str(BINDINGS),
            "--calibration",
            str(CALIBRATION),
            "--out",
            str(out),
        ]
        if log_text is not None:
            (Path(tmp) / "run.log").write_text(log_text, encoding="utf-8")
        return build.main(argv), out

    def test_no_log_fails_closed_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = self._run(None, tmp)
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())

    def test_a_complete_log_writes_the_artefact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = self._run(_sample_log(self.classes), tmp)
            self.assertEqual(rc, 0)
            self.assertTrue(out.exists())
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], build.SCHEMA)
            self.assertFalse(payload["approved"])
            self.assertEqual(len(payload["rows"]), len(self.classes))
            self.assertEqual(payload["counts"]["paired"], len(self.classes))

    def test_the_fit_is_the_median_row_scale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = self._run(_sample_log(self.classes), tmp)
            self.assertEqual(rc, 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            scales = [row["scale"] for row in payload["rows"]]
            self.assertAlmostEqual(
                payload["fit"]["scale"],
                round(statistics.median(scales), build.SCALE_ROUND),
                places=build.SCALE_ROUND,
            )
            self.assertEqual(payload["leave_one_out"]["n"], len(self.classes))

    def test_a_missing_class_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = self._run(_sample_log(self.classes, drop=self.classes[0]), tmp)
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())

    def test_a_non_numeric_live_mass_fails_closed(self) -> None:
        log = _sample_log(self.classes).replace(f"live={2000.0}", "live=FAIL", 1)
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = self._run(log, tmp)
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())

    def test_the_committed_census_pairs_every_bound_class(self) -> None:
        readings = {}
        for index, name in enumerate(self.classes):
            readings[name] = (1000.0 + index, 2000.0 + index)
        rows = build.build_rows(self.classes, readings, self.held)
        self.assertEqual([row["game_class"] for row in rows], self.classes)


class ValidateMassCalibrationTest(unittest.TestCase):
    """The validator accepts a clean artefact and rejects a tampered one."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.classes = _classes()

    def _written(self, tmp: str) -> Path:
        log = Path(tmp) / "run.log"
        log.write_text(_sample_log(self.classes), encoding="utf-8")
        out = Path(tmp) / "mass_calibration.json"
        rc = build.main(
            [
                "--log",
                str(log),
                "--bindings",
                str(BINDINGS),
                "--calibration",
                str(CALIBRATION),
                "--out",
                str(out),
            ]
        )
        self.assertEqual(rc, 0)
        return out

    def test_a_written_artefact_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._written(tmp)
            payload = v.load_artefact(out)
            self.assertEqual(v.validate_artefact(payload, self.classes), [])

    def test_the_cli_accepts_a_written_artefact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._written(tmp)
            self.assertEqual(
                v.main(["--path", str(out), "--bindings", str(BINDINGS)]), 0
            )

    def test_an_absent_artefact_is_a_legal_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(v.main(["--path", str(Path(tmp) / "missing.json")]), 0)

    def test_a_tampered_scale_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._written(tmp)
            payload = v.load_artefact(out)
            tampered = copy.deepcopy(payload)
            tampered["rows"][0]["scale"] = 99.0
            errors = v.validate_artefact(tampered, self.classes)
            self.assertTrue(
                any("does not reproduce" in error for error in errors), errors
            )

    def test_a_flipped_approval_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._written(tmp)
            payload = v.load_artefact(out)
            flipped = copy.deepcopy(payload)
            flipped["approved"] = True
            errors = v.validate_artefact(flipped, self.classes)
            self.assertTrue(
                any("without an approval" in error for error in errors), errors
            )

    def test_a_missing_row_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._written(tmp)
            payload = v.load_artefact(out)
            short = copy.deepcopy(payload)
            short["rows"].pop()
            short["leave_one_out"]["n"] = len(short["rows"])
            errors = v.validate_artefact(short, self.classes)
            self.assertTrue(any("miss bound class" in e for e in errors), errors)

    def test_the_self_check_passes(self) -> None:
        self.assertEqual(v.main(["--self-check"]), 0)


if __name__ == "__main__":
    unittest.main()
