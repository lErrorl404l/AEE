#!/usr/bin/env python3
"""Local wind field tests (issue #136).

The mod's wind is a single global vector; fnc_getLocalWind.sqf makes it
SPATIAL via four mechanisms: terrain lee-side (Jackson-Hunt 1975),
building wake (ADMS-Build / Hertwig 2019), urban canyon (Oke 1988), and
aircraft wake-vortex (FAA JO 7110.126B / NASA AVOSS).  These tests lock
the physics mirrors against the spec's published validation vectors.

Run: python3 -m unittest tools.tests.test_local_wind
"""

import math
import unittest


# ─── Terrain lee-side (Jackson-Hunt 1975) ────────────────────────────────
# Crest speed-up: dS ~ 2h/L_h (a 1:5 slope doubles surface stress).
# S_terrain = 0.2 + 0.8 x (x/(10h))^0.5, clamped [0.2, 1.0] for the
# lee-side recirculation; crest speed-up capped at 1.4.
# x = distance downwind of the crest in units of h (the hill height).


def terrain_speed_up(h, l_h):
    """Windward crest speed-up: dS ~ 2h/L_h (Jackson-Hunt)."""
    return 1.0 + 2.0 * (h / l_h)


def terrain_lee_recirculation(x_h, clamp_max=1.0, clamp_min=0.2):
    """Lee-side recirculation zone: S = 0.2 + 0.8*sqrt(x/(10h))."""
    return max(clamp_min, min(clamp_max, 0.2 + 0.8 * math.sqrt(x_h / 10.0)))


# ─── Building wake (ADMS-Build, Hertwig 2019) ────────────────────────────
# Cavity length: L_R/H = 1.8 x (W_c/H)^-0.3 / (1 + 0.24 x (W_c/H)^-0.3)
# Zones: cavity 0-1.5H (reversed, -20 to -50%), near wake 1.5-5H
# (30-60%), far wake 5-15H (60-90%).
# Shadow: S(x) = 1 - 0.7 x (x/L_R)^-p, p ~1.5-2.0.


def building_cavity_length(h, w_c):
    """ADMS-Build cavity length behind the building (metres)."""
    r = (w_c / h) ** -0.3
    return h * 1.8 * r / (1 + 0.24 * r)


def building_s_factor(h, w_c, dist):
    """Composite building-wake speed factor at distance downwind."""
    l_r = building_cavity_length(h, w_c)
    x_norm = dist / h
    if x_norm < 1.5:
        return -0.35  # cavity: reversed flow (spec: -20 to -50%)
    if x_norm < 5:
        return 0.45  # near wake: 30-60%
    if x_norm < 15:
        s = 1.0 - 0.7 * (dist / l_r) ** -1.75
        return max(0.6, min(1.0, s))
    return 1.0


# ─── Urban canyon (Oke 1988) ─────────────────────────────────────────────
# Regimes by H/W: skimming >0.65, wake interference 0.4-0.65, isolated
# <0.4.  Perpendicular wind: street-level 10-20% of roof wind.  Parallel
# (channelling): S = 1.2.


def canyon_s_factor(h_w_ratio, perpendicular=True):
    """Street-level wind factor by canyon H/W regime."""
    if h_w_ratio > 0.65:  # skimming
        return 0.15 if perpendicular else 1.2
    if h_w_ratio > 0.4:  # wake interference
        return 0.5 if perpendicular else 1.1
    return 1.0  # isolated


# ─── Aircraft wake (FAA JO 7110.126B, NASA AVOSS) ────────────────────────
# Circulation Gamma0 = 4W/(pi·rho·U·b) with W in NEWTONS (mass_kg·9.81).
# The 786 m2/s B747 reference is at APPROACH speed (80 m/s ~ 155 kt):
# 4·(396890·9.81)/(pi·1.225·80·64.4) = 785.5 (Greene 1986, NASA AVOSS).
# Descent: w = Gamma0/(2·pi·b0), b0 = (pi/4)·b -> 2·786/(pi²·64.4) = 2.47 m/s.


