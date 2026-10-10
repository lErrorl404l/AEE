#!/usr/bin/env python3
"""Aircraft coverage guard tests (aircraft corpus, wave 4 task 16).

The coverage logic lives in the production generator
``tools/validation/gen_aircraft_coverage.py``. This module imports it. The
tests cover the build, the guard and the generated artefacts.

The guard gives every air token in ``data/vehicle/classes.json`` one state.
The states are ``recorded``, ``lead``, ``no_source`` and
``excluded_non_ground``. A non-air token is ``excluded_non_ground``. An air
token is ``recorded`` only when a runtime row is emitted and a class binding
holds it. No token leaves the inventory in silence.

The committed ``coverage.json`` must match a fresh build, so the rows are
derived, not hand-maintained.

Run: python3 -m unittest tools.tests.test_aircraft_coverage -v
     python3 tools/tests/test_aircraft_coverage.py --report
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from typing import cast

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools import schemas  # noqa: E402
from tools.validation import gen_aircraft_coverage as g  # noqa: E402

DATA = REPO / "data" / "aircraft"

JsonObject = dict[str, object]


def _as_sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"expected an array, got {type(value).__name__}")
    return list(cast("list[object]", value))


def _entries(payload: JsonObject) -> list[JsonObject]:
    return g.entries(payload)


def _live_rows(payload: JsonObject) -> list[JsonObject]:
    """Return the token rows without copying them, for in-place edits."""
    rows: list[JsonObject] = []
    for item in _as_sequence(payload.get("tokens")):
        if not isinstance(item, dict):
            raise TypeError("coverage row must be an object")
        rows.append(cast("JsonObject", item))
    return rows


def _row(coverage: JsonObject, token: str) -> JsonObject:
    for row in _live_rows(coverage):
        if row.get("class") == token:
            return row
    raise AssertionError(f"no coverage row for {token}")


def _token(token: str, is_air: bool, reason: str = "fixture reason") -> JsonObject:
    return {
        "class": token,
        "kind": "engine_base",
        "is_ground": False,
        "exclusion_reason": reason,
    }


def _classes(*tokens: JsonObject) -> JsonObject:
    return {"schema": schemas.VEHICLE_CLASS_INVENTORY, "tokens": list(tokens)}


class CoverageBuildTest(unittest.TestCase):
    def test_an_air_token_without_a_record_is_no_source(self) -> None:
        payload = g.build_coverage(_classes(_token("Plane", True)), {})
        row = _row(payload, "Plane")
        self.assertEqual(g.AIR_ABSENT_STATE, row["state"])
        self.assertIsNone(row["variant"])
        self.assertTrue(row["reason"])

    def test_an_air_token_with_one_record_is_recorded(self) -> None:
        payload = g.build_coverage(_classes(_token("Plane", True)), {"Plane": {"a10a"}})
        row = _row(payload, "Plane")
        self.assertEqual("recorded", row["state"])
        self.assertEqual("a10a", row["variant"])

    def test_a_non_air_token_is_excluded(self) -> None:
        payload = g.build_coverage(_classes(_token("Tank", False, "ground token")), {})
        row = _row(payload, "Tank")
        self.assertEqual(g.NON_AIR_STATE, row["state"])
        self.assertEqual("ground token", row["reason"])

    def test_build_keeps_every_token(self) -> None:
        classes = _classes(_token("Plane", True), _token("Tank", False))
        self.assertEqual(len(_entries(g.build_coverage(classes, {}))), 2)

    def test_a_researched_lead_is_carried_with_its_reason(self) -> None:
        payload = g.build_coverage(
            _classes(_token("Plane", True)), {}, {"Plane": "researched lead"}
        )
        row = _row(payload, "Plane")
        self.assertEqual("lead", row["state"])
        self.assertEqual("researched lead", row["reason"])


class CoverageGuardTest(unittest.TestCase):
    def _classes_and_coverage(self) -> tuple[JsonObject, JsonObject]:
        classes = _classes(_token("Plane", True), _token("Tank", False, "ground row"))
        return classes, g.build_coverage(classes, {})

    def test_a_clean_table_has_no_errors(self) -> None:
        classes, coverage = self._classes_and_coverage()
        self.assertEqual([], g.coverage_errors(classes, coverage, {}))

    def test_a_dropped_token_is_reported_by_name(self) -> None:
        classes, coverage = self._classes_and_coverage()
        coverage["tokens"] = [
            row for row in _entries(coverage) if row.get("class") != "Plane"
        ]
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any("coverage token Plane: no entry" in error for error in errors), errors
        )

    def test_a_recorded_token_needs_an_emitted_row_and_a_binding(self) -> None:
        classes, coverage = self._classes_and_coverage()
        _row(coverage, "Plane")["state"] = "recorded"
        _row(coverage, "Plane")["variant"] = "a10a"
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any("recorded without an emitted row and binding" in e for e in errors),
            errors,
        )

    def test_a_no_source_token_needs_a_reason(self) -> None:
        classes, coverage = self._classes_and_coverage()
        _row(coverage, "Plane")["reason"] = None
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any("no_source token needs a reason" in error for error in errors), errors
        )

    def test_a_state_that_hides_a_recorded_row_is_reported(self) -> None:
        classes, coverage = self._classes_and_coverage()
        errors = g.coverage_errors(classes, coverage, {"Plane": {"a10a"}})
        self.assertTrue(
            any("hides a recorded row" in error for error in errors), errors
        )

    def test_a_non_air_token_must_be_excluded(self) -> None:
        classes, coverage = self._classes_and_coverage()
        _row(coverage, "Tank")["state"] = g.AIR_ABSENT_STATE
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any("non-air token must be" in error for error in errors), errors
        )

    def test_an_unknown_state_is_reported(self) -> None:
        classes, coverage = self._classes_and_coverage()
        _row(coverage, "Plane")["state"] = "maybe"
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(any("state 'maybe'" in error for error in errors), errors)


class RealCorpusCoverageTest(unittest.TestCase):
    classes: JsonObject = {}
    recorded: dict[str, set[str]] = {}
    coverage: JsonObject = {}

    def setUp(self) -> None:
        self.classes = g.load_classes()
        self.recorded = g.recorded_variants(g.load_catalogue(DATA))
        self.coverage = g.load_coverage(DATA)

    def test_every_air_token_has_one_coverage_row(self) -> None:
        rows = _entries(self.coverage)
        tokens = [str(row.get("class")) for row in rows]
        self.assertEqual(len(tokens), len(set(tokens)), "duplicate coverage token")
        for token in g.AIR_TOKENS:
            self.assertEqual(
                1, tokens.count(token), f"coverage.json must hold {token} once"
            )

    def test_the_air_rows_are_exactly_the_four_tokens(self) -> None:
        air = {
            str(row.get("class"))
            for row in _entries(self.coverage)
            if row.get("is_air")
        }
        self.assertEqual(set(g.AIR_TOKENS), air)

    def test_a_recorded_token_has_an_emitted_row_and_a_binding(self) -> None:
        emitted = set(g.emitted_rows(g.load_catalogue(DATA)).values())
        for row in _entries(self.coverage):
            if row.get("state") != "recorded":
                continue
            token = str(row.get("class"))
            variants = self.recorded.get(token, set())
            self.assertTrue(variants, f"{token} is recorded without a binding")
            for variant in variants:
                self.assertIn(variant, emitted, f"{token}/{variant}")

    def test_a_no_source_token_carries_a_reason(self) -> None:
        for row in _entries(self.coverage):
            if row.get("state") != g.AIR_ABSENT_STATE:
                continue
            self.assertTrue(row.get("reason"), row.get("class"))

    def test_plane_and_helicopter_are_recorded(self) -> None:
        rows = {row.get("class"): row for row in _entries(self.coverage)}
        for token in ("Plane", "Helicopter"):
            self.assertEqual("recorded", rows[token]["state"], token)

    def test_every_inventory_token_is_covered(self) -> None:
        self.assertEqual(len(_entries(self.classes)), len(_entries(self.coverage)))

    def test_the_committed_table_matches_a_fresh_build(self) -> None:
        roster = g.load_roster(DATA)
        class_recorded = g.recorded_classes(g.load_catalogue(DATA))
        self.assertEqual(
            g.build_coverage(
                self.classes,
                self.recorded,
                g.LEAD_CANDIDATES,
                roster,
                class_recorded,
            ),
            self.coverage,
        )

    def test_every_roster_class_has_a_coverage_entry_keyed_by_class(self) -> None:
        roster = g.load_roster(DATA)
        keyed = {
            str(row.get("class"))
            for row in _as_sequence(self.coverage.get("classes"))
            if isinstance(row, dict)
        }
        missing = [
            str(entry.get("game_class"))
            for entry in roster
            if entry.get("game_class") not in keyed
        ]
        self.assertEqual([], missing, f"coverage.json drops {missing}")

    def test_every_air_token_state_is_known(self) -> None:
        for row in _entries(self.coverage):
            if row.get("is_air") is not True:
                continue
            self.assertIn(row.get("state"), g.COVERAGE_STATES, row.get("class"))


class CoverageCheckModeTest(unittest.TestCase):
    """`--check` proves freshness and writes nothing."""

    def _copy_corpus(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        data = tmp / "aircraft"
        data.mkdir()
        for name in (
            "sources.json",
            "class_map.json",
            "class_bindings.json",
            "roster.json",
        ):
            shutil.copy(DATA / name, data / name)
        shutil.copytree(DATA / "catalogue", data / "catalogue")
        return data

    def test_a_fresh_write_passes_the_check(self) -> None:
        data = self._copy_corpus()
        g.write_all(data)
        self.assertEqual(0, g.check_all(data))

    def test_check_writes_nothing(self) -> None:
        data = self._copy_corpus()
        self.assertEqual(1, g.check_all(data))
        for name in g.ARTEFACTS:
            self.assertFalse((data / name).exists(), name)

    def test_a_missing_output_is_reported(self) -> None:
        data = self._copy_corpus()
        g.write_all(data)
        (data / g.SOURCE_GAPS_REPORT).unlink()
        self.assertEqual(1, g.check_all(data))

    def test_a_stale_output_is_reported(self) -> None:
        data = self._copy_corpus()
        g.write_all(data)
        path = data / g.COVERAGE_OUT
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assertEqual(1, g.check_all(data))

    def test_a_removed_binding_breaks_the_recorded_row(self) -> None:
        # Remove every binding for one token: the token loses its recorded
        # row, so the committed table no longer matches a fresh build, and
        # the guard reports the recorded token without a binding.
        data = self._copy_corpus()
        g.write_all(data)
        committed = g.load_coverage(data)
        path = data / "class_bindings.json"
        bindings = cast(
            "list[JsonObject]", json.loads(path.read_text(encoding="utf-8"))
        )
        token = str(bindings[0].get("class_token"))
        kept = [b for b in bindings if b.get("class_token") != token]
        self.assertLess(len(kept), len(bindings))
        path.write_text(json.dumps(kept), encoding="utf-8")

        reduced = g.recorded_variants(g.load_catalogue(data))
        self.assertNotIn(token, reduced)
        errors = g.coverage_errors(g.load_classes(), committed, reduced)
        self.assertTrue(
            any(token in error and "recorded" in error for error in errors), errors
        )
        self.assertEqual(1, g.check_all(data))

    def test_a_written_table_matches_the_committed_table(self) -> None:
        data = self._copy_corpus()
        g.write_all(data)
        self.assertEqual(
            (DATA / g.COVERAGE_OUT).read_text(encoding="utf-8"),
            (data / g.COVERAGE_OUT).read_text(encoding="utf-8"),
        )


def report(data_dir: Path = DATA) -> int:
    """Print the coverage counts and the guard result."""
    classes = g.load_classes()
    coverage = g.load_coverage(data_dir)
    recorded = g.recorded_variants(g.load_catalogue(data_dir))
    errors = g.coverage_errors(classes, coverage, recorded)

    rows = _entries(coverage)
    counts: Counter[str] = Counter()
    for row in rows:
        state = row.get("state")
        if isinstance(state, str):
            counts[state] += 1
    print(f"coverage: {len(rows)} tokens")
    for state in g.COVERAGE_STATES:
        print(f"  {state}: {counts.get(state, 0)}")
    if errors:
        print("coverage guard: FAIL")
        for error in errors:
            print(f"  {error}")
        return 1
    print("coverage guard: PASS")
    return 0


if __name__ == "__main__":
    if "--report" in sys.argv:
        sys.exit(report())
    _ = unittest.main()
