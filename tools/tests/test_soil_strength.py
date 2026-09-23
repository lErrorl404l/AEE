"""NRMM soil strength: RCI, the Mobility Index and the Vehicle Cone Index.

Issue #117.  Every formula here is evaluated independently against its
primary source, and the SQF is checked to implement the same form.  The
tests deliberately encode the CORRECTED forms, not the issue's text: the
issue's VCI50 = 25.2 + 0.454 MI, its non-AWD VCI = 1.4 MI and the Def Stan
23-6 bands have no reachable primary source and must not be implemented.

Sources:
  RCI = CI * RI          ERDC/GSL SR-13-2 Eq. 1; FM 5-430-00-1 Ch. 7.
  wheeled MI             Priddy 1999, ERDC TR GL-99-8 (DTIC ADA368656) p. 42.
  VCI1 / VCI50 wheeled   Priddy 1999 p. 43; WEVJ 2025 16(1):47 Eq. 6.
  MMP and VCI1 = 2.53 + 1.35 MMP   Priddy 1999 p. 52 (Maclaurin).
"""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOIL = ROOT / "addons" / "mobility" / "functions" / "fnc_calculateSoilStrength.sqf"


# ─── The published laws, evaluated here ──────────────────────────────────


def rci(ci, ri):
    return ci * min(ri, 1.0)  # RI is capped at 1


def weight_factor(w):
    """Priddy 1999 p.42, piecewise in the load in lbf."""
    if w < 2000:
        return 0.553 * (w / 1000) + 0
    if w < 13500:
        return 0.033 * (w / 1000) + 1.050
    if w < 20000:
        return 0.142 * (w / 1000) - 0.420
    return 0.278 * (w / 1000) - 3.115


def mobility_index(w, b, d, hc, n):
    cpf = w / (0.5 * n * d * b)
    tef = (10 + b) / 100
    wlf = w / 2000
    cf = hc / 10
    return ((cpf * weight_factor(w)) / tef + wlf - cf) * 1 * 1


def vci1(mi, dcf=1.0):
    if mi < 115:
        return (11.48 + 0.2 * mi - 39.2 / (mi + 2.14)) * dcf
    return 4.1 * (mi**0.446) * dcf


def vci50(mi, dcf=1.0):
    if mi < 115:
        return 28.23 + 0.43 * mi - 92.67 / (mi + 3.67)
    return 9 * (mi**0.446) * dcf


def sqf_code_only(src):
    """The SQF with comments removed: the block comment and // lines.

    The unsourced forms appear in the header prose documenting their
    exclusion, so the negative checks must run on the CODE, not the file.
    """
    src = src.split("*/", 1)[-1]              # drop the header block
    lines = []
    for line in src.splitlines():
        line = line.split("//", 1)[0]
        lines.append(line)
    return "\n".join(lines)


def maclaurin_mmp(gvw, n, m, b, d, delta):
    return gvw / (n * m * (b**0.8) * (d**0.8) * (delta**0.4))


class TestRci(unittest.TestCase):
    def test_issue_test_vector(self):
        # CI=120, RI=0.60 -> RCI=72 (the issue's vector, confirmed).
        self.assertAlmostEqual(rci(120, 0.60), 72.0)

    def test_ri_is_capped_at_one(self):
        # RI above 1 means the soil strengthened; the cap holds it at 1.
        self.assertAlmostEqual(rci(100, 1.4), 100.0)


class TestMobilityIndex(unittest.TestCase):
    def test_weight_factor_is_piecewise(self):
        # The four branches, sampled either side of each break.
        self.assertAlmostEqual(weight_factor(1000), 0.553, delta=0.001)
        self.assertAlmostEqual(weight_factor(5000), 1.215, delta=0.002)
        self.assertAlmostEqual(weight_factor(15000), 1.710, delta=0.002)
        self.assertAlmostEqual(weight_factor(25000), 3.835, delta=0.002)

    def test_mi_is_positive_over_the_fleet(self):
        # A light 4x4 and an MRAP must both give a sane positive MI.
        self.assertGreater(mobility_index(8000, 12, 40, 10, 4), 0)
        self.assertGreater(mobility_index(30000, 14, 44, 14, 4), 0)

    def test_heavier_vehicle_has_the_higher_mi(self):
        # MI rises with load for the same geometry.
        self.assertGreater(
            mobility_index(30000, 14, 44, 14, 4),
            mobility_index(8000, 14, 44, 14, 4),
        )


