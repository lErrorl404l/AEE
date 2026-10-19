#!/usr/bin/env python3
"""Matcher coverage split: base content against modded content.

The matcher coverage tool reports one combined number, and a combined
number cannot be held to a target: losing a base class and gaining two
modded ones reads as an improvement. The operator's target is that every
MODDED class resolves in every AEE matcher, so the measurement is split by
the PBO that declares the class - `<install>/Addons/*.pbo` is the base game
and every other source is modded - and the modded number is locked here.

The lock is three assertions in one:
  * the split itself, on a synthetic install: a base PBO class is base, a
    workshop PBO class is modded, and a mod class that inherits a base
    class is still modded;
  * the baseline artefact is present, shaped, and self-consistent with the
    gap files it ships beside it;
  * the tool reproduces the baseline from the scan, table by table, when
    the scan is present. A machine without the scan skips that one
    assertion by name, and never passes it in silence.

No test asserts 100% modded coverage. That is the target the closing work
moves toward, not a state the repository is in.

Run: python3 -m unittest tools.tests.test_match_coverage -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools import report_match_coverage as m  # noqa: E402

COVERAGE = REPO / "data" / "coverage"
BASELINE = COVERAGE / "modded_baseline.json"
SCHEMA = "aee.match_coverage.baseline/1"
TABLES = {
    "vehicles",
    "aircraft",
    "small_arms",
    "carried_launchers",
    "vehicle_armament",
}


def row(source: str, cls: str, display: str, parent: str = "") -> dict:
    return {
        "source": source,
        "kind": "CfgVehicles",
        "class": cls,
        "display": display,
        "parent": parent,
        "fmt": "bin",
        "feeds": False,
        "magazines": [],
        "ammo": "",
        "damage": 0.0,
    }


def always(match: bool):
    return lambda _identity: match


class TestSplit(unittest.TestCase):
    """Who declares a class decides which half of the measurement holds it."""

    BASE = {"base_vehicles.pbo"}

    def test_a_base_pbo_class_is_base(self):
        rows = [row("base_vehicles.pbo", "B_MBT_01_cannon_F", "M2A1 Slammer")]
        res = m.score(rows, always(True), self.BASE)
        self.assertEqual(res["base"], {"hit": 1, "total": 1})
        self.assertEqual(res["modded"], {"hit": 0, "total": 0})

    def test_a_workshop_pbo_class_is_modded(self):
        rows = [row("some_mod_vehicles.pbo", "mod_tank_x", "Mod Tank X")]
        res = m.score(rows, always(True), self.BASE)
        self.assertEqual(res["base"], {"hit": 0, "total": 0})
        self.assertEqual(res["modded"], {"hit": 1, "total": 1})

    def test_case_is_folded_on_both_sides(self):
        # A scan may carry the PBO name as the file system spells it.
        rows = [row("Base_Vehicles.PBO", "B_MBT_01_cannon_F", "M2A1 Slammer")]
        res = m.score(rows, always(True), self.BASE)
        self.assertEqual(res["base"]["total"], 1)

    def test_a_mod_class_inheriting_a_base_class_is_modded(self):
        rows = [
            row(
                "some_mod_vehicles.pbo",
                "mod_tank_x",
                "Mod Tank X",
                parent="B_MBT_01_cannon_F",
            )
        ]
        res = m.score(rows, always(False), self.BASE)
        self.assertEqual(res["modded"]["total"], 1)
        self.assertEqual(len(m.modded_gaps(res)), 1)

    def test_an_unresolved_class_carries_the_four_facts(self):
        rows = [row("some_mod_vehicles.pbo", "mod_tank_x", "Mod Tank X", "Car")]
        res = m.score(rows, always(False), self.BASE)
        self.assertEqual(
            res["unresolved"],
            [
                {
                    "group": "modded",
                    "class": "mod_tank_x",
                    "display": "Mod Tank X",
                    "parent": "Car",
                    "source": "some_mod_vehicles.pbo",
                }
            ],
        )

    def test_modded_gaps_excludes_the_base_half(self):
        rows = [
            row("base_vehicles.pbo", "B_Truck_01_F", "HEMTT"),
            row("some_mod_vehicles.pbo", "mod_tank_x", "Mod Tank X"),
        ]
        res = m.score(rows, always(False), self.BASE)
        gaps = m.modded_gaps(res)
        self.assertEqual([g["class"] for g in gaps], ["mod_tank_x"])

    def test_a_resolved_class_is_not_a_gap(self):
        rows = [row("some_mod_vehicles.pbo", "mod_tank_x", "Mod Tank X")]
        res = m.score(rows, always(True), self.BASE)
        self.assertEqual(res["unresolved"], [])


class TestInstallSplit(unittest.TestCase):
    """The base game is `<install>/Addons`, and its absence is loud."""

    def test_base_sources_reads_the_addons_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            addons = Path(tmp) / "Addons"
            addons.mkdir()
            (addons / "armor_f.pbo").write_bytes(b"")
            (addons / "air_f.pbo").write_bytes(b"")
            # Not a PBO: the directory also holds the extracted directory and
            # the signature beside every PBO.
            (addons / "armor_f.pbo.a3.bisign").write_bytes(b"")
            got = m.base_sources(Path(tmp))
        self.assertEqual(got, {"armor_f.pbo", "air_f.pbo"})

    def test_a_missing_addons_directory_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as caught:
                m.install_dir(tmp)
            self.assertIn("Addons", str(caught.exception))

    def test_an_empty_addons_directory_fails_loudly(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Addons").mkdir()
            with self.assertRaises(SystemExit) as caught:
                m.base_sources(Path(tmp))
            self.assertIn("no *.pbo", str(caught.exception))

    def test_the_environment_names_the_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Addons").mkdir()
            (Path(tmp) / "Addons" / "armor_f.pbo").write_bytes(b"")
            old = os.environ.get(m.INSTALL_ENV)
            os.environ[m.INSTALL_ENV] = tmp
            try:
                self.assertEqual(m.install_dir(None), Path(tmp))
            finally:
                if old is None:
                    del os.environ[m.INSTALL_ENV]
                else:
                    os.environ[m.INSTALL_ENV] = old


class TestBaselineArtefact(unittest.TestCase):
    """The committed baseline is the number the closing work is measured against."""

    @classmethod
    def setUpClass(cls):
        if not BASELINE.is_file():
            raise unittest.SkipTest(f"no baseline artefact at {BASELINE}")
        cls.payload = json.loads(BASELINE.read_text(encoding="utf-8"))

    def test_the_baseline_is_present_with_its_schema(self):
        self.assertEqual(self.payload["schema"], SCHEMA)

    def test_the_provenance_names_the_scan_the_date_the_install_and_the_pbos(self):
        prov = self.payload["provenance"]
        for key in (
            "generated",
            "scan",
            "scan_sha256",
            "scan_rows",
            "measured_rows",
            "install",
            "base_addons",
            "base_pbo_count",
            "base_pbos",
            "method",
        ):
            self.assertIn(key, prov)
        self.assertEqual(len(prov["scan_sha256"]), 64)
        self.assertGreater(prov["measured_rows"], 0)
        self.assertLessEqual(prov["measured_rows"], prov["scan_rows"])
        # The base PBO list is the split, checked in, so a reader without the
        # install can still tell which source is base.
        self.assertEqual(prov["base_pbo_count"], len(prov["base_pbos"]))
        self.assertGreater(prov["base_pbo_count"], 0)
        self.assertEqual(prov["base_pbos"], sorted(set(prov["base_pbos"])))
        self.assertEqual(prov["base_addons"], str(Path(prov["install"]) / "Addons"))

    def test_every_matcher_table_is_measured(self):
        self.assertEqual(set(self.payload["tables"]), TABLES)

    def test_each_table_reports_base_and_modded_with_its_counts(self):
        for name, table in self.payload["tables"].items():
            with self.subTest(table=name):
                for half in ("base", "modded"):
                    counts = table[half]
                    self.assertIn("hit", counts)
                    self.assertIn("total", counts)
                    self.assertLessEqual(counts["hit"], counts["total"])
                    self.assertGreater(counts["total"], 0)
                    expected = round(100.0 * counts["hit"] / counts["total"], 2)
                    self.assertAlmostEqual(counts["pct"], expected, places=6)
                self.assertEqual(
                    table["unresolved_modded"],
                    table["modded"]["total"] - table["modded"]["hit"],
                )

    def test_the_baseline_is_not_a_claim_of_full_coverage(self):
        # The lock must not read as "the target is met": the closing workers
        # have not run, so at least one table still holds a modded gap.
        gaps = sum(t["unresolved_modded"] for t in self.payload["tables"].values())
        self.assertGreater(gaps, 0)

    def test_the_gap_files_agree_with_the_baseline(self):
        base_pbos = set(self.payload["provenance"]["base_pbos"])
        for name, table in self.payload["tables"].items():
            with self.subTest(table=name):
                path = COVERAGE / f"modded_gaps_{name}.txt"
                self.assertTrue(path.is_file(), f"no gap list at {path}")
                body = path.read_text(encoding="utf-8").splitlines()
                header = [line for line in body if line.startswith("#")]
                rows = [line for line in body if not line.startswith("#")]
                self.assertEqual(
                    header[0], f"# modded match coverage gaps: {table['label']}"
                )
                self.assertEqual(header[2], "# class\tdisplay\tparent\tsource")
                self.assertEqual(len(rows), table["unresolved_modded"])
                self.assertIn(str(table["unresolved_modded"]), header[1])
                for line in rows:
                    fields = line.split("\t")
                    self.assertEqual(len(fields), 4, line)
                    cls, display, parent, source = fields
                    self.assertTrue(cls)
                    self.assertTrue(display)
                    self.assertTrue(parent)
                    # A gap list of modded classes must not name a base PBO.
                    self.assertNotIn(source.lower(), base_pbos)

    def test_the_gap_files_are_the_only_gap_lists_shipped(self):
        found = sorted(p.name for p in COVERAGE.glob("modded_gaps_*.txt"))
        self.assertEqual(found, sorted(f"modded_gaps_{n}.txt" for n in TABLES))


class TestBaselineReproduces(unittest.TestCase):
    """The tool's numbers are the artefact's numbers, or the artefact is stale."""

    @classmethod
    def setUpClass(cls):
        if not BASELINE.is_file():
            raise unittest.SkipTest(f"no baseline artefact at {BASELINE}")
        cls.payload = json.loads(BASELINE.read_text(encoding="utf-8"))
        cls.scan = Path(
            os.environ.get("AEE_COVERAGE_SCAN") or cls.payload["provenance"]["scan"]
        )
        if not cls.scan.is_file():
            raise unittest.SkipTest(
                f"no scan at {cls.scan}: re-scan with tools/scan_game_classes.py, "
                "or set AEE_COVERAGE_SCAN to a scan, to re-derive the baseline"
            )
        cls.tables = cls.measure(cls.scan)

    @classmethod
    def measure(cls, scan: Path) -> dict:
        raw = [
            json.loads(line)
            for line in scan.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        scanned = [r for r in raw if r.get("fmt") == "bin"]
        # The split comes from the install when it is there, and from the
        # baseline's own base PBO list when it is not.
        install = Path(cls.payload["provenance"]["install"])
        if (install / "Addons").is_dir():
            base = m.base_sources(install)
        else:
            base = set(cls.payload["provenance"]["base_pbos"])
        return m.measure(scanned, base)["tables"]

    def test_every_table_matches_the_baseline(self):
        for name, table in self.payload["tables"].items():
            with self.subTest(table=name):
                got = self.tables[name]
                self.assertEqual(got["base"]["total"], table["base"]["total"])
                self.assertEqual(got["base"]["hit"], table["base"]["hit"])
                self.assertEqual(got["modded"]["total"], table["modded"]["total"])
                self.assertEqual(got["modded"]["hit"], table["modded"]["hit"])
                self.assertEqual(len(m.modded_gaps(got)), table["unresolved_modded"])

    def test_the_split_is_not_one_sided(self):
        # A split that put every row in one half would pass the equality
        # above while measuring nothing.
        for name, tables in self.tables.items():
            with self.subTest(table=name):
                self.assertGreater(tables["base"]["total"], 0)
                self.assertGreater(tables["modded"]["total"], 0)

    def test_the_gap_files_are_what_the_tool_writes_now(self):
        """A stale gap list is worse than none: it hides the real worklist."""
        for name, table in self.tables.items():
            with self.subTest(table=name):
                path = COVERAGE / f"modded_gaps_{name}.txt"
                written = path.read_text(encoding="utf-8").splitlines()
                rows = [line for line in written if not line.startswith("#")]
                expected = sorted(
                    m.modded_gaps(table),
                    key=lambda r: (r["source"].lower(), r["class"].lower()),
                )
                self.assertEqual(len(rows), len(expected))
                for line, want in zip(rows, expected):
                    self.assertEqual(
                        line,
                        f"{want['class']}\t{m._tidy(want['display'])}\t"
                        f"{want['parent']}\t{want['source']}",
                    )


if __name__ == "__main__":
    unittest.main()
