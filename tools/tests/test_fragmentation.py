#!/usr/bin/env python3
"""Explosion fragmentation physics (issue #107).

Executes the REAL SQF kernels under addons/blast/functions/fragmentation/ with
the sqf_lite harness (issue #204: a hand-transcribed Python mirror would not be
testing the mod).  The kernels implement published models:

  - Gurney fragment velocity (BRL Report 405, 1943)
  - Mott fragment-size distribution (Mott 1943, 1947)
  - DDESB TP-12 fragment velocity decay
  - Henderson lethality curve (DTIC ADA532158)
  - Poisson density model and the angular pattern (issue #107)

Published test vectors pinned here (issue #107):
  M67  Gurney velocity            2027 m/s (the issue quotes 2029)
  M107 Gurney velocity             985 m/s
  M67  N(m > 0.5 g)                109
  0.1 g fragment at 10/30/50 m     502 / 88 / 15 m/s

Run: python3 -m unittest tools.tests.test_fragmentation
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.tests.sqf_lite import run_sqf  # noqa: E402

FRAG = ROOT / "addons" / "blast" / "functions" / "fragmentation"


def call(name, args):
    """Run one fragmentation kernel with the given arguments."""
    return run_sqf(FRAG / f"fnc_{name}.sqf", args)


class TestGurneyVelocity(unittest.TestCase):
    """Gurney fragment velocity (BRL Report 405, 1943)."""

    def test_m67_grenade_sphere(self):
        # M67: 184 g Composition B (sqrt2E 2700) in a 216 g body, sphere.
        # 2700 / sqrt(216/184 + 3/5) = 2027 m/s.  The issue quotes 2029,
        # which is the same form with a body of about 215 g.
        v = call("calculateGurneyVelocity", [0.184, 0.216, 2700, "sphere"])
        self.assertAlmostEqual(v, 2027, delta=3)

    def test_m107_155mm_cylinder(self):
        # M107: 6.86 kg TNT (sqrt2E 2370), 36.34 kg shell body, cylinder.
        v = call("calculateGurneyVelocity", [6.86, 36.34, 2370, "cylinder"])
        self.assertAlmostEqual(v, 985, delta=2)

    def test_issue_correction_wrong_form_rejected(self):
        # The misremembered form keeps a leading sqrt(M/C) factor and gives
        # about 6570 m/s for the M107, which is impossible.  The kernel must
        # not reproduce it.
        r = 36.34 / 6.86
        wrong = 2370 * r / math.sqrt(1 + 0.5 * r)
        self.assertGreater(wrong, 6000)
        self.assertLess(wrong, 7000)
        v = call("calculateGurneyVelocity", [6.86, 36.34, 2370, "cylinder"])
        self.assertNotAlmostEqual(v, wrong, delta=1000)

    def test_sphere_slower_than_cylinder(self):
        # For the same charge-to-metal ratio the sphere denominator (M/C + 3/5)
        # exceeds the cylinder one (M/C + 1/2), so the sphere form is slower.
        cyl = call("calculateGurneyVelocity", [1, 1, 2700, "cylinder"])
        sph = call("calculateGurneyVelocity", [1, 1, 2700, "sphere"])
        self.assertLess(sph, cyl)

    def test_invalid_input_returns_zero(self):
        self.assertEqual(call("calculateGurneyVelocity", [0, 1, 2700, "sphere"]), 0)
        self.assertEqual(call("calculateGurneyVelocity", [1, 0, 2700, "sphere"]), 0)


class TestMottDistribution(unittest.TestCase):
    """Mott fragment-size distribution (Mott 1943, 1947)."""

    def test_m67_count_above_half_gram(self):
        # M67 body 216 g, N0 = 1440 (mean fragment 0.15 g).  N(> 0.5 g) = 109.
        n = call("calculateMottCount", [0.216, 1440, 0.0005])
        self.assertAlmostEqual(n, 109, delta=1)

    def test_count_decreases_with_mass(self):
        a = call("calculateMottCount", [0.216, 1440, 0.0001])
        b = call("calculateMottCount", [0.216, 1440, 0.001])
        self.assertGreater(a, b)

    def test_mott_mass_is_inverse_of_count(self):
        # The sampled mass m(U) must satisfy N(m)/N0 = U.
        for u in (0.2, 0.5, 0.8):
            m = call("calculateMottMass", [0.216, 1440, u])
            n = call("calculateMottCount", [0.216, 1440, m])
            self.assertAlmostEqual(n / 1440, u, places=6)

    def test_sample_mass_positive(self):
        for u in (0.01, 0.5, 0.99):
            self.assertGreater(call("calculateMottMass", [0.216, 1440, u]), 0)


class TestFragmentDecay(unittest.TestCase):
    """DDESB TP-12 fragment velocity decay."""

    def test_light_fragment_01g(self):
        # 0.1 g at V0 = 1200 m/s: 502 / 88 / 15 m/s at 10 / 30 / 50 m.
        for r, expected in ((10, 502), (30, 88), (50, 15)):
            v = call("calculateFragmentDecay", [1200, 0.0001, r])
            self.assertAlmostEqual(v, expected, delta=1.5, msg=f"R={r}")

    def test_heavy_fragment_10g(self):
        # 10 g at V0 = 1200 m/s: 995 / 683 / 469 m/s at 10 / 30 / 50 m.
        for r, expected in ((10, 995), (30, 683), (50, 469)):
            v = call("calculateFragmentDecay", [1200, 0.01, r])
            self.assertAlmostEqual(v, expected, delta=1.5, msg=f"R={r}")

    def test_decay_monotonic(self):
        vs = [
            call("calculateFragmentDecay", [1200, 0.0001, r]) for r in (5, 10, 20, 40)
        ]
        for a, b in zip(vs, vs[1:]):
            self.assertGreater(a, b)

    def test_length_scale_247(self):
        # L = 247 * m^(1/3).  At R = L the velocity is V0 / e.
        m = 0.001
        length = 247 * m ** (1 / 3)
        v = call("calculateFragmentDecay", [1000, m, length])
        self.assertAlmostEqual(v, 1000 / math.e, delta=1)


class TestHendersonLethality(unittest.TestCase):
    """Henderson lethality curve (DTIC ADA532158)."""

    def test_energy_anchors(self):
        # 79 J -> 0.31, 103 J -> 0.50, 200 J -> 0.90.
        for energy, prob in ((79, 0.31), (103, 0.50), (200, 0.90)):
            v = math.sqrt(2 * energy / 0.001)
            self.assertAlmostEqual(
                call("calculateFragmentLethality", [0.001, v]), prob, places=2
            )

    def test_velocity_for_79j(self):
        # The velocity that gives 79 J: 0.1 g -> 1257, 1 g -> 397, 10 g -> 126.
        for m, v in ((0.0001, 1257), (0.001, 397), (0.01, 126)):
            exact = math.sqrt(2 * 79 / m)
            self.assertAlmostEqual(exact, v, delta=1)
            # At the exact 79 J velocity the lethality is the 31% anchor.
            self.assertAlmostEqual(
                call("calculateFragmentLethality", [m, exact]), 0.31, places=2
            )

    def test_below_threshold_not_lethal(self):
        # 50 J sits below the 79 J anchor.
        v = math.sqrt(2 * 50 / 0.001)
        self.assertEqual(call("calculateFragmentLethality", [0.001, v]), 0)

    def test_clamped_high(self):
        self.assertLessEqual(call("calculateFragmentLethality", [0.01, 5000]), 1.0)


class TestAngularPattern(unittest.TestCase):
    """Angular emission (Gurney, BRL Report 405, 1943)."""

    def test_isotropic_half_within_30_of_horizontal(self):
        # Sum the isotropic band fraction from theta 60 to 120 degrees.
        total = 0.0
        step = 1.0
        theta = 60.0
        while theta < 120.0:
            total += call(
                "calculateFragmentAngularFraction",
                [theta + step / 2, step, "isotropic"],
            )
            theta += step
        self.assertAlmostEqual(total, 0.5, delta=0.01)

    def test_isotropic_zero_at_poles(self):
        self.assertAlmostEqual(
            call("calculateFragmentAngularFraction", [0, 1, "isotropic"]), 0, places=6
        )

    def test_cylinder_peak_at_equator(self):
        self.assertAlmostEqual(
            call("calculateFragmentAngularFraction", [90, 1, "cylinder"]), 1.0, places=6
        )
        # One sigma off the equator the weight is exp(-1/2).
        off = call("calculateFragmentAngularFraction", [107.5, 1, "cylinder", 17.5])
        self.assertAlmostEqual(off, math.exp(-0.5), places=6)


class TestDensityAndHits(unittest.TestCase):
    """Poisson density model (issue #107)."""

    def test_ground_burst_inverse_square(self):
        r1 = call("calculateFragmentDensity", [1000, 1, 10, 0])
        r2 = call("calculateFragmentDensity", [1000, 1, 20, 0])
        # Doubling the range quarters the density.
        self.assertAlmostEqual(r1, 4 * r2, delta=r1 * 0.01)

    def test_airburst_less_steep(self):
        a1 = call("calculateFragmentDensity", [1000, 1, 10, 10])
        a2 = call("calculateFragmentDensity", [1000, 1, 20, 10])
        # An airburst falls off slower than the ground-burst 1/R^2.
        self.assertGreater(a2 / a1, 0.25)

    def test_hit_chance_poisson(self):
        density, area = 2.0, 0.25
        expected = 1 - math.exp(-density * area)
        self.assertAlmostEqual(
            call("calculateFragmentHitChance", [density, area]), expected, places=6
        )

    def test_hit_chance_bounds(self):
        self.assertEqual(call("calculateFragmentHitChance", [0, 0.25]), 0)
        self.assertGreater(call("calculateFragmentHitChance", [0.1, 0.25]), 0)
        self.assertLess(call("calculateFragmentHitChance", [0.1, 0.25]), 1)


class TestWarheadTable(unittest.TestCase):
    """The sourced warhead rows drive the model (issue #107)."""

    def test_rows_present_and_sourced(self):
        for key in ("M67", "M107", "Mk82", "RPG7"):
            row = call("getFragmentationWarhead", [key])
            self.assertEqual(len(row), 6, key)
            self.assertEqual(row[0], key)

    def test_m67_row(self):
        row = call("getFragmentationWarhead", ["M67"])
        self.assertEqual(row, ["M67", 0.184, 0.216, 2700, "sphere", 1440])

    def test_unknown_key_empty(self):
        self.assertEqual(call("getFragmentationWarhead", ["nope"]), [])

    def test_table_drives_the_model(self):
        # The M107 row through Gurney gives the published 985 m/s.
        row = call("getFragmentationWarhead", ["M107"])
        v = call("calculateGurneyVelocity", [row[1], row[2], row[3], row[4]])
        self.assertAlmostEqual(v, 985, delta=2)


if __name__ == "__main__":
    unittest.main()
