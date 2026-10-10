#!/usr/bin/env python3
"""Fuel consumption and coolant thermal management checks (issue #111).

The kernel tests PARSE the real SQF and re-derive the physics from the
constants in the file they test, so a wrong constant in either place fails.
A hand-transcribed mirror is not acceptable.

Sources held for the constants:
  road load and rolling resistance   Gillespie, Fundamentals of Vehicle
                                     Dynamics (the road-load equation).
  BSFC, fuel properties, heat share  Heywood, Internal Combustion Engine
                                     Fundamentals (BSFC maps, fuel properties,
                                     the one-third coolant rejection).
  density correction                 SAE J1349, the standard the existing
                                     engine power model already cites.

Run: python3 -m unittest tools.tests.test_fuel_consumption -v
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation import validate_fuel_data as validator  # noqa: E402

ROAD_LOAD = REPO / "addons/vehicles/functions/fnc_calculateRoadLoad.sqf"
FUEL_RATE = REPO / "addons/vehicles/functions/fnc_calculateFuelRate.sqf"
COOLANT_TEMP = REPO / "addons/vehicles/functions/fnc_calculateCoolantTemperature.sqf"
COOLANT_DERATE = REPO / "addons/vehicles/functions/fnc_calculateCoolantDerate.sqf"
DRIVER = REPO / "addons/vehicles/functions/fnc_updateFuelConsumption.sqf"
DATA = REPO / "data/physics/fuel.json"
GEN = REPO / "addons/vehicles/functions/fnc_getFuelData.sqf"


def _code(text: str) -> str:
    """Strip block and line comments so a search cannot match the prose."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "\n".join(line.split("//")[0] for line in text.split("\n"))


ROAD_SRC = _code(ROAD_LOAD.read_text(encoding="utf-8"))
FUEL_SRC = _code(FUEL_RATE.read_text(encoding="utf-8"))
COOLTEMP_SRC = _code(COOLANT_TEMP.read_text(encoding="utf-8"))
DERATE_SRC = _code(COOLANT_DERATE.read_text(encoding="utf-8"))
DRIVER_SRC = _code(DRIVER.read_text(encoding="utf-8"))


def _sqf_number(src: str, pattern: str) -> float:
    match = re.search(pattern, src)
    if not match:
        raise AssertionError(f"SQF no longer matches {pattern!r}")
    return float(match.group(1))


# ─── First-principles re-derivations ───────────────────────────────────────


def road_load_force(mass, speed, accel, crr, grade_sin, drag_area, rho, g):
    return (
        crr * mass * g
        + 0.5 * rho * drag_area * abs(speed) ** 2
        + mass * g * grade_sin
        + mass * accel
    )


def fuel_rate_lph(idle_w, drive_w, bsfc, density):
    return bsfc * ((max(idle_w, 0) + max(drive_w, 0)) / 1000) / density


def fuel_mass_rate_kgs(rate_lph, density):
    return rate_lph * density / 3.6e6


def range_km(capacity_l, fuel_fraction, rate_lph, speed_kmh):
    return (capacity_l * fuel_fraction * speed_kmh) / rate_lph


def coolant_new(t_amb, q_reject, ua, tau, t_cool, dt):
    t_inf = t_amb + q_reject / ua
    return t_inf + (t_cool - t_inf) * math.exp(-dt / tau)


def linear(a, b, v, map_min, map_max):
    return map_min + (map_max - map_min) * (v - a) / (b - a)


def coolant_derate(t_cool, normal_max, hot_max, critical, floor):
    if hot_max <= normal_max or critical <= hot_max:
        return 1.0, 0
    if t_cool <= normal_max:
        return 1.0, 0
    if t_cool <= hot_max:
        return linear(normal_max, hot_max, t_cool, 1, floor), 1
    if t_cool <= critical:
        return floor, 1
    return 0.0, 1