def wake_gamma0(mass_kg, speed_ms, span_m, rho=1.225):
    """Initial vortex circulation (m^2/s).  mass in kg, W = mg."""
    w_n = mass_kg * 9.81
    return 4.0 * w_n / (math.pi * rho * speed_ms * span_m)


def wake_descent_rate(mass_kg, speed_ms, span_m, rho=1.225):
    """Vortex pair descent rate (m/s): Gamma0/(2 pi b0), b0 = (pi/4) b."""
    gamma0 = wake_gamma0(mass_kg, speed_ms, span_m, rho)
    return 2.0 * gamma0 / (math.pi ** 2 * span_m)


def wake_induced_velocity(gamma0, radius_m):
    """Induced tangential velocity at radius r (m/s), capped 3 m/s."""
    v = gamma0 / (2.0 * math.pi * max(radius_m, 3.0))
    return min(v, 3.0)


# ─── Composition ─────────────────────────────────────────────────────────
# V_local = V_global x min(S_terrain, S_building, S_canyon) + V_wake


def local_wind(global_ms, s_terrain, s_building, s_canyon, wake_v=0.0):
    """Mirror of the fnc_getLocalWind composition."""
    s_min = min(s_terrain, s_building, s_canyon)
    return global_ms * s_min + wake_v


class TestWakeVortex(unittest.TestCase):
    """FAA/NASA wake validation vectors."""

    def test_b747_circulation(self):
        # B747-400 at APPROACH: 396890 kg, 80 m/s (~155 kt), 64.4 m span.
        # The spec's 786 m2/s is this configuration (Greene 1986); the
        # formula gives 785.5.
        g = wake_gamma0(396890, 80, 64.4)
        self.assertAlmostEqual(g, 786, delta=5)

    def test_b747_descent(self):
        d = wake_descent_rate(396890, 80, 64.4)
        self.assertAlmostEqual(d, 2.47, delta=0.05)

    def test_c172_circulation_smaller(self):
        # Cessna 172: 1043 kg, 60 m/s, 11 m span -> ~16 m2/s, an order of
        # magnitude below the B747's heavy wake (FAA heavy/light).
        g = wake_gamma0(1043, 60, 11)
        self.assertLess(g, 786 / 10)
        self.assertGreater(g, 10)

    def test_induced_velocity_caps(self):
        # Close to the core the induced velocity is capped at 3 m/s.
        self.assertEqual(wake_induced_velocity(786, 1.0), 3.0)
        # Far away it decays as 1/r.
        self.assertLess(wake_induced_velocity(786, 100), wake_induced_velocity(786, 50))

    def test_gamma_scales_with_mass(self):
        g_big = wake_gamma0(200000, 250, 64.4)
        g_small = wake_gamma0(100000, 250, 64.4)
        self.assertAlmostEqual(g_big / g_small, 2.0, places=6)


class TestBuildingWake(unittest.TestCase):
    """ADMS-Build cavity/wake validation."""

    def test_cavity_length_spec(self):
        # Spec: H=20, W_c=30 -> L_R = 26.5 m.
        l_r = building_cavity_length(20, 30)
        self.assertAlmostEqual(l_r, 26.5, delta=2.0)

    def test_spec_5h_s_factor(self):
        # Spec: at 5H, S = 0.91.  5H = 100 m for H=20.
        s = building_s_factor(20, 30, 100)
        self.assertAlmostEqual(s, 0.91, delta=0.05)

    def test_cavity_reversed(self):
        # In the cavity (0-1.5H) flow is reversed (negative factor).
        s = building_s_factor(20, 30, 20)  # 1H
        self.assertLess(s, 0)
        self.assertGreater(s, -0.5)

    def test_far_wake_recovers(self):
        s_far = building_s_factor(20, 30, 280)  # 14H
        self.assertGreater(s_far, 0.6)
        self.assertLessEqual(s_far, 1.0)

    def test_beyond_wake_global(self):
        self.assertEqual(building_s_factor(20, 30, 400), 1.0)  # 20H


