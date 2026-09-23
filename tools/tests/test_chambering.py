#!/usr/bin/env python3
"""The chambering canonical form and the join it drives.

The canonical form is the fix for the blank cartridge_id: the maker writes
a chambering one way and the register writes it another, so an exact name
match misses. These tests pin the transformations that must hold, and the
ones that must NOT happen, because an over-eager rule silently merges two
different cartridges.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "validation"))
import chambering  # noqa: E402


class TestCanonical(unittest.TestCase):
    def test_verse_forms_of_one_cartridge_agree(self):
        """7.62x54R is written four ways across the sources."""
        forms = [
            "7_62_x_54_r",
            "7,62 x 54 R",
            "7.62x54mmR",
            "7.62\u00d754mmR",
        ]
        keys = {chambering.canonical(f) for f in forms}
        self.assertEqual(len(keys), 1, f"verse forms diverged: {keys}")

    def test_the_rim_is_kept(self):
        """7x57 and 7x57R are different cartridges."""
        self.assertNotEqual(chambering.canonical("7x57"), chambering.canonical("7x57R"))

    def test_a_ratio_is_one_designation(self):
        """450/400 is a single cartridge, not a list."""
        self.assertNotEqual(
            chambering.canonical("450/400"), chambering.canonical("450")
        )

    def test_magnum_is_folded_but_rem_is_not_a_unit(self):
        """The mm in Remington must not be read as the unit mm."""
        self.assertEqual(chambering.canonical("222 Rem. Mag."), "222remmag")
        self.assertNotEqual(
            chambering.canonical("222 Rem. Mag."), chambering.canonical("222 Rem.")
        )

    def test_the_unit_goes(self):
        self.assertEqual(chambering.canonical("9x19mm"), "9x19")
        self.assertEqual(chambering.canonical("5.56x45mm NATO"), "556x45nato")


class TestResolution(unittest.TestCase):
    def test_a_collision_is_refused_not_guessed(self):
        """Two records on one key must not resolve."""
        index = {"dup": {"record_a", "record_b"}}
        cid, candidates = chambering.resolve("dup", index)
        self.assertEqual(cid, "")
        self.assertEqual(candidates, ["record_a", "record_b"])

    def test_a_single_hit_resolves(self):
        cid, candidates = chambering.resolve("9x19mm", {"9x19": {"9x19"}})
        self.assertEqual(cid, "9x19")
        self.assertEqual(candidates, [])

    def test_an_unknown_chambering_is_unresolved(self):
        cid, candidates = chambering.resolve("9x99mm", {"9x19": {"9x19"}})
        self.assertEqual(cid, "")
        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
