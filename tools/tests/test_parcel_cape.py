#!/usr/bin/env python3
"""Parcel CAPE (fnc_calculateParcelCape): parcel theory against an ICAO
standard-atmosphere environment, checked against an independent integration.

Run: python3 -m unittest tools.tests.test_parcel_cape -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

KERNEL = REPO / "addons/atmos/functions/physics/fnc_calculateParcelCape.sqf"


def es(t):
    return 6.112 * math.exp(17.67 * t / (t + 243.5))


def reference(tc, rh, ps=1013.25, dz=1.0):
    g, rd, cp, lv, eps = 9.80665, 287.04, 1004.0, 2.501e6, 0.622
    e = rh / 100 * es(tc)
    ln = math.log(e / 6.112)
    td = 243.5 * ln / (17.67 - ln) + 273.15
    tk = tc + 273.15
    tl = 1 / (1 / (td - 56) + math.log(tk / td) / 800) + 56
    zl = (tk - tl) / 0.0098
    cape, tp, z = 0.0, tk, 0.0
    while z <= 16000:
        te = tk - 0.0065 * min(z, 11000)
        if z < 11000:
            p = ps * (1 - 0.0065 * z / tk) ** 5.2559
        else:
            p = (
                ps
                * (1 - 0.0065 * 11000 / tk) ** 5.2559
                * math.exp(-g * (z - 11000) / (rd * (tk - 71.5)))
            )
        if z <= zl:
            tp = tk - 0.0098 * z
        elif z - dz < zl:
            tp = tl
            ews = es(tp - 273.15)
            rs = eps * ews / (p - ews)
            gm = (
                g
                * (1 + lv * rs / (rd * tp))
                / (cp + lv * lv * rs * eps / (rd * tp * tp))
            )
            tp -= gm * (z - zl)
        else:
            ews = es(tp - 273.15)
            rs = eps * ews / (p - ews)
            gm = (
                g
                * (1 + lv * rs / (rd * tp))
                / (cp + lv * lv * rs * eps / (rd * tp * tp))
            )
            tp -= gm * dz
        b = g * (tp - te) / te
        if b > 0:
            cape += b * dz
        z += dz
    return cape, zl


class TestParcelCape(unittest.TestCase):
    def test_matches_a_fine_integration(self):
        for tc, rh in ((30, 70), (25, 80), (30, 50)):
            cape, zl, w, _lnb = run_sqf(KERNEL, [tc, rh, 1013.25])
            ref, rzl = reference(tc, rh)
            self.assertAlmostEqual(zl, rzl, places=3)
            self.assertAlmostEqual(cape, ref, delta=max(15, 0.03 * ref))
            self.assertAlmostEqual(w, math.sqrt(2 * cape), places=6)

    def test_lcl_is_about_125_m_per_degree_of_dew_point_depression(self):
        # Espy: z_LCL ~ 125 m per K of (T - Td).
        _cape, zl, _w, _lnb = run_sqf(KERNEL, [20, 50, 1013.25])
        e = 0.5 * es(20)
        ln = math.log(e / 6.112)
        td = 243.5 * ln / (17.67 - ln)
        self.assertAlmostEqual(zl / (20 - td), 125, delta=8)

    def test_cool_or_dry_air_is_stable(self):
        for tc, rh in ((15, 50), (5, 90), (35, 20)):
            self.assertEqual(run_sqf(KERNEL, [tc, rh, 1013.25])[0], 0)

    def test_humid_tropical_air_is_strongly_unstable(self):
        self.assertGreater(run_sqf(KERNEL, [30, 75, 1013.25])[0], 2000)

    def test_the_lnb_is_the_top_of_the_positive_area(self):
        # The 4th return element is the level of neutral buoyancy: 0 for a
        # parcel that is never buoyant above its LCL, and above the LCL for an
        # unstable one.  The lightning ice gate consumes it (issue #238).
        self.assertEqual(run_sqf(KERNEL, [15, 50, 1013.25])[3], 0)
        _cape, zl, _w, lnb = run_sqf(KERNEL, [30, 75, 1013.25])
        self.assertGreater(lnb, zl)


if __name__ == "__main__":
    unittest.main()
