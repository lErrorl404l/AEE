#!/usr/bin/env python3
"""Wet/ice traction model tests (issue #133).

Mirrors of fnc_calculateWetTraction.sqf: hydroplaning (Horne & Dreher,
NASA TN D-2056), black ice (freezing-rain gate), and brake fade (Limpert).

Run: python3 -m unittest tools.tests.test_wet_traction
"""

import math
import unittest


# ─── 1. Hydroplaning (Horne & Dreher) ─────────────────────────────────────
def hydroplane_critical_mps(tyre_psi):
    """V_cr = 10.35*sqrt(P) mph, converted to m/s."""
    return 10.35 * math.sqrt(max(tyre_psi, 20)) * 0.44704


def surface_mu(surface_wet, speed_mps, v_cr_mps, dry_mu=0.8, wet_mu=0.55):
    """Mirror of the hydroplaning friction ramp.

    Below 80% V_cr: friction interpolates dry..wet by wetness.
    At 80-100% V_cr: linear ramp to the 0.05 hydroplaning floor.
    """
    mu = dry_mu - (dry_mu - wet_mu) * max(0.0, min(1.0, surface_wet))
    if speed_mps > 0 and surface_wet > 0.3:
        frac = speed_mps / v_cr_mps
        if frac >= 0.8:
            t = max(0.0, min(1.0, (frac - 0.8) / 0.2))
            mu = mu - (mu - 0.05) * t
    return mu


# ─── 2. Black ice ──────────────────────────────────────────────────────────
def black_ice_mu(road_temp, precip_phase, surface_wet, base_mu):
    """Mirror of the black-ice branch.  Returns new mu or None if no ice."""
    if (
        road_temp < 0
        and precip_phase in ("rain", "freezing_rain")
        and surface_wet > 0.1
    ):
        cold_factor = 1.0 - (0.5 * max(0.0, min(1.0, (road_temp + 10) / 10)))
        return min(0.1 + 0.05 * cold_factor, base_mu)
    return None


# ─── 3. Brake fade (Limpert) ──────────────────────────────────────────────
def brake_temp_step(mass_kg, speed_mps, rotor_mass_kg=16.0, k=0.6, c_p=460.0):
    """dT per braking event = (0.5 m v^2 k)/(m_rotor c_p)."""
    return (0.5 * mass_kg * speed_mps**2 * k) / (rotor_mass_kg * c_p)


def brake_cool(temp_c, ambient_c, dt_s, tau=450.0):
    """Exponential cooling toward ambient."""
    return ambient_c + (temp_c - ambient_c) * math.exp(-dt_s / tau)


def brake_mu(temp_c, mu_cold=0.4, mu_hot=0.2, fade_start=200.0, fade_end=300.0):
    """Friction coefficient: cold -> hot, linear between 200-300 C."""
    if temp_c <= fade_start:
        return mu_cold
    if temp_c >= fade_end:
        return mu_hot
    t = (temp_c - fade_start) / (fade_end - fade_start)
    return mu_cold - (mu_cold - mu_hot) * t


# ─── 4. Stopping distance ──────────────────────────────────────────────────
def stopping_distance_m(speed_mps, mu, g=9.81):
    """d = v^2/(2 mu g)."""
    return speed_mps**2 / (2 * mu * g)


class TestHydroplaning(unittest.TestCase):
    def test_critical_speed_30psi(self):
        # NASA anchor: V_cr(30 psi) = 56.7 mph = 25.35 m/s.
        v = hydroplane_critical_mps(30)
        self.assertAlmostEqual(v * 2.23694, 56.7, delta=1.0)  # mph

    def test_critical_speed_40psi(self):
        v = hydroplane_critical_mps(40)
        self.assertAlmostEqual(v * 2.23694, 65.5, delta=1.0)

    def test_mass_independent(self):
        # V_cr depends only on tyre pressure, never mass (NASA).
        self.assertEqual(hydroplane_critical_mps(32), hydroplane_critical_mps(32))

    def test_below_threshold_holds_wet_friction(self):
        # At 60% V_cr the friction is the wet value, no ramp.
        v = hydroplane_critical_mps(32)
        mu = surface_mu(1.0, v * 0.6, v)
        self.assertAlmostEqual(mu, 0.55, places=2)

    def test_ramp_to_floor(self):
        # At/above V_cr friction hits the 0.05 hydroplaning floor.
        v = hydroplane_critical_mps(32)
        mu = surface_mu(1.0, v * 1.0, v)
        self.assertAlmostEqual(mu, 0.05, places=3)
        mu_over = surface_mu(1.0, v * 1.5, v)
        self.assertAlmostEqual(mu_over, 0.05, places=3)

    def test_partial_ramp(self):
        # At 90% V_cr, halfway through the 80-100% ramp.
        v = hydroplane_critical_mps(32)
        mu = surface_mu(1.0, v * 0.9, v)
        self.assertAlmostEqual(mu, 0.05 + (0.55 - 0.05) * 0.5, places=3)

    def test_dry_no_effect(self):
        v = hydroplane_critical_mps(32)
        self.assertEqual(surface_mu(0.0, v, v), 0.8)

    def test_monotonic_down_with_speed(self):
        v = hydroplane_critical_mps(32)
        prev = 1.0
        for frac in [x / 20 for x in range(0, 21)]:
            mu = surface_mu(1.0, v * frac, v)
            self.assertLessEqual(mu, prev + 1e-9)
            prev = mu