class TestRoadLoad(unittest.TestCase):
    def test_gravity_constant(self):
        # The kernel carries the standard gravity literal.
        self.assertAlmostEqual(
            _sqf_number(ROAD_SRC, r"_g\s*=\s*([0-9.]+)"), 9.80665, places=4
        )

    def test_rolling_term_is_crr_mass_g(self):
        g = _sqf_number(ROAD_SRC, r"_g\s*=\s*([0-9.]+)")
        mass, crr = 2361.0, 0.03
        self.assertAlmostEqual(
            road_load_force(mass, 0, 0, crr, 0, 0, 1.225, g), crr * mass * g, places=6
        )

    def test_grade_multiplier_about_three_and_a_half(self):
        # A 5 percent grade at a rolling coefficient of 0.02 lifts the load
        # about 3.5 times at low speed (the brief states about 3.4x).
        g = _sqf_number(ROAD_SRC, r"_g\s*=\s*([0-9.]+)")
        mass, crr, grade = 20000.0, 0.02, 0.05
        flat = road_load_force(mass, 1.0, 0, crr, 0, 0, 1.225, g)
        climb = road_load_force(mass, 1.0, 0, crr, grade, 0, 1.225, g)
        ratio = climb / flat
        self.assertGreater(ratio, 3.0)
        self.assertLess(ratio, 4.5)

    def test_drag_term_is_half_rho_cda_v_squared(self):
        g = _sqf_number(ROAD_SRC, r"_g\s*=\s*([0-9.]+)")
        mass, speed, cda, rho = 2000.0, 22.2, 0.7, 1.225
        force = road_load_force(mass, speed, 0, 0.0, 0, cda, rho, g)
        self.assertAlmostEqual(force, 0.5 * rho * cda * speed**2, places=6)

    def test_nonpositive_mass_refused(self):
        self.assertIn("if (_massKg <= 0) exitWith { [-1, -1] }", ROAD_SRC)


class TestFuelRate(unittest.TestCase):
    def test_formula_units(self):
        # BSFC * P / density: (g/kWh * kW) / (g/L) = L/h.
        self.assertAlmostEqual(
            fuel_rate_lph(7500, 8300, 206, 840), 206 * 15.8 / 840, places=6
        )

    def test_mass_rate_is_the_same_relation_as_the_flight_kernel(self):
        # fuel_burn_kg_s = sfc_kg_kwh * power_w / 3.6e6, expressed here as
        # L/h * density / 3.6e6.  Both give the same mass rate.
        rate_lph = fuel_rate_lph(0, 100000, 206, 840)
        kgs = fuel_mass_rate_kgs(rate_lph, 840)
        sfc_kg_kwh = 206 / 1000.0
        self.assertAlmostEqual(kgs, sfc_kg_kwh * 100000 / 3.6e6, places=9)

    def test_idle_only_rate(self):
        # The declared idle floor: 0.05 * 150 kW at the diesel scalar.
        idle = 0.05 * 150000
        self.assertAlmostEqual(
            fuel_rate_lph(idle, 0, 206, 840), 206 * 7.5 / 840, places=6
        )

    def test_nonpositive_density_refused(self):
        self.assertIn("if (_fuelDensityGL <= 0) exitWith { [-1, -1] }", FUEL_SRC)


class TestRange(unittest.TestCase):
    def test_hmmwv_vector(self):
        # 95 L tank, 20 L/100km highway -> 475 km.
        rate_lph = 20.0 * 20.0 / 100.0  # 20 L/100km at 20 km/h -> 4 L/h
        self.assertAlmostEqual(range_km(95, 1.0, rate_lph, 20.0), 475.0, places=3)

    def test_abrams_vector(self):
        # 1909 L tank, 4 L/km -> about 477 km (the brief's about 480 km).
        rate_lph = 4.0 * 40.0  # 4 L/km at 40 km/h -> 160 L/h
        self.assertAlmostEqual(range_km(1909, 1.0, rate_lph, 40.0), 477.25, places=2)


