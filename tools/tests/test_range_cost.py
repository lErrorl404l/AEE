#!/usr/bin/env python3
"""Long-range performance validator (issue #139).

Locks the verified research (long-range-performance.md) against the
code: the object-view-distance lever must exist in
fnc_calculateViewDistance with the BI-guidance constants, and the
verified command specs must be referenced.
"""

import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
FNC = (REPO / "addons/optics/functions/vision/fnc_calculateViewDistance.sqf").read_text(
    encoding="utf-8"
)
DOC = (REPO / "docs/wiki/research/long-range-performance.md").read_text(
    encoding="utf-8"
)


class TestRangeCostLever(unittest.TestCase):
    def test_object_view_distance_driven(self):
        # The "CPU killer" lever must be driven, with the two-param
        # setObjectViewDistance form (object + shadow together).
        self.assertIn("setObjectViewDistance", FNC)
        self.assertIn("_objTarget", FNC)

    def test_bot_guidance_ratio(self):
        # Object = 1/2 of terrain (the BI guidance mid-point).
        self.assertIn("(_target * 0.5)", FNC)

    def test_shadow_fraction(self):
        # The two-param form sets shadow to 25% of object.
        self.assertIn("_to * 0.25", FNC)

    def test_verified_40000_max_in_doc(self):
        # The research corrected the scripted max: 40,000, not 12,000.
        self.assertIn("40,000", DOC)
        self.assertIn("12,000 is", DOC)

    def test_verified_two_param_in_doc(self):
        self.assertIn("[object, shadow]", DOC)
        self.assertIn("setObjectViewDistance [2000, 800]", DOC)


if __name__ == "__main__":
    unittest.main()
