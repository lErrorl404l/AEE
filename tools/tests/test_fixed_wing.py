#!/usr/bin/env python3
"""Fixed-wing aircraft performance kernels (issue #22).

Density altitude, ground effect and landing performance, grounded in the ISA
standard atmosphere, the SAE J1349 piston density correction and the FAA
empirical ground-effect curve.

  fnc_calculateDensityAltitude        - DA from pressure altitude and OAT
  fnc_calculatePowerRatio             - engine power/thrust ratio from sigma
  fnc_calculateGroundEffect           - induced-drag reduction from h/b
  fnc_calculateFixedWingPerformance   - the derived performance row
  fnc_updateFixedWingPerformance      - the driver (source contract only)
  fnc_logFixedWingState               - the debug consumer (source contract)

The pure kernels run from their real SQF through tools/tests/sqf_lite.py, so a
failure is a source failure and not a mirror drift.

Run: python3 -m unittest tools.tests.test_fixed_wing -v
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FLIGHT = ROOT / "addons" / "flight"
FUNCS = FLIGHT / "functions"
PREP = FLIGHT / "XEH_PREP.hpp"
POST_INIT = FLIGHT / "XEH_postInit.sqf"
SETTINGS = FLIGHT / "initSettings.inc.sqf"
STRINGTABLE = FLIGHT / "stringtable.xml"

DA = FUNCS / "fnc_calculateDensityAltitude.sqf"
POWER = FUNCS / "fnc_calculatePowerRatio.sqf"
GE = FUNCS / "fnc_calculateGroundEffect.sqf"
PERF = FUNCS / "fnc_calculateFixedWingPerformance.sqf"
DRIVER = FUNCS / "fnc_updateFixedWingPerformance.sqf"
LOG = FUNCS / "fnc_logFixedWingState.sqf"


def _code_only(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    out = []
    for line in text.split("\n"):
        cut = line.find("//")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


def _da(pa_m, oat_c):
    return float(run_sqf(DA, [pa_m, oat_c], {}))


def _power(sigma, propulsion):
    return float(run_sqf(POWER, [sigma, propulsion], {}))


def _ge(height_m, wingspan_m):
    return float(run_sqf(GE, [height_m, wingspan_m], {}))


def _perf(sigma, ias, stall, propulsion, height_m, wingspan_m, headwind):
    return run_sqf(
        PERF,
        [sigma, ias, stall, propulsion, height_m, wingspan_m, headwind],
        {
            "__FUNC__calculatePowerRatio": _power,
            "__FUNC__calculateGroundEffect": _ge,
        },
    )


class TestDensityAltitude(unittest.TestCase):
    """fnc_calculateDensityAltitude is the FAA density-altitude correction."""

    def test_standard_day_at_sea_level_is_zero(self):
        self.assertAlmostEqual(_da(0, 15), 0.0, places=6)

    def test_hot_day_adds_density_altitude(self):
        # 30 C at sea level: 15 C above ISA, 36.576 m per degree.
        self.assertAlmostEqual(_da(0, 30), 36.576 * 15, places=6)

    def test_cold_day_subtracts(self):
        self.assertAlmostEqual(_da(0, 0), 36.576 * -15, places=6)

    def test_pressure_altitude_correction(self):
        # 2400 m PA, 30 C.  ISA temp = 15 - 0.0065*2400 = -0.6 C.
        expected = 2400 + 36.576 * (30 - (15 - 0.0065 * 2400))
        self.assertAlmostEqual(_da(2400, 30), expected, places=4)

    def test_monotonic_in_temperature(self):
        self.assertLess(_da(1000, 0), _da(1000, 20))
        self.assertLess(_da(1000, 20), _da(1000, 40))


class TestPowerRatio(unittest.TestCase):
    """fnc_calculatePowerRatio is the engine power/thrust lapse."""

    def test_sea_level_standard_day_is_one(self):
        for propulsion in ("piston_prop", "turbojet", "turbofan", "turboprop"):
            with self.subTest(propulsion=propulsion):
                self.assertAlmostEqual(_power(1.0, propulsion), 1.0, places=6)

    def test_piston_reproduces_the_issue_vector(self):
        # SAE J1349: sigma^1.2.  At 8000 ft sigma = 0.789, P/P0 = 0.752.
        self.assertAlmostEqual(_power(0.789, "piston_prop"), 0.789**1.2, places=6)
        self.assertAlmostEqual(_power(0.789, "piston_prop"), 0.752, places=3)

    def test_turbojet_is_linear_in_sigma(self):
        self.assertAlmostEqual(_power(0.789, "turbojet"), 0.789, places=6)

    def test_turbofan_uses_the_0_7_exponent(self):
        self.assertAlmostEqual(_power(0.789, "turbofan"), 0.789**0.7, places=6)

    def test_turboprop_is_taken_as_gas_turbine_like(self):
        self.assertAlmostEqual(_power(0.789, "turboprop"), 0.789, places=6)

    def test_unknown_propulsion_lapses_as_sigma(self):
        self.assertAlmostEqual(_power(0.789, ""), 0.789, places=6)

    def test_monotonic_in_sigma(self):
        for propulsion in ("piston_prop", "turbofan"):
            with self.subTest(propulsion=propulsion):
                self.assertLess(_power(0.5, propulsion), _power(0.9, propulsion))


class TestGroundEffect(unittest.TestCase):
    """fnc_calculateGroundEffect is the FAA empirical induced-drag curve."""

    def test_the_faa_table_points(self):
        cases = [
            (1.0, 10.0, 0.50),  # h/b = 0.1
            (2.5, 10.0, 0.40),  # h/b = 0.25
            (5.0, 10.0, 0.25),  # h/b = 0.5
            (10.0, 10.0, 0.10),  # h/b = 1.0
        ]
        for height, span, expected in cases:
            with self.subTest(hb=height / span):
                self.assertAlmostEqual(_ge(height, span), expected, places=6)

    def test_free_air_above_one_wingspan(self):
        self.assertEqual(_ge(11.0, 10.0), 0.0)
        self.assertEqual(_ge(100.0, 10.0), 0.0)

    def test_on_the_ground_is_clamped_to_fifty_percent(self):
        self.assertAlmostEqual(_ge(0.0, 10.0), 0.50, places=6)

    def test_zero_wingspan_is_no_effect(self):
        self.assertEqual(_ge(5.0, 0.0), 0.0)

    def test_bounded_and_monotonic_decreasing(self):
        prev = 1.0
        for height in (0.5, 1.0, 2.5, 5.0, 9.9):
            value = _ge(height, 10.0)
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 0.5)
            self.assertLessEqual(value, prev)
            prev = value


class TestFixedWingPerformance(unittest.TestCase):
    """fnc_calculateFixedWingPerformance is the derived performance row."""

    def _row(self, **kw):
        base = dict(
            sigma=0.789,
            ias=100.0,
            stall=100.0,
            propulsion="piston_prop",
            height=10.0,
            span=10.0,
            headwind=0.0,
        )
        base.update(kw)
        return _perf(
            base["sigma"],
            base["ias"],
            base["stall"],
            base["propulsion"],
            base["height"],
            base["span"],
            base["headwind"],
        )

    def test_tas_scales_as_one_over_sqrt_sigma(self):
        row = self._row()
        self.assertAlmostEqual(row[0], 100.0 / (0.789**0.5), places=4)
        self.assertAlmostEqual(row[0], 112.6, places=1)

    def test_stall_speed_scales_as_one_over_sqrt_sigma(self):
        # The issue vector: 112.6 kt from a 100 kt base at 8000 ft.
        row = self._row()
        self.assertAlmostEqual(row[1], 112.6, places=1)

    def test_power_ratio_is_carried_through(self):
        row = self._row()
        self.assertAlmostEqual(row[2], _power(0.789, "piston_prop"), places=6)

    def test_ground_effect_is_carried_through(self):
        row = self._row(height=10.0, span=10.0)
        self.assertAlmostEqual(row[3], 0.10, places=6)

    def test_landing_multiplier_is_one_over_sigma(self):
        # The issue vector: 1.27x at 8000 ft.
        row = self._row()
        self.assertAlmostEqual(row[5], 1.0 / 0.789, places=6)
        self.assertAlmostEqual(row[5], 1.27, places=2)

    def test_piston_takeoff_anchor(self):
        # 1/(sigma * power) = 1/sigma^2.2 = 1.68 at 8000 ft (issue 1.6-1.7).
        row = self._row()
        expected = 1.0 / (0.789 * (0.789**1.2))
        self.assertAlmostEqual(row[4], expected, places=6)
        self.assertAlmostEqual(row[4], 1.68, places=1)

    def test_jet_takeoff_anchor(self):
        # A turbojet gives 1/sigma^2 = 1.61 at 8000 ft (issue vector).
        row = self._row(propulsion="turbojet")
        self.assertAlmostEqual(row[4], 1.0 / (0.789**2), places=6)
        self.assertAlmostEqual(row[4], 1.61, places=2)

    def test_headwind_shortens_the_roll(self):
        still = self._row(headwind=0.0)
        head = self._row(headwind=10.0)
        self.assertAlmostEqual(head[4], still[4] * 0.9, places=6)
        self.assertAlmostEqual(head[5], still[5] * 0.9, places=6)

    def test_tailwind_lengthens_the_roll_more_steeply(self):
        still = self._row(headwind=0.0)
        tail = self._row(headwind=-10.0)
        self.assertAlmostEqual(tail[4], still[4] * 1.5, places=6)
        self.assertAlmostEqual(tail[5], still[5] * 1.5, places=6)

    def test_sea_level_standard_day_is_unity(self):
        row = _perf(1.0, 100.0, 100.0, "turbojet", 100.0, 10.0, 0.0)
        self.assertAlmostEqual(row[0], 100.0, places=6)
        self.assertAlmostEqual(row[4], 1.0, places=6)
        self.assertAlmostEqual(row[5], 1.0, places=6)

    def test_sigma_floor_keeps_the_row_finite(self):
        row = _perf(0.0, 100.0, 100.0, "piston_prop", 10.0, 10.0, 0.0)
        for value in row:
            self.assertTrue(value == value)  # not NaN
            self.assertLess(abs(value), 1.0e6)


class TestDriverContract(unittest.TestCase):
    """The driver reads the core state and publishes the ambient row."""

    def setUp(self):
        self.src = _code_only(DRIVER.read_text(encoding="utf-8"))

    def test_reads_the_environment_state(self):
        self.assertIn("EGVAR(core,referenceAltitude)", self.src)
        self.assertIn("EGVAR(core,currentTemperature)", self.src)
        self.assertIn("EGVAR(core,currentAirDensity)", self.src)

    def test_uses_the_density_altitude_kernel(self):
        self.assertIn("FUNC(calculateDensityAltitude)", self.src)

    def test_density_ratio_is_the_isa_ratio(self):
        self.assertIn("AERO_ISA_SEA_LEVEL_DENSITY", self.src)

    def test_publishes_the_ambient_row(self):
        self.assertIn("QGVAR(currentDensityAltitude)", self.src)
        self.assertIn("QGVAR(currentDensityRatio)", self.src)


class TestStateConsumer(unittest.TestCase):
    """The published ambient row has a reader on the trace gate."""

    def setUp(self):
        self.consumer = _code_only(LOG.read_text(encoding="utf-8"))
        self.post = _code_only(POST_INIT.read_text(encoding="utf-8"))

    def test_reads_every_published_value(self):
        self.assertIn("QGVAR(currentDensityAltitude)", self.consumer)
        self.assertIn("QGVAR(currentDensityRatio)", self.consumer)

    def test_the_consumer_is_gated_on_the_trace_switch(self):
        self.assertIn("if (!AEE_TRACE_ON) exitWith", self.consumer)

    def test_post_init_runs_the_driver_and_the_state_line(self):
        self.assertIn("FUNC(updateFixedWingPerformance)", self.post)
        self.assertIn("FUNC(logFixedWingState)", self.post)
        self.assertIn("GVAR(fixedWingPerformance)", self.post)


class TestWiring(unittest.TestCase):
    """The kernels are PREP'd, gated and documented."""

    def test_all_kernels_are_prepped(self):
        prep = PREP.read_text(encoding="utf-8")
        for name in (
            "calculateDensityAltitude",
            "calculatePowerRatio",
            "calculateGroundEffect",
            "calculateFixedWingPerformance",
            "updateFixedWingPerformance",
            "logFixedWingState",
        ):
            with self.subTest(name=name):
                self.assertIn(f"PREP({name})", prep)

    def test_setting_is_registered(self):
        settings = SETTINGS.read_text(encoding="utf-8")
        self.assertIn("fixedWingPerformance", settings)

    def test_stringtable_holds_the_setting(self):
        stringtable = STRINGTABLE.read_text(encoding="utf-8")
        self.assertIn("STR_AEE_Flight_fixedWingPerformance_Name", stringtable)
        self.assertIn("STR_AEE_Flight_fixedWingPerformance_Description", stringtable)


if __name__ == "__main__":
    unittest.main()
