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


def gagge_reference(tdb, tr, v, met, clo, pa_mmhg, minutes=59):
    """The ASHRAE 55-2020 reference loop, transcribed from pythermalcomfort
    `_gagge_two_nodes_optimized`.  met is in met units, pa_mmhg in mmHg.

    The oracle for the two kernel deviations this file pins: the initial
    e_skin = 0.1 * met, and q_res and c_res fixed once before the loop from
    m = met * 58.2.  Its own test proves it reproduces the held vectors, so an
    assertion against it is independent of the SQF under test.
    """
    sbc = 0.000000056697
    c_sw, c_dil, c_str = 170.0, 120.0, 0.5
    tsn, tcn, alfa = 33.7, 36.8, 0.1
    t_body_neutral = alfa * tsn + (1 - alfa) * tcn
    t_skin, t_core, m_bl = tsn, tcn, 6.3
    e_skin = 0.1 * met
    m = rm = met * 58.2
    air_speed = max(v, 0.1)
    r_clo = 0.155 * clo
    f_a_cl = 1.0 + 0.15 * clo
    lr = 2.2
    i_cl = 0.45 if clo > 0 else 1.0
    w_max = 0.59 * air_speed**-0.08 if clo > 0 else 0.38 * air_speed**-0.29
    h_cc = max(3.0, 8.600001 * (air_speed**0.53))
    if met > 0.85:
        h_cc = max(h_cc, 5.66 * (met - 0.85) ** 0.39)
    h_r = 4.7
    h_t = h_r + h_cc
    r_a = 1.0 / (f_a_cl * h_t)
    t_op = (h_r * tr + h_cc * tdb) / h_t
    q_res = 0.0023 * m * (44.0 - pa_mmhg)
    c_res = 0.0014 * m * (34.0 - tdb)
    for _ in range(minutes):
        t_cl = (r_a * t_skin + r_clo * t_op) / (r_a + r_clo)
        for _ in range(150):
            h_r = 4.0 * 0.95 * sbc * (((t_cl + tr) / 2.0 + 273.15) ** 3.0) * 0.73
            h_t = h_r + h_cc
            r_a = 1.0 / (f_a_cl * h_t)
            t_op = (h_r * tr + h_cc * tdb) / h_t
            new = (r_a * t_skin + r_clo * t_op) / (r_a + r_clo)
            if abs(new - t_cl) <= 0.01:
                t_cl = new
                break
            t_cl = new
        q_sensible = (t_skin - t_op) / (r_a + r_clo)
        hf_cs = (t_core - t_skin) * (5.28 + 1.163 * m_bl)
        s_core = m - hf_cs - q_res - c_res
        s_skin = hf_cs - q_sensible - e_skin
        t_skin += (s_skin * 1.8258) / (0.97 * alfa * 70.0 * 60.0)
        t_core += (s_core * 1.8258) / (0.97 * (1 - alfa) * 70.0 * 60.0)
        t_body = alfa * t_skin + (1 - alfa) * t_core
        sk_sig = t_skin - tsn
        warm_sk, cold_sk = max(sk_sig, 0.0), max(-sk_sig, 0.0)
        c_cold = max(tcn - t_core, 0.0)
        warm_b = max(t_body - t_body_neutral, 0.0)
        m_bl = max(
            min((6.3 + c_dil * max(t_core - tcn, 0.0)) / (1 + c_str * cold_sk), 90.0),
            0.5,
        )
        e_rsw = 0.68 * min(c_sw * warm_b * math.exp(warm_sk / 10.7), 500.0)
        r_ea = 1.0 / (lr * f_a_cl * h_cc)
        r_ecl = r_clo / (lr * i_cl)
        e_max = (math.exp(18.6686 - 4030.183 / (t_skin + 235.0)) - pa_mmhg) / (
            r_ea + r_ecl
        )
        if e_max == 0:
            e_max = 0.001
        p_rsw = e_rsw / e_max
        w = 0.06 + 0.94 * p_rsw
        e_diff = w * e_max - e_rsw
        if w > w_max:
            w = w_max
            p_rsw = w_max / 0.94
            e_rsw = p_rsw * e_max
            e_diff = 0.06 * (1.0 - p_rsw) * e_max
        if e_max < 0:
            e_diff = 0.0
            e_rsw = 0.0
        e_skin = e_rsw + e_diff
        m = rm + 19.4 * cold_sk * c_cold
        alfa = 0.0417737 + 0.7451833 / (m_bl + 0.585417)
    return t_core, t_skin


class TestGaggeReference(unittest.TestCase):
    def test_the_reference_transcription_reproduces_the_held_vectors(self):
        # The oracle used by the two tests below must first be shown to be the
        # reference, by reproducing the held vectors to four decimals.
        for c in REF["cases"]:
            with self.subTest(c=c):
                tc, ts = gagge_reference(
                    c["tdb"], c["tr"], c["v"], c["met"], c["clo"], c["pa_mmhg"]
                )
                self.assertAlmostEqual(tc, c["t_core"], places=4)
                self.assertAlmostEqual(ts, c["t_skin"], places=4)

    def test_the_initial_skin_evaporation_matches_the_reference(self):
        # Given a fresh state and one minute.  The reference starts
        # e_skin = 0.1 * met (0.1 at 1 met), which the first step replaces.
        # A start of 0.1 * 58.2 shifts the first-step skin temperature by
        # about 0.026 C, so the reference start is the pinned value.
        out = gagge([], 60, 25, 25, 0.1, 58.2, 0.6, 12)
        tc, ts = gagge_reference(25, 25, 0.1, 1.0, 0.6, 12, minutes=1)
        self.assertAlmostEqual(out[0], tc, delta=0.005)
        self.assertAlmostEqual(out[1], ts, delta=0.005)

    def test_respiration_is_fixed_before_shivering(self):
        # Given a cold, resting, non-immersed hour: shivering raises the core
        # storage rate.  The reference computes q_res and c_res once from the
        # working rate, so the kernel must not raise them with shivering.  A
        # shivering-inclusive respiration lowers the core by 0.029 C here.
        out = gagge([], 59 * 60, -10, -10, 0.2, 58.2, 0.5, 2)
        tc, _ts = gagge_reference(-10, -10, 0.2, 1.0, 0.5, 2)
        self.assertAlmostEqual(out[0], tc, delta=0.005)

    def test_reproduces_the_ashrae_reference(self):
        for c in REF["cases"]:
            with self.subTest(c=c):
                out = gagge([], 59 * 60, c["tdb"], c["tr"], c["v"], c["met"] * 58.2, c["clo"], c["pa_mmhg"])
                self.assertAlmostEqual(out[0], c["t_core"], delta=0.02)
                self.assertAlmostEqual(out[1], c["t_skin"], delta=0.02)

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
