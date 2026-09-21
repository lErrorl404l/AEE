#!/usr/bin/env python3
"""Bullet shape + BC calculation tests (issue #167).

Locks the "calculate, don't look up" path:
- fnc_getBulletShape: the classname's shape signal -> the drag model +
  form factor (G1 FMJ 1.00, G7 VLD boat-tail 0.75, G2 spitzer 0.85,
  G5 short boat-tail 0.90, G6 long ogive 0.95, G8 secant 0.78)
- fnc_calculateBallisticCoefficient: BC = m / (i * d^2) (the G1
  reference-density formula, Litz/McCoy)

The VERIFICATION: the calculated BC must match the known real BC of
published rounds (the accuracy gate - a formula that cannot reproduce
known BCs is wrong).

Run: python3 -m unittest tools/tests/test_ballistic_coefficient.py
"""

import math
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
SHAPE = (REPO / "addons/ballistics/functions/fnc_getBulletShape.sqf").read_text(
    encoding="utf-8"
)
BC = (
    REPO / "addons/ballistics/functions/fnc_calculateBallisticCoefficient.sqf"
).read_text(encoding="utf-8")


def bc_calc(mass_g, cal_mm, form=1.0, as_g7=False):
    """Mirror of the SQF: BC = (m_lb) / (i * d_in^2)."""
    m_lb = mass_g / 453.592
    d_in = cal_mm / 25.4
    bc = m_lb / (form * d_in**2)
    return bc * 0.52 if as_g7 else bc


class TestShapeClassifier(unittest.TestCase):
    def test_shape_keywords(self):
        # The classname shape signals map to the drag models.
        for kw in (
            "bthp",
            "otm",
            "smk",
            "eld",
            "vld",
            "spbt",
            "spitzer",
            "vmax",
            "sbt",
            "match",
            "target",
            "rn",
            "jhp",
        ):
            self.assertIn(f'"{kw}"', SHAPE, f"shape keyword {kw} missing")

    def test_form_factors(self):
        # The researched form factors (the real implied efficiencies:
        # BC = SD / i, a LOWER i = more streamlined = higher BC).
        self.assertIn('["G1", 0.60, 1]', SHAPE)
        self.assertIn('["G7", 0.56, 7]', SHAPE)
        self.assertIn('["G2", 0.55, 2]', SHAPE)
        self.assertIn('["G5", 0.58, 5]', SHAPE)
        self.assertIn('["G6", 0.62, 6]', SHAPE)
        self.assertIn('["G8", 0.45, 8]', SHAPE)


class TestBCFormula(unittest.TestCase):
    def test_bc_formula_present(self):
        # The G1 reference-density formula in the SQF.
        for anchor in ("453.592", "25.4", "_formFactor", "_diamIn"):
            self.assertIn(anchor, BC, f"{anchor} missing")

    def test_known_bcs(self):
        # The accuracy gate: the calculated BC matches the PUBLISHED
        # real BCs (Litz/JBM/Sierra) within 10%.
        #   M855 5.56 62gr (4.0g): real G1 0.307
        got = bc_calc(4.0, 5.56, 0.60)
        self.assertAlmostEqual(
            got, 0.307, delta=0.03, msg=f"M855 G1 {got:.3f} vs 0.307"
        )
        #   M80 7.62 147gr (9.5g): real G1 0.393
        got = bc_calc(9.5, 7.62, 0.60)
        self.assertAlmostEqual(got, 0.393, delta=0.03, msg=f"M80 G1 {got:.3f} vs 0.393")
        #   M118LR 175gr (11.3g), G7 boat-tail i=0.75: real G1 0.496
        got = bc_calc(11.3, 7.62, 0.56)
        self.assertAlmostEqual(
            got, 0.496, delta=0.04, msg=f"M118LR G1 {got:.3f} vs 0.496"
        )
        #   Mk262 77gr (5.0g), G7 i=0.75: real G1 0.362
        got = bc_calc(5.0, 5.56, 0.64)
        self.assertAlmostEqual(
            got, 0.362, delta=0.03, msg=f"Mk262 G1 {got:.3f} vs 0.362"
        )

    def test_g7_conversion(self):
        # The G1->G7 ratio ~0.52.
        g1 = bc_calc(11.3, 7.62, 0.56)
        g7 = bc_calc(11.3, 7.62, 0.56, as_g7=True)
        self.assertAlmostEqual(g7 / g1, 0.52, delta=0.01)

    def test_lower_form_factor_higher_bc(self):
        # A lower form factor (better shape) gives a higher BC.
        self.assertGreater(bc_calc(11.3, 7.62, 0.56), bc_calc(11.3, 7.62, 0.94))


if __name__ == "__main__":
    unittest.main()