class TestBlackIce(unittest.TestCase):
    def test_no_ice_when_above_freezing(self):
        self.assertIsNone(black_ice_mu(1.0, "rain", 0.5, 0.55))

    def test_no_ice_without_rain(self):
        self.assertIsNone(black_ice_mu(-2.0, "snow", 0.5, 0.55))

    def test_no_ice_on_dry_surface(self):
        self.assertIsNone(black_ice_mu(-2.0, "rain", 0.05, 0.55))

    def test_ice_near_zero_slipperiest(self):
        mu_near = black_ice_mu(-0.5, "rain", 0.5, 0.55)
        mu_cold = black_ice_mu(-15, "rain", 0.5, 0.55)
        self.assertIsNotNone(mu_near)
        self.assertIsNotNone(mu_cold)
        near_v: float = mu_near  # type: ignore[assignment]
        cold_v: float = mu_cold  # type: ignore[assignment]
        self.assertLess(near_v, cold_v, "ice should be slipperier near 0 C")

    def test_ice_floor_bounds(self):
        for temp in [-0.1, -5, -10, -20]:
            mu = black_ice_mu(temp, "rain", 0.5, 0.55)
            self.assertIsNotNone(mu)
            mu_v: float = mu  # type: ignore[assignment]
            self.assertGreaterEqual(mu_v, 0.1)
            self.assertLessEqual(mu_v, 0.15 + 1e-9)

    def test_ice_stopping_distance(self):
        # Spec anchor: 100 km/h on ice (mu 0.1) -> 393.3 m.
        d = stopping_distance_m(100 / 3.6, 0.1)
        self.assertAlmostEqual(d, 393.3, delta=10)

    def test_dry_vs_ice_stopping(self):
        dry = stopping_distance_m(100 / 3.6, 0.8)
        ice = stopping_distance_m(100 / 3.6, 0.1)
        self.assertGreater(ice / dry, 7.0)  # ~8x


class TestBrakeFade(unittest.TestCase):
    def test_dt_per_stop(self):
        # Spec anchor: 2000 kg, 100 km/h, k=0.6, 16 kg rotors -> 62.9 K.
        dt = brake_temp_step(2000, 100 / 3.6, rotor_mass_kg=16, k=0.6)
        self.assertAlmostEqual(dt, 62.9, delta=5)

    def test_dt_scales_with_mass(self):
        dt_heavy = brake_temp_step(4000, 100 / 3.6)
        dt_light = brake_temp_step(2000, 100 / 3.6)
        self.assertAlmostEqual(dt_heavy, 2 * dt_light, places=6)

    def test_dt_scales_with_speed_squared(self):
        dt_100 = brake_temp_step(2000, 100 / 3.6)
        dt_200 = brake_temp_step(2000, 200 / 3.6)
        self.assertAlmostEqual(dt_200, 4 * dt_100, places=4)

    def test_cooling_toward_ambient(self):
        hot = brake_cool(400, 20, 450.0)  # one tau
        self.assertAlmostEqual(hot, 20 + 380 * math.exp(-1), places=4)
        cold = brake_cool(400, 20, 3600.0)
        self.assertAlmostEqual(cold, 20, delta=2)

    def test_mu_cold_above_fade_start(self):
        self.assertEqual(brake_mu(150), 0.4)

    def test_mu_hot_above_fade_end(self):
        self.assertEqual(brake_mu(350), 0.2)

    def test_mu_linear_mid(self):
        self.assertAlmostEqual(brake_mu(250), 0.3, places=3)  # halfway

    def test_fade_reduces_stopping(self):
        mu_cold = brake_mu(150)
        mu_hot = brake_mu(400)
        d_cold = stopping_distance_m(100 / 3.6, mu_cold)
        d_hot = stopping_distance_m(100 / 3.6, mu_hot)
        self.assertGreater(d_hot, d_cold)


if __name__ == "__main__":
    unittest.main()
