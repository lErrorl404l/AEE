#!/usr/bin/env python3
"""Flight-physics kernels, the advanced-model gate and the runtime force wiring.

The flight layer fixes the dead advanced-flight-model gate and gives the AEE
atmosphere a flight consumer:

  fnc_resolveFlightModel        — the AFM/rotor-lib gate truth table
  fnc_calculateTurbulenceForce  — the gust force magnitude
  fnc_calculateAeroPenalty      — the density/icing lift-loss and drag-rise
  fnc_applyAirframeLoad         — the density/icing consumer
  fnc_applyFlightTurbulence     — the physical turbulence layer

The pure kernels run from their real SQF through tools/tests/sqf_lite.py, so a
failure is a source failure and not a mirror drift.  The source contracts read
the engine wiring the harness cannot execute.

The gate contract is the reason this suite exists.  The old code tested
isClass (configOf _veh >> "AdvancedFlightModel"); that class does not exist in
vanilla, so the addForce branch never ran and every aircraft took the simple
velocity path.  The correct gate is difficultyEnabledRTD, plus the
RotorLibHelicopterProperties class for a rotary airframe.

Run: python3 -m unittest tools.tests.test_flight_physics -v
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MOBILITY = ROOT / "addons" / "mobility"
FUNCS = MOBILITY / "functions"
HEADER = MOBILITY / "script_component.hpp"
POST_INIT = MOBILITY / "XEH_postInit.sqf"
PREP = MOBILITY / "XEH_PREP.hpp"
SETTINGS = MOBILITY / "initSettings.inc.sqf"
STRINGTABLE = MOBILITY / "stringtable.xml"
RUNNER = ROOT / "tools" / "run_tests.py"

RESOLVE = FUNCS / "fnc_resolveFlightModel.sqf"
TURB_FORCE = FUNCS / "fnc_calculateTurbulenceForce.sqf"
TURB_AREA = FUNCS / "fnc_resolveTurbulenceArea.sqf"
AERO_PENALTY = FUNCS / "fnc_calculateAeroPenalty.sqf"
APPLY_AIR = FUNCS / "fnc_applyAirframeLoad.sqf"
APPLY_TURB = FUNCS / "fnc_applyFlightTurbulence.sqf"
LOG_AIRFRAME = FUNCS / "fnc_logAirframeState.sqf"

G = 9.80665


def _define(name):
    """The numeric value of a #define in the mobility component header."""
    text = HEADER.read_text(encoding="utf-8")
    match = re.search(rf"^#define\s+{name}\s+([0-9]+(?:\.[0-9]+)?)", text, re.M)
    assert match, f"{name} is not defined in {HEADER.name}"
    return float(match.group(1))


def _defines():
    return {
        "TURBULENCE_FORCE_CAP_FRACTION": _define("TURBULENCE_FORCE_CAP_FRACTION"),
        "TURBULENCE_DENSITY_RATIO_MAX": _define("TURBULENCE_DENSITY_RATIO_MAX"),
        "TURBULENCE_TORQUE_FRACTION": _define("TURBULENCE_TORQUE_FRACTION"),
        "AERO_ISA_SEA_LEVEL_DENSITY": _define("AERO_ISA_SEA_LEVEL_DENSITY"),
        "AERO_DENSITY_LIFT_LOSS_MAX": _define("AERO_DENSITY_LIFT_LOSS_MAX"),
        "AERO_ICE_LIFT_LOSS_MAX": _define("AERO_ICE_LIFT_LOSS_MAX"),
        "AERO_ICE_DRAG_RISE_MAX": _define("AERO_ICE_DRAG_RISE_MAX"),
        "AERO_LIFT_LOSS_CAP": _define("AERO_LIFT_LOSS_CAP"),
        "AERO_DRAG_AREA_M2": _define("AERO_DRAG_AREA_M2"),
        "AERO_DEFAULT_AIRCRAFT_MASS_KG": _define("AERO_DEFAULT_AIRCRAFT_MASS_KG"),
    }


