#!/usr/bin/env python3
"""CBRN equipment tests (issue #119, the CBRN gear table).

Locks the researched CBRN protection in fnc_getCbrnProtection.sqf
(equipment-library.md CBRN section): JSLIST 2.63 kg / 24 h profile,
M50 JSGPM 0.86 kg CBRN Cap 1, MOPP/L-1/OKZK suits.  The protection
factor scales the ACM contamination exposure (full kit 0.05 exposure,
no kit 1.0).

Run: python3 -m unittest tools/tests/test_cbrn.py
"""

import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
FNC = (
    REPO / "addons/environmental/functions/warnings/fnc_getCbrnProtection.sqf"
).read_text(encoding="utf-8")
ACM = (REPO / "addons/compat_acm/functions/fnc_integrateACM.sqf").read_text(
    encoding="utf-8"
)


class TestCbrnProtection(unittest.TestCase):
    def test_mask_keywords(self):
        # The researched respirators: M50 JSGPM (0.86 kg CBRN Cap 1),
        # M40/M42, FM12/FM50/C50, S10, PMK-3, GP-5/7.
        for kw in ("m50", "m40", "fm12", "c50", "s10", "pmk", "gp-7", "respirator"):
            self.assertIn(f'"{kw}"', FNC, f"mask keyword {kw} missing")

    def test_suit_keywords(self):
        # The researched suits: JSLIST (2.63 kg), MOPP, L-1/OKZK (RU
        # impermeable), 6B44 Ratnik CBRN.
        for kw in ("jslist", "mopp", "l-1", "okzk", "6b44", "nbc"):
            self.assertIn(f'"{kw}"', FNC, f"suit keyword {kw} missing")

    def test_protection_tiers(self):
        # Full kit 0.95, mask alone 0.75, suit alone 0.60, none 0.0.
        self.assertIn("{ 0.95 }", FNC)
        self.assertIn("{ 0.75 }", FNC)
        self.assertIn("{ 0.60 }", FNC)
        self.assertIn("{ 0.0 }", FNC)

    def test_uses_gear_slots(self):
        # Reads the goggles slot (mask) + uniform (suit).
        self.assertIn("goggles _unit", FNC)
        self.assertIn("uniform _unit", FNC)

    def test_ace_integration_scales_exposure(self):
        # The ACM integration scales the contamination by 1 - protection.
        self.assertIn("getCbrnProtection", ACM)
        self.assertIn("(1 - _protection)", ACM)


if __name__ == "__main__":
    unittest.main()
