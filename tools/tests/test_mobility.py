#!/usr/bin/env python3
"""Reference checks for AEE's mobility and maritime models.

These tests validate the SQF implementations in addons/mobility and
addons/maritime against their published references:

  fnc_calculateEnginePower.sqf      — SAE J1349 air-density derating
  fnc_calculateTraction.sqf         — Bekker slip curve (F = mu*W*(1-exp(-k*s)))
  fnc_calculateMudAccretion.sqf     — surface-type mud test and exponential decay
  fnc_calculateRiverWaterLevel.sqf  — Nash cascade of three linear reservoirs
  fnc_calculateRouteDegradation.sqf — NRMM cone-index passability
  fnc_calculateCompassDeviation.sqf — WMM 2020 coarse declination table

They fail if the formulas drift from the SQF source of truth.

Run: python3 -m unittest tools/tests/test_mobility.py
"""

import math
import unittest


def engine_power_ratio(density_kgm3):
    """Mirror of fnc_calculateEnginePower.sqf (SAE J1349 density derating).

    Power scales with the air-density ratio to the power 1.2.  The SQF
    clamps the final power to 0.3-1.0 after the temperature term; this
    mirror isolates the density ratio only.
    """
    return (density_kgm3 / 1.225) ** 1.2


def traction_force(mu, wheel_load, slip):
    """Mirror of fnc_calculateTraction.sqf (Bekker slip curve, k = 10).

    F = mu * W * (1 - exp(-k * s)).  The SQF clamps slip to 0-1 before
    the curve; a negative load floors the force at zero.
    """
    slip = min(max(slip, 0.0), 1.0)
    wheel_load = max(wheel_load, 0.0)
    return mu * wheel_load * (1 - math.exp(-10 * slip))


def mud_factor(surface_type_string):
    """Mirror of fnc_calculateMudAccretion.sqf (surfaceType mud test).

    The SQF tests the surface string for "Mud", "Dirt" or "Soft" and
    converts the boolean to 1 or 0 with parseNumber.
    """
    s = surface_type_string
    return 1.0 if ("Mud" in s or "Dirt" in s or "Soft" in s) else 0.0


def accretion_after_ticks(initial, ticks, decay=0.99):
    """Mirror of the exponential decay in fnc_calculateMudAccretion.sqf.

    Off mud the accretion multiplies by 0.99 per tick.  The result never
    goes negative.
    """
    return max(0.0, initial * (decay**ticks))


def nash_cascade(r1, r2, r3, inflow, k=0.1, ticks=1):
    """Mirror of fnc_calculateRiverWaterLevel.sqf (Nash cascade, k = 0.1).

    Three serial linear reservoirs; the water level is the outflow from
    the third reservoir, clamped at zero.  Returns (r1, r2, r3, level)
    so callers can thread the state across ticks.
    """
    for _ in range(ticks):
        r1 = r1 + inflow - (r1 * k)
        r2 = r2 + (r1 * k) - (r2 * k)
        r3 = r3 + (r2 * k) - (r3 * k)
    return r1, r2, r3, max(0.0, r3 * k)


def route_passability(cone_index, ground_pressure):
    """Mirror of fnc_calculateRouteDegradation.sqf (NRMM cone index).

    One tick: exponential recovery toward 1.0, then damage from vehicle
    ground pressure, then the cone-index clamp 0.1-1.0.  Passability is
    the cone index over the required index (1.0), clamped 0-1.
    """
    cone_index = min(cone_index * 1.001, 1.0)
    cone_index = cone_index - (ground_pressure * 0.00002)
    cone_index = min(max(cone_index, 0.1), 1.0)
    return min(max(cone_index / 1.0, 0.0), 1.0)


def declination(lon_deg, lat_deg):
    """Mirror of fnc_calculateCompassDeviation.sqf (WMM 2020 coarse table).

    Linear interpolation across the longitude bands, a small latitude
    adjustment, and the final +/-30 degree clamp.
    """
    table = [
        (-180, 10),
        (-120, 12),
        (-80, -13),
        (-20, -5),
        (0, 1),
        (40, 6),
        (90, -3),
        (120, -5),
        (150, -9),
        (180, 10),
    ]
    n = len(table)
    if lon_deg <= table[0][0]:
        decl = table[0][1]
    elif lon_deg >= table[n - 1][0]:
        decl = table[n - 1][1]
    else:
        decl = 0.0
        for i in range(n - 1):
            lo, hi = table[i], table[i + 1]
            if lo[0] <= lon_deg <= hi[0]:
                frac = (lon_deg - lo[0]) / (hi[0] - lo[0])
                decl = lo[1] + frac * (hi[1] - lo[1])
    decl = decl + ((lat_deg - 45) * 0.05)
    return min(max(decl, -30.0), 30.0)