def _code_only(text):
    """Strip block and line comments so a search sees code, not prose."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    out = []
    for line in text.split("\n"):
        cut = line.find("//")
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


class TestConstants(unittest.TestCase):
    """The bounds are pinned, so a drift is caught here."""

    def test_bounds_are_the_published_values(self):
        d = _defines()
        self.assertEqual(d["TURBULENCE_FORCE_CAP_FRACTION"], 0.25)
        self.assertEqual(d["AERO_ISA_SEA_LEVEL_DENSITY"], 1.225)
        self.assertEqual(d["AERO_ICE_LIFT_LOSS_MAX"], 0.35)
        self.assertEqual(d["AERO_ICE_DRAG_RISE_MAX"], 0.5)
        self.assertEqual(d["AERO_LIFT_LOSS_CAP"], 0.45)
        self.assertEqual(d["AERO_DRAG_AREA_M2"], 0.7)

    def test_lift_loss_cap_leaves_headroom(self):
        # The scripted layer must stay a perturbation, never a full stall.
        self.assertLess(_define("AERO_LIFT_LOSS_CAP"), 0.5)


class TestFlightModelGate(unittest.TestCase):
    """fnc_resolveFlightModel is the executable AFM/rotor-lib truth table."""

    CASES = [
        (False, False, 0.0),
        (True, False, 1.0),
        (False, True, 1.0),
        (True, True, 1.0),
    ]

    def test_truth_table(self):
        for rtd, rotor, expected in self.CASES:
            with self.subTest(rtd=rtd, rotor=rotor):
                got = run_sqf(RESOLVE, [rtd, rotor], _defines())
                # An SQF boolean is a number in the harness (true -> 1).
                self.assertEqual(float(got), expected)

    def test_rotor_lib_alone_selects_the_physical_path(self):
        # The scenario flag may be off while a rotor-lib airframe still
        # integrates forces; the property class must be enough on its own.
        self.assertEqual(float(run_sqf(RESOLVE, [False, True], _defines())), 1.0)


class TestTurbulenceForce(unittest.TestCase):
    """fnc_calculateTurbulenceForce is the aerodynamic gust force.

    The force is the dynamic pressure times the airframe's effective drag
    area, F = 0.5 rho v^2 (Cd S).  It carries no mass, so the acceleration it
    realises is F / mass.  The old kernel multiplied by the mass, so the
    acceleration was the same for a 752 kg Littlebird and a 22 tonne Chinook.
    """

    def _force(self, gust, density=1.225, area=0.7, mass=1000.0):
        return float(run_sqf(TURB_FORCE, [gust, density, area, mass], _defines()))

    def test_zero_gust_is_no_force(self):
        self.assertEqual(self._force(0.0), 0.0)

    def test_negative_gust_is_no_force(self):
        self.assertEqual(self._force(-3.0), 0.0)

    def test_zero_mass_is_no_force(self):
        self.assertEqual(self._force(4.0, mass=0.0), 0.0)

    def test_zero_drag_area_is_no_force(self):
        self.assertEqual(self._force(4.0, area=0.0), 0.0)

    def test_known_magnitude(self):
        # 0.5 * 1.225 * 4^2 * 0.7 = 6.86 N.
        self.assertAlmostEqual(self._force(4.0), 6.86, places=6)

    def test_density_scales_the_force(self):
        full = self._force(4.0, density=1.225)
        half = self._force(4.0, density=0.6125)
        self.assertAlmostEqual(half, full / 2.0, places=6)

    def test_drag_area_scales_the_force(self):
        base = self._force(4.0, area=0.7)
        double = self._force(4.0, area=1.4)
        self.assertAlmostEqual(double, base * 2.0, places=6)

    def test_density_is_capped(self):
        at_cap = self._force(
            4.0, density=1.225 * _define("TURBULENCE_DENSITY_RATIO_MAX")
        )
        beyond = self._force(4.0, density=99.0)
        self.assertAlmostEqual(beyond, at_cap, places=6)

    def test_force_is_quadratic_in_gust(self):
        # A drag force goes with the square of the gust speed.
        self.assertAlmostEqual(self._force(4.0), self._force(2.0) * 4.0, places=6)

    def test_force_is_independent_of_mass(self):
        # The fix: the aerodynamic force carries no mass, so a heavy airframe
        # does not get a proportionally larger force (the old flat
        # acceleration).  Below the cap the force is identical.
        light = self._force(4.0, area=50.9, mass=752.0)
        heavy = self._force(4.0, area=50.9, mass=22680.0)
        self.assertAlmostEqual(light, heavy, places=6)

    def test_extreme_gust_is_bounded_to_a_fraction_of_weight(self):
        cap = 1000.0 * G * _define("TURBULENCE_FORCE_CAP_FRACTION")
        self.assertAlmostEqual(self._force(1.0e6), cap, places=3)

    def test_monotonic_in_gust(self):
        self.assertLess(self._force(2.0), self._force(4.0))
        self.assertLess(self._force(4.0), self._force(8.0))


class TestGustWeightResponse(unittest.TestCase):
    """A heavy airframe resists a gust and a light one is nudged.

    The operator report: the wind blew the light Littlebird around like a
    heavy airframe.  The old kernel returned a mass-proportional force, so the
    acceleration F / mass was flat across airframes.  This proves the
    acceleration now falls with the mass.
    """

    LIGHT = 782.0  # MD 530F / AH-9 Pawnee operating weight, kg
    HEAVY = 9185.0  # UH-60 / UH-80 Ghost Hawk operating weight, kg
    DISC = 55.154115  # MD 530F rotor disc area, m^2 (the operator's airframe)

    def _accel(self, mass, area, gust=5.0):
        force = float(run_sqf(TURB_FORCE, [gust, 1.225, area, mass], _defines()))
        return force / mass

    def test_light_airframe_accelerates_more_than_heavy(self):
        self.assertGreater(
            self._accel(self.LIGHT, self.DISC),
            self._accel(self.HEAVY, self.DISC),
        )

    def test_acceleration_scales_as_one_over_mass(self):
        # Same drag area, so the force is equal and the acceleration is 1/mass.
        a_light = self._accel(self.LIGHT, self.DISC)
        a_heavy = self._accel(self.HEAVY, self.DISC)
        self.assertAlmostEqual(a_light / a_heavy, self.HEAVY / self.LIGHT, places=6)


class TestResolveTurbulenceArea(unittest.TestCase):
    """fnc_resolveTurbulenceArea reads the drag area from the corpus row.

    The row order is the generated value row: [operating_weight_kg,
    rated_power_w, drag_area_m2, rotor_disc_area_m2].  A fixed-wing entry holds
    drag_area_m2 (Cd S); a rotary-wing entry holds rotor_disc_area_m2 (the
    disc).  No parallel data table is added.
    """

    def _area(self, row):
        return float(run_sqf(TURB_AREA, [row], _defines()))

    def test_fixed_wing_uses_the_drag_area(self):
        self.assertEqual(self._area([12701, 0, 0.7, 0]), 0.7)

    def test_rotary_wing_uses_the_rotor_disc(self):
        # The operator's airframe: AH-9 Pawnee (md530f), disc 55.154115 m^2.
        self.assertAlmostEqual(
            self._area([782, 478000, 0, 55.154115]), 55.154115, places=6
        )

    def test_unknown_row_uses_the_kernel_default(self):
        self.assertEqual(self._area([]), _define("AERO_DRAG_AREA_M2"))

    def test_all_absent_uses_the_kernel_default(self):
        self.assertEqual(self._area([0, 0, 0, 0]), _define("AERO_DRAG_AREA_M2"))


class TestAeroPenalty(unittest.TestCase):
    """fnc_calculateAeroPenalty is the density/icing lift-loss and drag-rise."""

    def _penalty(self, ratio, ice):
        got = run_sqf(AERO_PENALTY, [ratio, ice], _defines())
        return float(got[0]), float(got[1])

    def test_sea_level_no_ice_is_no_penalty(self):
        self.assertEqual(self._penalty(1.0, 0.0), (0.0, 0.0))

    def test_thin_air_removes_lift(self):
        lift, drag = self._penalty(0.9, 0.0)
        self.assertAlmostEqual(lift, 0.1, places=6)
        self.assertEqual(drag, 0.0)

    def test_dense_air_is_not_credited(self):
        # The engine's own model gains from dense air; the scripted penalty
        # must not add lift.
        self.assertEqual(self._penalty(1.5, 0.0), (0.0, 0.0))

    def test_full_ice_gives_the_declared_loss_and_rise(self):
        lift, drag = self._penalty(1.0, 1.0)
        self.assertAlmostEqual(lift, _define("AERO_ICE_LIFT_LOSS_MAX"), places=6)
        self.assertAlmostEqual(drag, _define("AERO_ICE_DRAG_RISE_MAX"), places=6)

    def test_combined_lift_loss_is_capped(self):
        # Extreme thin air plus full ice would exceed the cap; the cap holds.
        lift, _ = self._penalty(0.0, 1.0)
        self.assertAlmostEqual(lift, _define("AERO_LIFT_LOSS_CAP"), places=6)

    def test_ice_severity_is_clamped(self):
        self.assertEqual(self._penalty(1.0, 5.0), self._penalty(1.0, 1.0))
        self.assertEqual(self._penalty(1.0, -2.0), self._penalty(1.0, 0.0))

    def test_monotonic_in_ice(self):
        self.assertLess(self._penalty(1.0, 0.2)[0], self._penalty(1.0, 0.7)[0])
        self.assertLess(self._penalty(1.0, 0.2)[1], self._penalty(1.0, 0.7)[1])

    def test_sweep_stays_bounded(self):
        # No input may produce a lift loss above the cap or a drag rise above
        # the declared maximum, so the layer cannot destabilise the airframe.
        for ratio in (-1.0, 0.0, 0.4, 0.9, 1.0, 1.5, 5.0):
            for ice in (-1.0, 0.0, 0.5, 1.0, 3.0):
                lift, drag = self._penalty(ratio, ice)
                self.assertGreaterEqual(lift, 0.0)
                self.assertLessEqual(lift, _define("AERO_LIFT_LOSS_CAP") + 1e-9)
                self.assertGreaterEqual(drag, 0.0)
                self.assertLessEqual(drag, _define("AERO_ICE_DRAG_RISE_MAX") + 1e-9)


class TestGateSourceContract(unittest.TestCase):
    """The caller reads the real engine gate, not the nonexistent class."""

    def setUp(self):
        self.src = _code_only(APPLY_TURB.read_text(encoding="utf-8"))

    def test_reads_the_difficulty_flag(self):
        self.assertIn("difficultyEnabledRTD", self.src)

    def test_reads_the_rotor_lib_property(self):
        # The exact config read, on the vehicle's own config.
        self.assertIn('configOf _veh >> "RotorLibHelicopterProperties"', self.src)

    def test_does_not_test_the_nonexistent_class(self):
        self.assertNotIn('"AdvancedFlightModel"', self.src)
        self.assertNotIn("AdvancedFlightModel", self.src)

    def test_uses_the_gate_kernel(self):
        self.assertIn("FUNC(resolveFlightModel)", self.src)

    def test_reads_the_corpus_drag_area(self):
        # The drag area comes from the aircraft record, not a parallel table.
        self.assertIn("FUNC(getAircraftData)", self.src)
        self.assertIn("FUNC(resolveTurbulenceArea)", self.src)

    def test_no_unsourced_force_divisor(self):
        self.assertNotIn("TURBULENCE_FORCE_DIVISOR", self.src)

    def test_simple_path_carries_the_mass(self):
        # The simple model cannot integrate a force, so it applies the same
        # acceleration as a velocity delta: force / mass over the real clock
        # delta, never the per-frame diag_deltaTime.
        self.assertIn("EGVAR(core,simTime)", self.src)
        self.assertIn("(_forceN / _mass) * _dt", self.src)
        self.assertNotIn("diag_deltaTime", self.src)

    def test_physical_path_applies_force_and_torque(self):
        self.assertIn("addForce", self.src)
        self.assertIn("addTorque", self.src)

    def test_simple_path_is_gated_and_not_sole(self):
        # setVelocity must still exist as the simple-model path, but only in
        # the else branch of the physical test.
        self.assertIn("_veh setVelocity", self.src)
        self.assertIn("} else {", self.src)
        # local ownership is what makes every application MP-safe.
        self.assertIn("(local _x) &&", self.src)


class TestApplyAirframeLoadContract(unittest.TestCase):
    """The density/icing consumer reads the AEE state and is bounded."""

    def setUp(self):
        self.src = _code_only(APPLY_AIR.read_text(encoding="utf-8"))

    def test_reads_the_lift_ratio_and_density(self):
        self.assertIn("currentLiftRatio", self.src)
        self.assertIn("currentAirDensity", self.src)

    def test_reads_the_icing_state(self):
        self.assertIn("airframeIcing", self.src)
        self.assertIn("iceAccretion_kg", self.src)

    def test_local_gate_is_the_mp_safety(self):
        self.assertIn("if (!local _vehicle) exitWith", self.src)

    def test_applies_forces_and_ice_mass(self):
        self.assertIn("addForce", self.src)
        self.assertIn("setMass", self.src)

    def test_uses_the_bounded_kernel_for_the_penalty(self):
        self.assertIn("FUNC(calculateAeroPenalty)", self.src)
        self.assertIn("_penalty select 0", self.src)
        self.assertIn("_penalty select 1", self.src)

    def test_air_only_and_parachute_excluded(self):
        self.assertIn('isKindOf "Air"', self.src)
        self.assertIn('isKindOf "ParachuteBase"', self.src)

    def test_drag_uses_the_declared_area(self):
        self.assertIn("AERO_DRAG_AREA_M2", self.src)


class TestAirframeStateConsumer(unittest.TestCase):
    """The applied penalties have a real consumer on the mobility debug gate.

    fnc_applyAirframeLoad publishes airLiftLoss, airDragRise, airIceMassKg and
    airLiftRatioApplied.  Before this consumer nothing read them.  Removing the
    state line fails these tests and makes validate_cba_settings.py report the
    four names as orphan writes again.
    """

    def setUp(self):
        self.consumer = _code_only(LOG_AIRFRAME.read_text(encoding="utf-8"))
        self.post = _code_only(POST_INIT.read_text(encoding="utf-8"))

    def test_reads_every_published_penalty(self):
        for name in (
            "airLiftLoss",
            "airDragRise",
            "airIceMassKg",
            "airLiftRatioApplied",
        ):
            with self.subTest(name=name):
                self.assertIn(f"QGVAR({name})", self.consumer)

    def test_the_consumer_is_gated_on_the_trace_switch(self):
        self.assertIn("if (!AEE_TRACE_ON) exitWith", self.consumer)
        self.assertIn("airframe state | applied", self.consumer)

    def test_post_init_runs_the_state_line_at_one_hertz(self):
        self.assertIn("FUNC(logAirframeState)", self.post)
        self.assertIn("}, 1.0] call CBA_fnc_addPerFrameHandler", self.post)

    def test_prep_registers_the_consumer(self):
        prep = PREP.read_text(encoding="utf-8")
        self.assertIn("PREP(logAirframeState)", prep)


class TestWiring(unittest.TestCase):
    """The functions, settings, strings and loop are all wired."""

    def test_prep_entries(self):
        prep = PREP.read_text(encoding="utf-8")
        for name in (
            "PREP(applyFlightTurbulence)",
            "PREP(applyAirframeLoad)",
            "PREP(resolveFlightModel)",
            "PREP(calculateTurbulenceForce)",
            "PREP(calculateAeroPenalty)",
        ):
            self.assertIn(name, prep)

    def test_post_init_registers_the_airframe_loop(self):
        post = _code_only(POST_INIT.read_text(encoding="utf-8"))
        self.assertIn("GVAR(flightAeroPenalty)", post)
        self.assertIn("FUNC(applyAirframeLoad)", post)
        self.assertIn("airframeRadius", post)
        # The radius belongs in the refresh, not the per-frame body.
        refresh = post.index("if ((time - GVAR(airframeRefresh)) > 1) then")
        select = post.index("GVAR(airframeVehicles) = vehicles select")
        body = post.index("} forEach GVAR(airframeVehicles)")
        self.assertLess(refresh, select)
        self.assertLess(select, body)
        self.assertIn("distance _ref", post[select:body])
        open_at = post.rindex("{", 0, body)
        self.assertNotIn("distance", post[open_at : body + 1])

    def test_settings_registered(self):
        settings = SETTINGS.read_text(encoding="utf-8")
        self.assertIn("AEE_SETTING_CHECKBOX(flightAeroPenalty", settings)
        self.assertIn("AEE_SETTING_SLIDER(airframeRadius", settings)

    def test_stringtable_keys(self):
        st = STRINGTABLE.read_text(encoding="utf-8")
        for key in (
            "STR_AEE_Mobility_flightAeroPenalty_Name",
            "STR_AEE_Mobility_flightAeroPenalty_Description",
            "STR_AEE_Mobility_airframeRadius_Name",
            "STR_AEE_Mobility_airframeRadius_Description",
        ):
            self.assertEqual(st.count(f'ID="{key}"'), 1, key)

    def test_runner_registers_the_suites(self):
        runner = RUNNER.read_text(encoding="utf-8")
        self.assertIn("tools/tests/test_flight_physics.py", runner)
        self.assertIn("tools/tests/test_mobility_pfh.py", runner)


if __name__ == "__main__":
    unittest.main()
