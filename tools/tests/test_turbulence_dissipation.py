#!/usr/bin/env python3
"""Boundary-layer dissipation (fnc_turbulenceDissipation): Monin-Obukhov
surface layer and convective mixed-layer scaling.

Run: python3 -m unittest tools.tests.test_turbulence_dissipation -v
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

K = REPO / "addons/atmos/functions/physics/fnc_turbulenceDissipation.sqf"


def diss(u10, z, z0=0.03, dt=0.0, tc=15.0, rho=1.225, lat=45.0, zi=1000.0):
    return run_sqf(K, [u10, z, z0, dt, tc, rho, lat, zi])


class TestDissipation(unittest.TestCase):
    def test_neutral_log_law(self):
        eps, edr, _l, ustar, _cn2 = diss(10, 10)
        u = 0.4 * 10 / math.log(10 / 0.03)
        self.assertAlmostEqual(ustar, u, places=6)
        self.assertAlmostEqual(eps, u ** 3 / (0.4 * 10), places=6)
        self.assertAlmostEqual(edr, eps ** (1 / 3), places=6)

    def test_rougher_ground_is_more_turbulent(self):
        self.assertGreater(diss(10, 30, z0=1.0)[0], diss(10, 30, z0=0.03)[0])

    def test_stable_night_layer(self):
        # Surface 5 K below the air: L > 0 and phi = 1 + 5 z/L.
        eps, _edr, lob, ustar, _cn2 = diss(5, 10, dt=-5, tc=0, rho=1.27)
        self.assertGreater(lob, 0)
        zeta = min(10 / lob, 1)
        self.assertAlmostEqual(eps, ustar ** 3 * (1 + 5 * zeta) / (0.4 * 10), places=6)

    def test_convective_mixed_layer(self):
        # Hot ground: H > 0, mid mixed layer eps = 0.4 w*^3 / z_i.
        u, z0, dt, tc, rho, zi = 3, 0.03, 15, 30, 1.15, 1500
        eps = diss(u, 500, z0, dt, tc, rho, 30, zi)[0]
        lnm = math.log(10 / z0)
        ch = 0.16 / (lnm * math.log(10 / (z0 / 10)))
        h = rho * 1004 * ch * u * dt
        wstar = (9.80665 * h * zi / (rho * 1004 * (tc + 273.15))) ** (1 / 3)
        self.assertAlmostEqual(eps, 0.4 * wstar ** 3 / zi, places=6)

    def test_wyngaard_optical_turbulence(self):
        u, z, z0, dt, tc, rho = 3, 2, 0.03, 10, 25, 1.18
        out = run_sqf(K, [u, z, z0, dt, tc, rho, 45, 1200, 1013.25])
        lnm = math.log(10 / z0)
        ustar = 0.4 * u / lnm
        ch = 0.16 / (lnm * math.log(10 / (z0 / 10)))
        h = rho * 1004 * ch * u * dt
        tk = tc + 273.15
        lob = -(ustar ** 3) * tk * rho * 1004 / (0.4 * 9.80665 * h)
        tstar = -h / (rho * 1004 * ustar)
        ct2 = 4.9 * tstar ** 2 * z ** (-2 / 3) * (1 - 7 * z / lob) ** (-2 / 3)
        cn2 = (79e-6 * 1013.25 / tk ** 2) ** 2 * ct2
        self.assertAlmostEqual(out[4] / cn2, 1.0, places=6)

    def test_neutral_air_has_no_optical_turbulence(self):
        self.assertEqual(run_sqf(K, [5, 2, 0.03, 0, 15, 1.22, 45, 1000, 1013.25])[4], 0)

    def test_above_the_neutral_layer_is_calm(self):
        # h = 0.25 u* / f; well above it the clear air is still.
        self.assertEqual(diss(5, 5000)[0], 0)


if __name__ == "__main__":
    unittest.main()
