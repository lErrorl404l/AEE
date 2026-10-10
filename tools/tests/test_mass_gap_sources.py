#!/usr/bin/env python3
"""Cargo, mortar and launcher mass-gap contract (Task 9).

The source plan must characterise each of the three remaining mass gaps.
Each gap must name its engine key, its held-data status, a source class to
seek and a licence. Each gap must name a source class.

Run: python3 -m unittest tools.tests.test_mass_gap_sources -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

PLAN = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "wiki"
    / "research"
    / "mass-gap-source-plan.md"
)

# One entry per gap: the engine key it names, the held-data status, the
# source class it must name, and a licence it must name. Tokens are matched
# case-insensitively against the plan text.
GAPS = (
    {
        "name": "cargo and ammo boxes",
        "engine_key": "cfgvehicles >> mass",
        "source_class": "maker or army datasheet",
        "licence": "public domain or maker",
    },
    {
        "name": "mortar bombs",
        "engine_key": "cfgmagazines >> mass",
        "source_class": "us army technical manual",
        "licence": "public domain",
    },
    {
        "name": "launcher empty masses",
        "engine_key": "cfgweapons >> iteminfo >> mass",
        "source_class": "maker datasheet",
        "licence": "public domain or maker",
    },
)


class MassGapSourcesTest(unittest.TestCase):
    """The plan characterises each gap and names a source class for it."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.text = PLAN.read_text(encoding="utf-8")
        cls.lower = cls.text.lower()

    def test_the_plan_exists_and_is_not_empty(self) -> None:
        self.assertTrue(self.text.strip())

    def test_every_gap_names_an_engine_key(self) -> None:
        for gap in GAPS:
            with self.subTest(gap=gap["name"]):
                self.assertIn(gap["engine_key"], self.lower)

    def test_every_gap_names_a_source_class(self) -> None:
        for gap in GAPS:
            with self.subTest(gap=gap["name"]):
                self.assertIn(gap["source_class"], self.lower)

    def test_every_gap_names_the_held_data_status(self) -> None:
        for gap in GAPS:
            with self.subTest(gap=gap["name"]):
                heading = self.lower.find(gap["name"])
                self.assertGreaterEqual(heading, 0, gap["name"])
                section = self.lower[heading:]
                next_heading = section.find("\n## ", len(gap["name"]) + 3)
                if next_heading != -1:
                    section = section[:next_heading]
                self.assertIn("held data: none", section)

    def test_every_gap_names_a_licence(self) -> None:
        for gap in GAPS:
            with self.subTest(gap=gap["name"]):
                self.assertIn(gap["licence"], self.lower)

    def test_the_plan_lists_the_three_gaps(self) -> None:
        for gap in GAPS:
            with self.subTest(gap=gap["name"]):
                self.assertIn(gap["name"], self.lower)


if __name__ == "__main__":
    unittest.main()
