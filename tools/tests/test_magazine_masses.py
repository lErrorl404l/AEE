"""Unit tests for the magazine loaded-mass projection (gen_magazine_masses)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.validation import gen_magazine_masses as gen

REPO = Path(__file__).parents[2]
OUT = REPO / "data" / "ballistics" / "magazine_masses.json"


class TestMagazineMasses(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(OUT.read_text(encoding="utf-8"))

    def test_published_loaded_rows(self) -> None:
        published = [row for row in self.payload["rows"] if row["basis"] == "published"]
        self.assertEqual(len(published), 13)

    def test_derived_round_numbers(self) -> None:
        # The pinned derived formula: 141.7 + 30 * 12.3 = 510.7 g.
        by_item = {row["item"]: row for row in self.payload["rows"]}
        row = by_item["Magpul PMAG 30 AR/M4 GEN M3"]
        self.assertEqual(row["basis"], "derived")
        self.assertAlmostEqual(row["loaded_mass_g"], 141.7 + 30 * 12.3, places=3)

    def test_stanag_group_within_one_gram_of_g36(self) -> None:
        groups = {
            (group["calibre_key"], group["capacity"]): group
            for group in self.payload["groups"]
        }
        group = groups[("556x45", 30)]
        self.assertAlmostEqual(group["loaded_mass_g"], 510.7, delta=1.0)
        # The held G36 loaded value 510.0 g is an independent check.
        self.assertAlmostEqual(group["loaded_mass_g"], 510.0, delta=1.0)

    def test_counts(self) -> None:
        self.assertEqual(len(self.payload["rows"]), 61)
        self.assertEqual(len(self.payload["groups"]), 36)
        self.assertEqual(len(self.payload["leads"]), 15)

    def test_file_is_fresh(self) -> None:
        self.assertEqual(OUT.read_text(encoding="utf-8"), gen.render(gen.build()))


if __name__ == "__main__":
    unittest.main()