class TestCoolantDerate(unittest.TestCase):
    def test_normal_band_no_derate_no_fan(self):
        self.assertEqual(coolant_derate(90, 100, 115, 130, 0.5), (1.0, 0))

    def test_hot_band_fan_on_and_ramp(self):
        derate, fan = coolant_derate(107.5, 100, 115, 130, 0.5)
        self.assertEqual(fan, 1)
        self.assertAlmostEqual(derate, 0.75, places=6)

    def test_overheat_floor(self):
        self.assertEqual(coolant_derate(120, 100, 115, 130, 0.5), (0.5, 1))

    def test_critical_stops_the_engine(self):
        self.assertEqual(coolant_derate(135, 100, 115, 130, 0.5), (0.0, 1))

    def test_inverted_band_refused(self):
        self.assertEqual(coolant_derate(200, 100, 95, 130, 0.5), (1.0, 0))

    def test_kernel_uses_the_arguments_not_literals(self):
        # The bands arrive as arguments, so the kernel carries no band literal.
        self.assertIn('["_normalMaxC", 100, [0]]', DERATE_SRC)


class TestCoolantTemperature(unittest.TestCase):
    def test_equilibrium(self):
        # A long interval relaxes to T_amb + Q / UA.
        self.assertAlmostEqual(
            coolant_new(15, 40000, 800, 90, 90, 100000), 15 + 40000 / 800, places=4
        )

    def test_exact_exponential_step(self):
        t0, t_inf, tau, dt = 20.0, 100.0, 90.0, 30.0
        self.assertAlmostEqual(
            coolant_new(0, t_inf, 1.0, tau, t0, dt),
            t_inf + (t0 - t_inf) * math.exp(-dt / tau),
            places=9,
        )

    def test_guards_return_the_current_temperature(self):
        self.assertIn("if (_uaW <= 0) exitWith { _tCoolantC }", COOLTEMP_SRC)
        self.assertIn("if (_tauS <= 0) exitWith { _tCoolantC }", COOLTEMP_SRC)
        self.assertIn("if (_deltaTimeS < 0) exitWith { _tCoolantC }", COOLTEMP_SRC)


class TestCorpus(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(DATA.read_text(encoding="utf-8"))

    def test_corpus_validates(self):
        self.assertEqual(validator.validate(self.data), [])

    def test_diesel_is_the_sweet_spot(self):
        diesel = next(c for c in self.data["engine_classes"] if c["id"] == "diesel")
        self.assertAlmostEqual(diesel["bsfc_g_kwh"], 206.0)

    def test_mud_multiplier(self):
        mud = next(t for t in self.data["terrain_multipliers"] if t["id"] == "Mud")
        self.assertAlmostEqual(mud["multiplier"], 2.5)

    def test_heat_reject_fraction_is_one_third(self):
        frac = next(
            t for t in self.data["thermal"] if t["id"] == "heat_reject_fraction"
        )
        self.assertAlmostEqual(frac["value"], 1 / 3, places=5)

    def test_generator_is_fresh(self):
        result = subprocess.run(
            [sys.executable, str(REPO / "tools/gen_fuel_data.py"), "--check"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class TestReuse(unittest.TestCase):
    def test_coolant_kernel_reuses_the_existing_convection_correlation(self):
        header = COOLANT_TEMP.read_text(encoding="utf-8")
        self.assertIn("fnc_calculateVehicleHeat", header)
        self.assertIn("5.6 + 3.9", header)

    def test_fuel_kernel_names_the_flight_sibling(self):
        header = FUEL_RATE.read_text(encoding="utf-8")
        self.assertIn("fnc_calculateFuelBurn", header)

    def test_driver_does_not_burn_the_engine_tank(self):
        # The engine owns the tank; a second burn would double-count.
        self.assertNotIn("setFuel", DRIVER_SRC)

    def test_driver_reuses_the_shared_nearby_vehicle_list(self):
        self.assertIn("getNearbyVehicles", DRIVER_SRC)


if __name__ == "__main__":
    unittest.main()