class TestUrbanCanyon(unittest.TestCase):
    """Oke 1988 canyon regimes."""

    def test_skimming_perpendicular(self):
        # H/W 0.8 (skimming): street wind 10-20% of roof wind.
        s = canyon_s_factor(0.8, perpendicular=True)
        self.assertAlmostEqual(s, 0.15, places=4)
        self.assertLessEqual(s, 0.2)

    def test_skimming_parallel_channels(self):
        # Parallel wind in a skimming canyon accelerates.
        s = canyon_s_factor(0.8, perpendicular=False)
        self.assertEqual(s, 1.2)


def test_regime_boundaries(self):
    # Strict > boundary: 0.66 is skimming, 0.5 wake interference, 0.3 isolated.
    self.assertEqual(canyon_s_factor(0.66, True), 0.15)  # skimming
    self.assertEqual(canyon_s_factor(0.5, True), 0.5)  # wake interference
    self.assertEqual(canyon_s_factor(0.3, True), 1.0)  # isolated


class TestTerrain(unittest.TestCase):
    """Jackson-Hunt terrain effects."""

    def test_crest_speedup(self):
        # Ridge h=100, L_h=500: S = 1.4 crest (spec).
        s = terrain_speed_up(100, 500)
        self.assertAlmostEqual(s, 1.4, delta=0.05)

    def test_lee_recirculation_spec(self):
        # Spec: S = 0.77 at 5h downwind.
        s = terrain_lee_recirculation(5)
        self.assertAlmostEqual(s, 0.77, delta=0.05)

    def test_lee_bounded(self):
        # Clamped [0.2, 1.0]: the floor binds only as x->0.
        self.assertEqual(terrain_lee_recirculation(0.0), 0.2)
        self.assertGreaterEqual(terrain_lee_recirculation(50), 0.9)


class TestComposition(unittest.TestCase):
    """The min-then-scale composition."""

    def test_strongest_reduction_wins(self):
        # Deep canyon (0.15) inside a building far wake (0.9): min = 0.15.
        v = local_wind(10, 1.0, 0.9, 0.15)
        self.assertAlmostEqual(v, 1.5, places=4)

    def test_wake_adds(self):
        v = local_wind(5, 1.0, 1.0, 1.0, wake_v=2.0)
        self.assertAlmostEqual(v, 7.0, places=4)

    def test_full_suppression(self):
        # Cavity reversal + canyon: wind near zero or negative.
        v = local_wind(5, 1.0, -0.35, 0.15)
        self.assertLess(v, 1.0)

    def test_flat_open_field_global(self):
        v = local_wind(10, 1.0, 1.0, 1.0)
        self.assertAlmostEqual(v, 10.0, places=6)


class TestSQFSync(unittest.TestCase):
    """Drift-lock the SQF against the mirrors."""

    def test_sqf_has_all_four_mechanisms(self):
        from pathlib import Path

        text = Path("addons/atmos/functions/fnc_getLocalWind.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("Jackson-Hunt", text)
        self.assertIn("ADMS-Build", text)
        self.assertIn("Oke 1988", text)
        self.assertIn("FAA JO 7110.126B", text)

    def test_sqf_validation_anchors(self):
        from pathlib import Path

        text = Path("addons/atmos/functions/fnc_getLocalWind.sqf").read_text(
            encoding="utf-8"
        )
        # Spec anchors present in the physics.
        self.assertIn("0.2 + 0.8 * sqrt", text)  # terrain lee
        self.assertIn("1.8 * (_wcRatio ^ -0.3)", text)  # cavity length
        self.assertIn("0.65", text)  # canyon skimming H/W
        self.assertIn("4 * _mass / (pi * _rho * _speed * _span)", text)  # wake gamma

    def test_sqf_composition_min(self):
        from pathlib import Path

        text = Path("addons/atmos/functions/fnc_getLocalWind.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("_terrainS min _buildingS) min _canyonS", text)


if __name__ == "__main__":
    unittest.main()
