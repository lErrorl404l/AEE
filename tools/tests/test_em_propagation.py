#!/usr/bin/env python3
"""Reference checks for AEE's 3D EM propagation kernels (issue #13).

Executes the shipped SQF kernels through tools/tests/sqf_lite.py, the same
way the mod runs them.  Covers the two-ray ground-reflection excess, the
ITU-R P.526 single knife-edge loss, the Deygout multiple-edge combination and
the valley-waveguide modifier.

Run: python3 -m unittest tools.tests.test_em_propagation
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RADIO = ROOT / "addons" / "radio" / "functions"

TWO_RAY = RADIO / "fnc_calculateTwoRayGround.sqf"
KNIFE = RADIO / "fnc_calculateKnifeEdgeLoss.sqf"
DEYGOUT = RADIO / "fnc_calculateDeygoutDiffraction.sqf"
VALLEY = RADIO / "fnc_calculateValleyWaveguide.sqf"

C = 3e8


def knife_loss(v):
    """ITU-R P.526-16 eq (31), valid for v > -0.78 (0 below)."""
    if v <= -0.78:
        return 0.0
    return 6.9 + 20 * math.log10(math.sqrt((v - 0.1) ** 2 + 1) + v - 0.1)


def two_ray_excess(d, f, ht, hr, rho):
    """Mirror of fnc_calculateTwoRayGround: excess over free space, dB."""
    lam = C / f
    dphi = 4 * math.pi * ht * hr / (lam * d)
    field = max(0.01, 1 + rho**2 - 2 * rho * math.cos(dphi))
    return -10 * math.log10(field)


class TestTwoRayGround(unittest.TestCase):
    def test_breakpoint(self):
        # d_bp = 4 h_t h_r / lambda.
        _excess, bp = run_sqf(TWO_RAY, [5000.0, 1e8, 2.0, 1.5, 0.5])
        self.assertAlmostEqual(bp, 4 * 2.0 * 1.5 / (C / 1e8), places=6)

    def test_constructive_peak_perfect_ground(self):
        # rho = 1: at the breakpoint deltaPhi = pi, F = 4, excess = -6.02 dB.
        d_bp = 4 * 2.0 * 1.5 / (C / 1e8)
        excess, _bp = run_sqf(TWO_RAY, [d_bp, 1e8, 2.0, 1.5, 1.0])
        self.assertAlmostEqual(excess, -10 * math.log10(4), places=3)

    def test_d4_far_field_slope(self):
        # rho = 1: far field, doubling d adds 20*log10(2) = 6.02 dB of
        # excess, the d^4 law.
        e1, _ = run_sqf(TWO_RAY, [20000.0, 1e8, 2.0, 1.5, 1.0])
        e2, _ = run_sqf(TWO_RAY, [40000.0, 1e8, 2.0, 1.5, 1.0])
        self.assertAlmostEqual(e2 - e1, 20 * math.log10(2), places=1)

    def test_rough_ground_saturates(self):
        # rho < 1: the far-field excess saturates at -10*log10((1-rho)^2).
        excess, _ = run_sqf(TWO_RAY, [100000.0, 1e8, 2.0, 1.5, 0.5])
        self.assertAlmostEqual(excess, -10 * math.log10(0.25), places=1)

    def test_matches_mirror(self):
        for d, f, ht, hr, rho in [
            (5000, 1e8, 2, 1.5, 0.5),
            (1000, 1e8, 2, 1.5, 0.9),
            (30000, 5e7, 5, 3, 0.7),
        ]:
            excess, _ = run_sqf(
                TWO_RAY, [float(d), float(f), float(ht), float(hr), float(rho)]
            )
            self.assertAlmostEqual(excess, two_ray_excess(d, f, ht, hr, rho), places=6)


class TestKnifeEdge(unittest.TestCase):
    def test_clear_path_zero(self):
        # v <= -0.78: the obstacle clears the line -> 0 dB.
        self.assertEqual(run_sqf(KNIFE, [-25.0]), 0.0)

    def test_reference_values(self):
        # P.526-16 eq (31): v=0 -> 6.03 dB, v=1 -> 13.93 dB.
        self.assertAlmostEqual(knife_loss(0.0), 6.03, places=1)
        self.assertAlmostEqual(knife_loss(1.0), 13.93, places=1)

    def test_matches_mirror(self):
        # The canonical kernel takes the dimensionless Fresnel parameter nu
        # (ITU-R P.526-16 eq. 31).  The geometry-to-nu step (eq. 26) lives in
        # fnc_calculateTerrainDiffraction, exercised by test_radio_terrain.
        for v in (-0.5, 0.0, 0.5, 1.0, 2.0, 3.0):
            got = run_sqf(KNIFE, [v])
            self.assertAlmostEqual(got, knife_loss(v), places=4)


class TestDeygout(unittest.TestCase):
    def test_flat_profile_zero(self):
        dists = [i * 100.0 for i in range(11)]
        heights = [0.0] * 11
        self.assertEqual(run_sqf(DEYGOUT, [dists, heights, 0.0, 0.0, 1e8]), 0.0)

    def test_single_edge_equals_knife_edge(self):
        dists = [0.0, 500.0, 1000.0]
        heights = [0.0, 50.0, 0.0]
        v = 50.0 * math.sqrt(2 * 1000 / ((C / 1e8) * 500 * 500))
        expected = knife_loss(v)
        self.assertAlmostEqual(
            run_sqf(DEYGOUT, [dists, heights, 0.0, 0.0, 1e8]), expected, places=3
        )

    def test_two_edges_exceed_single(self):
        # Two equal edges: the Deygout total exceeds one edge alone.
        dists = [0.0, 250.0, 500.0, 750.0, 1000.0]
        heights = [0.0, 40.0, 0.0, 40.0, 0.0]
        loss = run_sqf(DEYGOUT, [dists, heights, 0.0, 0.0, 1e8])
        single = knife_loss(40.0 * math.sqrt(2 * 500 / ((C / 1e8) * 250 * 250)))
        self.assertGreater(loss, 0.0)
        self.assertGreater(loss, single)

    def test_short_profile_zero(self):
        self.assertEqual(run_sqf(DEYGOUT, [[0.0, 1.0], [0.0, 0.0], 0.0, 0.0, 1e8]), 0.0)


class TestValleyWaveguide(unittest.TestCase):
    def test_below_cutoff_no_effect(self):
        # f_c = c/(2a); a = 100 m -> 1.5 MHz.  100 kHz is below cutoff.
        self.assertEqual(run_sqf(VALLEY, [100.0, 1e5, 0.0]), 0.0)

    def test_zero_width_no_effect(self):
        self.assertEqual(run_sqf(VALLEY, [0.0, 1e8, 0.0]), 0.0)

    def test_along_axis_bonus(self):
        self.assertLess(run_sqf(VALLEY, [100.0, 1e8, 0.0]), 0.0)

    def test_across_axis_penalty(self):
        self.assertGreater(run_sqf(VALLEY, [100.0, 1e8, 90.0]), 0.0)

    def test_matches_mirror(self):
        a, f, ang = 100.0, 1e8, 30.0
        fc = C / (2 * a)
        coupling = math.sqrt(1 - (fc / f) ** 2)
        expected = (
            1.5 * coupling * math.sin(math.radians(ang)) ** 2
            - 3 * coupling * math.cos(math.radians(ang)) ** 2
        )
        self.assertAlmostEqual(run_sqf(VALLEY, [a, f, ang]), expected, places=6)


if __name__ == "__main__":
    unittest.main()
