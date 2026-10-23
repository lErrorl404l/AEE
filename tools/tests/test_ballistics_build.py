#!/usr/bin/env python3
"""Ballistics build tests: the held loads survive and the layers stay cited.

Three properties the build must hold:

  * a cannon or grenade load that a data sheet defines never leaves the
    table when the military ingest rebuilds it;
  * every cartridge cites a standard, or is reported as having none;
  * every ballistic coefficient states the drag model and its basis.

Run: python3 tools/tests/test_ballistics_build.py
"""

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_loads_from_cannon  # noqa: E402

DATA = REPO / "data" / "ballistics"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


class TestHeldLoads(unittest.TestCase):
    def test_every_held_cannon_load_survives(self):
        held = {r["load_id"] for r in load("sources/loads_cannon.json")["loads"]}
        table = {r["load_id"] for r in load("loads.json")}
        self.assertEqual(held - table, set(), "a held cannon load left the table")

    def test_the_cannon_merge_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "loads.json"
            shutil.copy(DATA / "loads.json", db)
            original = gen_loads_from_cannon.DB
            gen_loads_from_cannon.DB = db
            try:
                gen_loads_from_cannon.main()
                first = db.read_bytes()
                gen_loads_from_cannon.main()
                self.assertEqual(first, db.read_bytes())
            finally:
                gen_loads_from_cannon.DB = original


class TestStandardsRegister(unittest.TestCase):
    def test_every_cartridge_cites_a_standard_or_is_reported(self):
        coverage = (DATA / "STANDARDS_COVERAGE.md").read_text(encoding="utf-8")
        reported = {
            line.strip()[3:-1]
            for line in coverage.splitlines()
            if line.strip().startswith("- `")
        }
        for record in load("cartridges.json"):
            if record["cartridge_id"] in reported:
                continue
            self.assertTrue(
                record.get("standards"),
                f"{record['cartridge_id']} cites no standard and is not reported",
            )

    def test_one_standard_is_authoritative(self):
        for record in load("cartridges.json"):
            entries = record.get("standards") or []
            if entries:
                self.assertEqual(
                    sum(1 for e in entries if e.get("authoritative")),
                    1,
                    f"{record['cartridge_id']} needs one authoritative standard",
                )


class TestCoefficientBasis(unittest.TestCase):
    def test_every_coefficient_states_model_basis_and_edition(self):
        for record in load("projectiles.json"):
            for field, model in (("bc_g1", "G1"), ("bc_g7", "G7")):
                entry = record["values"].get(field)
                if entry is None:
                    continue
                self.assertEqual(
                    entry.get("drag_model"), model, record["projectile_id"]
                )
                self.assertIn(
                    entry.get("basis"),
                    ("independent_measurement", "maker_published_secondary"),
                    record["projectile_id"],
                )
                self.assertTrue(entry.get("edition"), record["projectile_id"])

    def test_the_basis_report_matches_the_coefficients(self):
        """A basis count in the report is a claim about the corpus.

        The report is generated from the same run, so a disagreement means
        one of the two was edited by hand or not regenerated.
        """
        counts = {"independent_measurement": 0, "maker_published_secondary": 0}
        for record in load("projectiles.json"):
            for field in ("bc_g1", "bc_g7"):
                entry = record["values"].get(field)
                if isinstance(entry, dict) and entry.get("basis") in counts:
                    counts[entry["basis"]] += 1
        report = (DATA / "BC_BASIS.md").read_text(encoding="utf-8")
        for basis, expected in counts.items():
            row = re.search(rf"^\| {basis} \| (\d+) \|$", report, re.M)
            self.assertIsNotNone(row, f"{basis} is missing from the report")
            self.assertEqual(int(row.group(1)), expected, basis)
        stated = re.search(r"^\| Total \| (\d+) \|$", report, re.M)
        self.assertIsNotNone(stated, "the report states no total")
        self.assertEqual(int(stated.group(1)), sum(counts.values()))


if __name__ == "__main__":
    unittest.main()
