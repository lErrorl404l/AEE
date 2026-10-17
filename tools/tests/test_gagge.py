#!/usr/bin/env python3
"""Human thermoregulation: the Gagge two-node kernel and Pandolf metabolism.

  fnc_gaggeTwoNode            reproduces the ASHRAE 55 reference (held
                              vectors from pythermalcomfort, data/physiology)
  fnc_pandolfMetabolicRate    Pandolf 1977 + Santee 2003
  fnc_pandolfTerrainFactor    Soule & Goldman 1972, Pandolf 1976 snow

Run: python3 -m unittest tools.tests.test_gagge -v
"""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

GAGGE = REPO / "addons/thermal/functions/solver/fnc_gaggeTwoNode.sqf"
PANDOLF = REPO / "addons/lib/functions/fnc_pandolfMetabolicRate.sqf"
TERRAIN = REPO / "addons/lib/functions/fnc_pandolfTerrainFactor.sqf"
REF = json.loads((REPO / "data/physiology/gagge_reference.json").read_text(encoding="utf-8"))


def gagge(state, dt, tdb, tr, v, met_w, clo, pa, ghi=0, alt=-90, exposure=0, t_water=-273, swim=False):
    return run_sqf(GAGGE, [state, dt, tdb, tr, v, met_w, clo, pa, 101325, ghi, alt, exposure, 0.7, t_water, 0, 1, swim])


class TestGaggeReference(unittest.TestCase):
    def test_reproduces_the_ashrae_reference(self):
        for c in REF["cases"]:
            with self.subTest(c=c):
                out = gagge([], 59 * 60, c["tdb"], c["tr"], c["v"], c["met"] * 58.2, c["clo"], c["pa_mmhg"])
                self.assertAlmostEqual(out[0], c["t_core"], delta=0.02)
                self.assertAlmostEqual(out[1], c["t_skin"], delta=0.02)

    def test_steps_compose(self):
        # Sixty one-minute calls equal one sixty-minute call.
        s = []
        for _ in range(59):
            s = gagge(s, 60, 35, 35, 0.5, 3 * 58.2, 0.6, 21)
        whole = gagge([], 59 * 60, 35, 35, 0.5, 3 * 58.2, 0.6, 21)
        self.assertAlmostEqual(s[0], whole[0], places=6)

    def test_rest_is_thermoneutral(self):
        out = gagge([], 4 * 3600, 25, 25, 0.1, 58.2, 0.6, 12)
        self.assertTrue(36.6 < out[0] < 37.1, out)

    def test_marching_in_heat_raises_the_core(self):
        # 400 W at 35 C, 50 % RH for 2 h: exertional heat strain.  Gagge's
        # conservative clothed critical wettedness (0.59) stores more heat
        # than ISO 7933 PHS (37.8 C); field loaded marches reach 38.5-39.5.
        out = gagge([], 2 * 3600, 35, 35, 0.5, 400 / 1.8258, 0.6, 21)
        self.assertTrue(38.0 < out[0] < 41.0, out)

    def test_the_sun_heats(self):
        shade = gagge([], 3600, 30, 30, 1.0, 150, 0.6, 15)
        sun = gagge([], 3600, 30, 30, 1.0, 150, 0.6, 15, ghi=900, alt=60, exposure=1)
        self.assertGreater(sun[1], shade[1])

    def test_immersion_follows_hayward(self):
        # Hayward, Eckerson & Collis 1975: 0.0785 - 0.0034 Tw C/min after
        # the first 15 min, 35 % faster swimming.
        for tw in (5, 10, 15):
            out = gagge([], 3600, 10, 10, 0.1, 58.2, 0.6, 6, t_water=tw)
            self.assertAlmostEqual(out[0], 36.8 - (0.0785 - 0.0034 * tw) * 45, delta=0.25)
        still = gagge([], 3600, 10, 10, 0.1, 58.2, 0.6, 6, t_water=10)
        swim = gagge([], 3600, 10, 10, 0.1, 58.2, 0.6, 6, t_water=10, swim=True)
        self.assertLess(swim[0], still[0])

    def test_warm_water_does_not_cool(self):
        out = gagge([], 3600, 25, 25, 0.1, 58.2, 0.0, 15, t_water=30)
        self.assertGreater(out[0], 36.5)


class TestPandolf(unittest.TestCase):
    @staticmethod
    def p(w, l, v, g, eta=1.0):
        return run_sqf(PANDOLF, [w, l, v, g, eta])

    def test_equation(self):
        for w, l, v, g, eta in ((70, 0, 1.34, 0, 1.0), (80, 30, 1.2, 5, 1.2), (70, 40, 0.8, 10, 1.5)):
            m = 1.5 * w + 2.0 * (w + l) * (l / w) ** 2 + eta * (w + l) * (1.5 * v * v + 0.35 * v * g)
            self.assertAlmostEqual(self.p(w, l, v, g, eta), m, places=4)

    def test_standing_with_load(self):
        self.assertAlmostEqual(self.p(70, 0, 0, 0), 105.0, places=6)

    def test_santee_downhill(self):
        w, l, v, g = 70, 20, 1.3, -10
        m = 1.5 * w + 2.0 * (w + l) * (l / w) ** 2 + (w + l) * (1.5 * v * v + 0.35 * v * g)
        cf = (g * (w + l) * v) / 3.5 - ((w + l) * (g + 6) ** 2) / w + (25 - v * v)
        self.assertAlmostEqual(self.p(w, l, v, g), m - cf, places=3)

    def test_terrain_factors(self):
        for name, eta in (("#GdtAsphalt", 1.0), ("GdtDirt", 1.1), ("GdtGrassGreen", 1.2),
                          ("GdtForestPine", 1.5), ("GdtMarsh", 1.8), ("GdtBeach", 2.1)):
            self.assertAlmostEqual(run_sqf(TERRAIN, [name, 0]), eta, places=6)
        self.assertAlmostEqual(run_sqf(TERRAIN, ["GdtGrassGreen", 0.2]), 1.30 + 0.082 * 20, places=6)


if __name__ == "__main__":
    unittest.main()
