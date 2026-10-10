#!/usr/bin/env python3
"""Frost heave model tests (issue #20).

Runs the REAL SQF kernels through the SQF lite interpreter and pins them to
the sourced constants.  The kernels are pure: no missionNamespace, no
GVAR/EGVAR, no engine command.

Kernels under addons/mobility/functions/heave/:
  fnc_calculateFrostHeave   in-situ expansion + ice-lens segregation
  fnc_differentialHeave     road-vs-field differential
  fnc_heaveTerrainPoints    the grid for the engine setTerrainHeight command

The sourced anchors:

  In-situ (closed-system) heave: H_in = (rho_w/rho_i - 1) * theta * z.
      rho_w 999.84 kg/m3 at 0 C (IAPWS R6-95; Tanaka et al. 2001),
      rho_i 916.8 kg/m3 at 0 C (CRC Handbook).  Ratio 999.84 / 916.8 - 1 =
      0.09058.  TM 5-852-6 / AFR 88-19 Vol 6 (1988) para 2-2d states the same
      9 per cent from 62.4 / 57.2 lb/ft3.
  Segregation (open-system) heave: H_seg = (rho_w/rho_i) * SP * grad T * t.
      SP is the segregation potential (Konrad and Morgenstern 1981, Can.
      Geotech. J. 18(4):482-491); the one sourced value is the Devon silt
      lower bound 1.0e-9 m2/(s.degC).  grad T is the temperature gradient
      across the frozen soil (degC/m) and t the freezing duration (s).

Run: python3 -m unittest tools.tests.test_frost_heave -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from sqf_lite import run_sqf  # noqa: E402

HEAVE = REPO / "addons" / "mobility" / "functions" / "heave"
CALC = HEAVE / "fnc_calculateFrostHeave.sqf"
DIFF = HEAVE / "fnc_differentialHeave.sqf"
TERRAIN = HEAVE / "fnc_heaveTerrainPoints.sqf"

RHO_W = 999.84  # kg/m3, IAPWS R6-95
RHO_I = 916.8  # kg/m3, CRC Handbook
EXPANSION = RHO_W / RHO_I - 1
RATIO = RHO_W / RHO_I
SP_SILT = 1.0e-9  # m2/(s.degC), Devon silt (Konrad and Morgenstern 1981)


def heave(soil, z, grad=0.0, t=0.0, mult=1.0):
    keys = ["total", "inSitu", "segregated"]
    return dict(zip(keys, run_sqf(CALC, [soil, z, grad, t, mult])))


def differential(soil, z, grad, t, theta_field, theta_road, mult=1.0):
    keys = ["dH", "field", "road"]
    return dict(
        zip(keys, run_sqf(DIFF, [soil, z, grad, t, theta_field, theta_road, mult]))
    )


def terrain(centre, radius, h, step):
    return run_sqf(TERRAIN, [centre, radius, h, step])


class TestInSituHeave(unittest.TestCase):
    """The closed-system 9 per cent expansion, fully sourced."""

    def test_expansion_ratio_is_nine_per_cent(self):
        # 999.84 / 916.8 - 1 = 0.09058, the 9 per cent of TM 5-852-6.
        self.assertAlmostEqual(EXPANSION, 0.09058, places=4)

    def test_silt_loam_in_situ(self):
        # ground theta 0.25, z 1 m.
        r = heave("ground", 1.0)
        self.assertAlmostEqual(r["inSitu"], EXPANSION * 0.25, places=9)
        self.assertAlmostEqual(r["inSitu"], 0.022645, places=5)
        self.assertEqual(r["segregated"], 0)
        self.assertAlmostEqual(r["total"], r["inSitu"], places=9)

    def test_rock_has_little_water(self):
        # rock theta 0.10.
        r = heave("rock", 1.0)
        self.assertAlmostEqual(r["inSitu"], EXPANSION * 0.10, places=9)

    def test_vegetation_holds_more_water(self):
        # vegetation theta 0.35.
        r = heave("vegetation", 1.0)
        self.assertAlmostEqual(r["inSitu"], EXPANSION * 0.35, places=9)

    def test_no_frost_no_heave(self):
        self.assertEqual(run_sqf(CALC, ["ground", 0.0, 50.0, 1000.0, 1.0]), [0, 0, 0])
        self.assertEqual(run_sqf(CALC, ["ground", -1.0, 50.0, 1000.0, 1.0]), [0, 0, 0])


class TestSegregationHeave(unittest.TestCase):
    """The open-system ice-lens term (Konrad and Morgenstern 1981)."""

    def test_silt_segregates(self):
        # ground, grad 50 degC/m, 50 days: H_seg = 1.0906 * 1e-9 * 50 * 4.32e6.
        r = heave("ground", 1.0, 50.0, 50 * 86400.0)
        self.assertAlmostEqual(
            r["segregated"], RATIO * SP_SILT * 50.0 * (50 * 86400.0), places=9
        )
        self.assertAlmostEqual(r["segregated"], 0.2356, places=3)

    def test_total_is_in_situ_plus_segregated(self):
        r = heave("ground", 1.0, 50.0, 50 * 86400.0)
        self.assertAlmostEqual(r["total"], r["inSitu"] + r["segregated"], places=9)

    def test_open_system_lands_in_the_issue_range(self):
        # The issue cites 5-30 cm for silty soil; the two-term value lands there.
        r = heave("ground", 1.5, 40.0, 60 * 86400.0)
        self.assertGreater(r["total"], 0.05)
        self.assertLess(r["total"], 0.30)

    def test_rock_does_not_segregate(self):
        # No sourced SP for rock; its heave is the in-situ term only.
        r = heave("rock", 1.0, 50.0, 50 * 86400.0)
        self.assertEqual(r["segregated"], 0)
        self.assertAlmostEqual(r["total"], r["inSitu"], places=9)

    def test_no_gradient_no_segregation(self):
        r = heave("ground", 1.0, 0.0, 50 * 86400.0)
        self.assertEqual(r["segregated"], 0)

    def test_multiplier_scales_the_total(self):
        full = heave("ground", 1.0, 50.0, 50 * 86400.0, 1.0)["total"]
        half = heave("ground", 1.0, 50.0, 50 * 86400.0, 0.5)["total"]
        self.assertAlmostEqual(half, full * 0.5, places=9)


class TestDifferentialHeave(unittest.TestCase):
    """Road-vs-field differential, driven by the moisture difference."""

    def test_drier_road_heaves_less(self):
        # In-situ only (grad 0): dH = expansion * z * (theta_field - theta_road).
        r = differential("ground", 1.0, 0.0, 0.0, 0.30, 0.15)
        self.assertAlmostEqual(r["dH"], EXPANSION * 1.0 * (0.30 - 0.15), places=9)
        self.assertGreater(r["field"], r["road"])

    def test_equal_moisture_no_differential(self):
        r = differential("ground", 1.0, 0.0, 0.0, 0.25, 0.25)
        self.assertAlmostEqual(r["dH"], 0.0, places=12)

    def test_no_frost_no_differential(self):
        self.assertEqual(
            run_sqf(DIFF, ["ground", 0.0, 0.0, 0.0, 0.3, 0.15, 1.0]), [0, 0, 0]
        )


class TestHeaveTerrainGrid(unittest.TestCase):
    """The setTerrainHeight grid: a tapered rise, not a cliff."""

    def test_centre_raised_by_full_heave(self):
        pts = terrain([0, 0, 10], 4, 0.1, 2)
        centre = [p for p in pts if p[0] == 0 and p[1] == 0]
        self.assertEqual(len(centre), 1)
        self.assertAlmostEqual(centre[0][2], 10.1, places=9)

    def test_edge_returns_to_baseline(self):
        pts = terrain([0, 0, 10], 4, 0.1, 2)
        edge = [p for p in pts if abs((p[0] ** 2 + p[1] ** 2) ** 0.5 - 4.0) < 1e-9]
        self.assertEqual(len(edge), 4)
        for p in edge:
            self.assertAlmostEqual(p[2], 10.0, places=9)

    def test_bad_input_returns_empty(self):
        self.assertEqual(terrain([0, 0, 0], 0, 0.1, 2), [])
        self.assertEqual(terrain([0, 0, 0], 4, 0.0, 2), [])
        self.assertEqual(terrain([0, 0, 0], 4, 0.1, 0), [])


if __name__ == "__main__":
    unittest.main()