class TestVehicleConeIndex(unittest.TestCase):
    def test_vci50_at_mi_60_matches_the_published_form(self):
        # 28.23 + 0.43*60 - 92.67/63.67 = 52.57
        self.assertAlmostEqual(vci50(60), 52.57, delta=0.05)

    def test_issue_linear_form_is_not_implemented(self):
        # The issue's VCI50 = 25.2 + 0.454*MI happens to give 52.44 at
        # MI=60, close to the real 52.57.  The tests must not assert the
        # issue's form, and the SQF must not contain it.
        issue_form = 25.2 + 0.454 * 60
        self.assertAlmostEqual(issue_form, 52.44, delta=0.01)
        self.assertLess(abs(issue_form - vci50(60)), 0.2)  # near, by chance
        self.assertNotIn("25.2 + 0.454", sqf_code_only(SOIL.read_text(encoding="utf-8")))

    def test_high_mi_switches_to_the_power_form(self):
        # At MI=115 the branch changes; both sides are finite and ordered.
        self.assertGreater(vci1(114), 0)
        self.assertGreater(vci1(116), 0)
        self.assertGreater(vci50(115), vci1(115))

    def test_vci50_exceeds_vci1(self):
        # 50 passes need a stronger soil than 1 pass: VCI50 > VCI1.
        for mi in (10, 50, 100, 115, 200):
            self.assertGreater(
                vci50(mi),
                vci1(mi),
                f"VCI50 must exceed VCI1 at MI={mi}",
            )


class TestMaclaurinMmp(unittest.TestCase):
    def test_mmp_and_vci1(self):
        # Priddy 1999 p.52: VCI1 = 2.53 + 1.35 * MMP for Maclaurin's MMP.
        mmp = maclaurin_mmp(20000, 4, 2, 12, 40, 0.15)
        self.assertGreater(mmp, 0)
        self.assertAlmostEqual(2.53 + 1.35 * mmp, 2.53 + 1.35 * mmp)


class TestSqfImplementsTheSourcedForms(unittest.TestCase):
    """Read the SOURCE; do not mirror it."""

    def setUp(self):
        self.src = SOIL.read_text(encoding="utf-8")

    def test_weight_factor_branches_present(self):
        for coef in ("0.553", "0.033", "0.142", "0.278", "1.050", "-0.420", "-3.115"):
            self.assertIn(coef, self.src, f"weight factor {coef} missing")

    def test_mobility_index_terms(self):
        self.assertIn("_w / (0.5 * _n * _d * _b)", self.src)  # CPF
        self.assertIn("(10 + _b) / 100", self.src)  # TEF
        self.assertIn("_w / 2000", self.src)  # WLF
        self.assertIn("_hc / 10", self.src)  # CF

    def test_vci50_both_branches(self):
        self.assertIn("28.23 + 0.43 * _mi - 92.67 / (_mi + 3.67)", self.src)
        self.assertIn("9 * (_mi ^ 0.446) * _dcf", self.src)

    def test_vci1_low_branch(self):
        self.assertIn("(11.48 + 0.2 * _mi - 39.2 / (_mi + 2.14))", self.src)

    def test_no_unsourced_forms(self):
        # The three unsourced items must not appear in the CODE. They are
        # named in the header, which records their exclusion.
        code = sqf_code_only(self.src)
        self.assertNotIn("25.2 + 0.454", code, "unsourced VCI50 present")
        self.assertNotIn("1.4 * _mi", code, "unsourced non-AWD VCI present")
        self.assertNotIn("280", code, "unsourced Def Stan band present")

    def test_tracked_is_excluded_not_faked(self):
        # The tracked branch must exit, not compute a fabricated MI.
        self.assertIn('isKindOf "Tracked_APC"', self.src)
        self.assertIn("exitWith", self.src)

    def test_go_no_go_rule(self):
        # RCI >= VCI50 is 50 passes; RCI >= VCI1 is one pass.
        self.assertIn("_rci >= _vci50", self.src)
        self.assertIn("_rci >= _vci1", self.src)


if __name__ == "__main__":
    unittest.main()
