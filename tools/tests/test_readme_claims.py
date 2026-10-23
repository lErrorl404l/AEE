#!/usr/bin/env python3
"""The README's feature claims must match the code and the tree.

The campaign changes the models faster than the prose.  This gate reads the
README, the addon tree and the kernel that owns each claim, so a stale
sentence fails here instead of shipping.  It checks four things:

(a) the CBRN claim names the model the kernel runs, and no removed rule;
(b) the compat addon count in prose equals the compat addons on disk;
(c) every item-mass grade the resolver can return is stated in the README;
(d) the coverage and load-gate claims name real tools and real paths.

A prose linter would be noise.  Each assertion below binds a sentence to a
fact that a change can break.

Run: python3 -m unittest tools.tests.test_readme_claims
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"
ADDONS = REPO / "addons"
CBRN = REPO / "addons/persistence/functions/warnings/fnc_calculateCBRNPersistence.sqf"
ITEM_MASS = REPO / "addons/clothing/functions/clothing/fnc_getItemMass.sqf"
COVERAGE = REPO / "tools/report_match_coverage.py"

# English numerals for the counts a short sentence states in words.
_NUMERALS = {
    1: "One",
    2: "Two",
    3: "Three",
    4: "Four",
    5: "Five",
    6: "Six",
    7: "Seven",
    8: "Eight",
    9: "Nine",
    10: "Ten",
}


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _compat_addons() -> list[str]:
    return sorted(p.parent.name for p in ADDONS.glob("compat_*/config.cpp"))


class TestReadmeClaims(unittest.TestCase):
    def test_cbrn_claim_matches_the_kernel(self) -> None:
        text = _readme()
        kernel = CBRN.read_text(encoding="utf-8")
        # The kernel runs on an activation energy and keeps no Q10 rule.
        self.assertIn("activation energy", kernel)
        self.assertIn("Q10 rule of thumb that stood here is gone", kernel)
        self.assertIn("activation energy", text)
        self.assertNotIn(
            "Q10", text, "the README still advertises the removed Q10 rule"
        )

    def test_compat_count_matches_the_tree(self) -> None:
        count = len(_compat_addons())
        word = _NUMERALS.get(count, str(count))
        self.assertIn(
            f"{word} compat addons",
            _readme(),
            f"README.md must say '{word} compat addons' for {count} on disk",
        )

    def test_every_item_mass_grade_is_stated(self) -> None:
        grades = set(
            re.findall(r'_grade = "([a-z_]+)"', ITEM_MASS.read_text(encoding="utf-8"))
        )
        self.assertEqual(
            grades,
            {"sourced", "family", "engine_mass", "type", "zero"},
            "the resolver's grade set changed; update the README vocabulary too",
        )
        text = _readme()
        missing = sorted(grade for grade in grades if f"`{grade}`" not in text)
        self.assertEqual(
            missing, [], "grades missing from README.md: " + ", ".join(missing)
        )

    def test_coverage_claim_names_the_measurement(self) -> None:
        text = _readme()
        self.assertIn("tools/report_match_coverage.py", text)
        self.assertIn("data/coverage/", text)
        self.assertTrue(
            COVERAGE.is_file(), "the coverage tool the README names is gone"
        )
        self.assertTrue((REPO / "data/coverage/modded_baseline.json").is_file())

    def test_load_gate_claim_names_a_real_mode(self) -> None:
        text = _readme()
        self.assertIn("tools/docker_test.sh --load", text)
        script = (REPO / "tools/docker_test.sh").read_text(encoding="utf-8")
        self.assertIn("--load)", script, "the load gate the README names is not a mode")


if __name__ == "__main__":
    unittest.main()