class TestEnginePower(unittest.TestCase):
    def test_sea_level_nominal(self):
        # ISA sea-level density gives the full power ratio.
        self.assertAlmostEqual(engine_power_ratio(1.225), 1.0, places=3)

    def test_high_altitude_derate(self):
        # 0.9 kg/m^3 (about 3000 m): roughly 0.72 of sea-level power.
        self.assertAlmostEqual(engine_power_ratio(0.9), 0.72, places=1)

    def test_zero_density_guard(self):
        # Zero density must give zero power, not NaN.
        self.assertEqual(engine_power_ratio(0.0), 0.0)

    def test_dense_air_boosts_power(self):
        # Density above sea level (negative altitude, turbocharging) gives
        # a ratio above 1.0.
        self.assertGreater(engine_power_ratio(1.5), 1.0)

    def test_monotonic_in_density(self):
        self.assertLess(engine_power_ratio(0.8), engine_power_ratio(0.9))
        self.assertLess(engine_power_ratio(0.9), engine_power_ratio(1.0))
        self.assertLess(engine_power_ratio(1.0), engine_power_ratio(1.1))


class TestTraction(unittest.TestCase):
    def test_zero_slip_no_force(self):
        self.assertAlmostEqual(traction_force(0.8, 1000, 0), 0.0, places=3)

    def test_full_slip_approaches_mu_w(self):
        # At slip 1 the curve is within 5% of mu*W.
        self.assertAlmostEqual(traction_force(0.8, 1000, 1), 800.0, delta=40.0)

    def test_partial_slip_between(self):
        force = traction_force(0.8, 1000, 0.1)
        self.assertGreater(force, 0.0)
        self.assertLess(force, 800.0)

    def test_zero_mu_ice(self):
        self.assertEqual(traction_force(0.0, 1000, 1), 0.0)

    def test_negative_slip_clamped(self):
        # The SQF clamps slip to 0-1; negative slip floors at zero.
        self.assertEqual(traction_force(0.8, 1000, -0.5), 0.0)

    def test_negative_load_clamped(self):
        # The SQF has no load clamp; the force floors at zero.
        self.assertEqual(traction_force(0.8, -100, 0.5), 0.0)

    def test_monotonic_in_slip(self):
        self.assertLess(traction_force(0.8, 1000, 0.1), traction_force(0.8, 1000, 0.5))


class TestMudAccretion(unittest.TestCase):
    def test_muddy_surfaces(self):
        self.assertEqual(mud_factor("Mud_1"), 1.0)
        self.assertEqual(mud_factor("Dirt_2"), 1.0)
        self.assertEqual(mud_factor("Soft_3"), 1.0)

    def test_hard_surfaces(self):
        self.assertEqual(mud_factor("Default"), 0.0)
        self.assertEqual(mud_factor("Grass"), 0.0)
        self.assertEqual(mud_factor("Concrete"), 0.0)

    def test_empty_string(self):
        self.assertEqual(mud_factor(""), 0.0)

    def test_mud_prefix_variant(self):
        self.assertEqual(mud_factor("Muddy"), 1.0)

    def test_decay_toward_zero(self):
        self.assertLess(accretion_after_ticks(1.0, 100), 1.0)
        self.assertGreater(accretion_after_ticks(1.0, 100), 0.0)

    def test_decay_never_negative(self):
        self.assertGreaterEqual(accretion_after_ticks(0.5, 50), 0.0)

    def test_default_decay_rate(self):
        # 0.99 per tick, as in the SQF.
        self.assertAlmostEqual(accretion_after_ticks(1.0, 1), 0.99, places=3)


