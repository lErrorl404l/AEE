#!/usr/bin/env python3
"""The MIL-STD-2525 taxonomy marker layer contract tests.

Pins the asset prefix to the affiliation and battle dimension, and pins the
Ground/Unit coverage the taxonomy closes against the standard enumeration.

Run: python3 -m unittest tools.tests.test_symbology_taxonomy -v
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
TAXONOMY = REPO / "data" / "symbology" / "app6_taxonomy.json"
CONFIG = (REPO / "addons" / "optics" / "config_taxonomy.hpp").read_text(
    encoding="utf-8"
)
MARKERS = REPO / "addons" / "optics" / "data" / "markers"
TSV = Path("/tmp/opencode/symbol_army_rows.tsv")

AFFIL_LETTER = {"Friend": "F", "Hostile": "H", "Neutral": "N", "Unknown": "U"}
DIM_LETTER = {
    "Land": "L",
    "Air/Space": "A",
    "Space": "P",
    "Sea Surface": "S",
    "Subsurface": "U",
    "Installation": "I",
    "Equipment": "E",
}


def entries() -> list[dict]:
    return json.loads(TAXONOMY.read_text(encoding="utf-8"))["entries"]


def tokens(text: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9]+", text.lower()))


class TestTaxonomyEncoding(unittest.TestCase):
    def test_every_entry_encodes_its_affiliation_and_dimension(self):
        for e in entries():
            with self.subTest(marker=e["marker"]):
                prefix = e["marker"].split("_")[1]
                self.assertEqual(prefix[0], AFFIL_LETTER[e["affil"]])
                self.assertEqual(prefix[1], DIM_LETTER[e["dim"]])

    def test_every_entry_is_registered(self):
        for e in entries():
            with self.subTest(marker=e["marker"]):
                self.assertIn(f"class {e['marker']}: AEE_MarkerBase {{", CONFIG)

    def test_every_asset_exists(self):
        for e in entries():
            with self.subTest(marker=e["marker"]):
                self.assertTrue((MARKERS / f"{e['marker']}.paa").is_file())

    def test_the_missing_ground_unit_names_are_now_covered(self):
        if not TSV.exists():
            self.skipTest("taxonomy enumeration not present")
        rows = [l.split("\t") for l in TSV.read_text(encoding="utf-8").splitlines()]
        ground_unit = {
            r[0].strip()
            for r in rows
            if len(r) == 3
            and len([p for p in r[2].split("/") if p.strip()]) >= 4
            and [p.strip() for p in r[2].split("/") if p.strip()][1] == "Ground"
            and [p.strip() for p in r[2].split("/") if p.strip()][2] == "Unit"
        }
        catalogue = json.loads(
            (REPO / "data" / "symbology" / "nato_catalogue.json").read_text(
                encoding="utf-8"
            )
        )
        known = [tokens(e["func"]) for e in catalogue["entries"]]
        known += [tokens(e["func"]) for e in entries()]
        missing = [n for n in ground_unit if not any(tokens(n) <= k for k in known)]
        self.assertEqual(missing, [], f"uncovered Ground/Unit names: {missing}")


if __name__ == "__main__":
    unittest.main()