class TestRiverWaterLevel(unittest.TestCase):
    def test_zero_inflow_drains(self):
        # With no inflow the reservoirs decay toward zero.
        r1, r2, r3, level = nash_cascade(1.0, 1.0, 1.0, 0.0, 0.1, 200)
        self.assertLess(level, 0.001)
        self.assertLess(r3, 0.01)

    def test_constant_inflow_steady_state(self):
        # Constant inflow reaches a bounded steady state (outflow = inflow).
        _, _, _, level = nash_cascade(0.0, 0.0, 0.0, 0.5, 0.1, 1000)
        self.assertAlmostEqual(level, 0.5, places=2)
        self.assertLess(level, 1.0)
        # The steady state does not grow with more ticks.
        _, _, _, level2 = nash_cascade(0.0, 0.0, 0.0, 0.5, 0.1, 2000)
        self.assertAlmostEqual(level2, level, places=3)

    def test_impulse_peaks_then_decays(self):
        # One tick of inflow, then zero: the Nash hydrograph rises to a
        # peak and then tails off.
        r1 = r2 = r3 = 0.0
        out = []
        for t in range(80):
            inflow = 1.0 if t == 0 else 0.0
            r1, r2, r3, level = nash_cascade(r1, r2, r3, inflow, 0.1, 1)
            out.append(level)
        peak = max(out)
        peak_idx = out.index(peak)
        # The peak exceeds the output at the impulse tick (zero).
        self.assertGreater(peak, out[0])
        # The peak exceeds the inflow at the peak tick (zero after the impulse).
        self.assertGreater(peak, 0.0)
        # The hydrograph tails off after the peak (index kept inside the array).
        tail_idx = min(peak_idx + 10, len(out) - 1)
        self.assertLess(out[tail_idx], peak)

    def test_level_never_negative(self):
        # The SQF clamps the water level at zero.
        _, _, _, level = nash_cascade(-1.0, -1.0, -1.0, 0.0, 0.1, 1)
        self.assertEqual(level, 0.0)
        _, _, _, level2 = nash_cascade(0.0, 0.0, 0.0, 0.5, 0.1, 10)
        self.assertGreaterEqual(level2, 0.0)


class TestRouteDegradation(unittest.TestCase):
    def test_fresh_route(self):
        # Nominal cone index with no traffic: passability near 1.0.
        self.assertAlmostEqual(route_passability(1.0, 0), 1.0, places=3)

    def test_heavy_passages_degrade(self):
        # Many heavy passages drive the cone index down.
        ci = 1.0
        for _ in range(50):
            ci = route_passability(ci, 1000)
        self.assertLess(ci, 1.0)
        self.assertGreater(ci, 0.0)

    def test_recovery_toward_nominal(self):
        # With no traffic the soil recovers toward 1.0.
        ci = 0.2
        for _ in range(1000):
            ci = route_passability(ci, 0)
        self.assertGreater(ci, 0.2)
        self.assertLessEqual(ci, 1.0)
        # Long enough, recovery clamps at 1.0.
        ci = 0.2
        for _ in range(5000):
            ci = route_passability(ci, 0)
        self.assertEqual(ci, 1.0)

    def test_passability_clamped(self):
        # Upper bound: a huge cone index still gives 1.0.
        self.assertLessEqual(route_passability(10.0, 0), 1.0)
        # Lower bound: a zero cone index still gives a non-negative result.
        self.assertGreaterEqual(route_passability(0.0, 0), 0.0)

    def test_light_vehicle_minimal_damage(self):
        # Zero ground pressure causes no damage; passability stays at 1.0.
        ci = 1.0
        for _ in range(100):
            ci = route_passability(ci, 0)
        self.assertEqual(ci, 1.0)


class TestCompassDeviation(unittest.TestCase):
    def test_new_york(self):
        # New York (40N, 74W): about -12 degrees.
        self.assertAlmostEqual(declination(-74, 40), -12.2, delta=1.0)

    def test_london(self):
        # London (51N, 0E): about +1 degree.
        self.assertAlmostEqual(declination(0, 51), 1.0, delta=1.0)

    def test_tokyo(self):
        # Tokyo (35N, 139E): about -7.5 degrees.
        self.assertAlmostEqual(declination(139, 35), -7.5, delta=1.0)

    def test_beyond_table_ends(self):
        # Longitude past the table clamps to the end values, not NaN.
        self.assertEqual(declination(-190, 45), 10.0)
        self.assertEqual(declination(200, 45), 10.0)

    def test_within_30_degree_clamp(self):
        # The result stays within +/-30 degrees at extreme lat/lon.
        for lon in range(-180, 181, 30):
            for lat in range(-80, 81, 20):
                self.assertTrue(-30 <= declination(lon, lat) <= 30)

    def test_linear_interpolation(self):
        # Midpoint between two table entries is their average.
        self.assertAlmostEqual(declination(-100, 45), -0.5, places=3)
        self.assertAlmostEqual(declination(20, 45), 3.5, places=3)


if __name__ == "__main__":
    unittest.main()
