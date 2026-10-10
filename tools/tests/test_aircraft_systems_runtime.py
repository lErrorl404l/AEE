#!/usr/bin/env python3
"""Runtime aircraft fuel kernel tests (aircraft systems, tasks 16 and 17).

The aircraft fuel layer burns a sourced rate on the owning machine and moves
the centre of gravity as the fuel leaves. Two files carry it:

  fnc_calculateFuelBurn   - the pure arithmetic over scalars
  fnc_updateFuelSystem    - the kernel that reads the systems row and writes

Both run from their real SQF through tools/tests/sqf_lite.py, so a failure is
a source failure and not a mirror drift. The pure kernel runs directly. The
kernel runs against a stub aircraft, a stub systems row and recorded engine
commands, so the test asserts the exact setFuel value and the centre-of-gravity
delta the kernel writes.

The sentinels below name no real aircraft and are never written to the corpus.

Run: python3 -m unittest tools.tests.test_aircraft_systems_runtime -v
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools" / "tests"))

from sqf_lite import run_sqf  # noqa: E402

FUNCS = REPO / "addons" / "flight" / "functions"
BURN = FUNCS / "fnc_calculateFuelBurn.sqf"
KERNEL = FUNCS / "fnc_updateFuelSystem.sqf"
PREP_PATH = REPO / "addons" / "flight" / "XEH_PREP.hpp"

BURN_SRC = BURN.read_text(encoding="utf-8")
KERNEL_SRC = KERNEL.read_text(encoding="utf-8")
PREP_SRC = PREP_PATH.read_text(encoding="utf-8")

# Sentinel fuel state. Distinct values so a swapped input is provable.
FULL_CAPACITY_L = 600.0
DENSITY_KG_L = 0.8
FULL_MASS_KG = FULL_CAPACITY_L * DENSITY_KG_L  # 480 kg
SOURCED_RATE = 0.1  # kg/s
CG_ARM_M = 2.5
DELTA_S = 10.0

# The systems row carries the numeric fields first. The kernel reads the fuel
# block: capacity, rate, density, sfc, cg arm.
SYSTEMS = [FULL_CAPACITY_L, SOURCED_RATE, DENSITY_KG_L, 0.0, CG_ARM_M]
# The flight-model row carries [operating_weight_kg, rated_power_w, ...].
DATA = [1100.0, 134000.0, 0.688, 0.0]

# Sentinel engine state. Distinct values so a swapped input is provable.
DESIGN_RPM = 2700.0
IDLE_NG = 0.4
MAX_NG = 1.0
MAX_TGT_C = 900.0
OIL_MIN_KPA = 200.0
OIL_MAX_KPA = 800.0
SPOOL_TAU_S = 4.0

NG = FUNCS / "fnc_calculateEngineNg.sqf"
TGT_OIL = FUNCS / "fnc_calculateScriptedTgtOil.sqf"
ENGINE_KERNEL = FUNCS / "fnc_updateEngineSystem.sqf"
NG_SRC = NG.read_text(encoding="utf-8")
TGT_OIL_SRC = TGT_OIL.read_text(encoding="utf-8")
ENGINE_KERNEL_SRC = ENGINE_KERNEL.read_text(encoding="utf-8")

# Sentinel damage state. Distinct values so a swapped input is provable.
DAMAGE_KERNEL = FUNCS / "fnc_updateDamageSystem.sqf"
DAMAGE_KERNEL_SRC = DAMAGE_KERNEL.read_text(encoding="utf-8")
DAMAGE_THRESHOLD = 0.1
ENGINE_HIT_DAMAGE = 0.5
FUEL_HIT_DAMAGE = 0.5
ROTOR_HIT_DAMAGE = 0.5

# The status kernel. It publishes the sourced nameplate state per system and
# never touches a force, a mass or a velocity.
STATUS_KERNEL = FUNCS / "fnc_updateStatusSystems.sqf"
STATUS_KERNEL_SRC = STATUS_KERNEL.read_text(encoding="utf-8")
STATUS_THRESHOLD = 22

# Sentinel status state. Distinct values so a swapped index is provable.
HYDRAULIC_KPA = 20684.3
GENERATOR_KW = 22.5
BUS_V = 28.0
BATTERY_AH = 12.75
CABIN_KPA = 75.0
OXYGEN = "onboard"

# The systems row carries the status fields at fixed indices: 14 hydraulic
# pressure, 15 generator power, 16 bus voltage, 17 battery charge, 18 cabin
# pressure and 21 the oxygen token.
STATUS_SYSTEMS: list[object] = [0] * 22
STATUS_SYSTEMS[14] = HYDRAULIC_KPA
STATUS_SYSTEMS[15] = GENERATOR_KW
STATUS_SYSTEMS[16] = BUS_V
STATUS_SYSTEMS[17] = BATTERY_AH
STATUS_SYSTEMS[18] = CABIN_KPA
STATUS_SYSTEMS[21] = OXYGEN

# The force, mass and velocity commands the status kernel must never call.
FORBIDDEN_STATUS_COMMANDS = (
    "addForce",
    "addTorque",
    "setVelocity",
    "setVelocityModelSpace",
    "forceSpeed",
    "setMass",
    "setCenterOfMass",
    "setVectorDir",
    "setVectorUp",
    "setVectorDirAndUp",
    "addForceGeneratorRTD",
)

# The systems driver and its ONE per-frame handler.
SYSTEMS_DRIVER = FUNCS / "fnc_updateAircraftSystems.sqf"
SYSTEMS_DRIVER_SRC = SYSTEMS_DRIVER.read_text(encoding="utf-8")
POSTINIT_PATH = REPO / "addons" / "flight" / "XEH_postInit.sqf"
POSTINIT_SRC = POSTINIT_PATH.read_text(encoding="utf-8")
DRIVER_KERNELS = (
    "updateFuelSystem",
    "updateEngineSystem",
    "updateDamageSystem",
    "updateStatusSystems",
)

# The systems row carries the numeric fields first, in the generated order:
# fuel (5), engine (6: design rpm, idle Ng, max Ng, max Np, max torque, max TGT),
# oil (2), then the remaining numeric fields and the three enum fields.
ENGINE_SYSTEMS = [
    0.0,  # 0 fuel_capacity
    0.0,  # 1 fuel_consumption_rate
    0.0,  # 2 fuel_density_kg_l
    0.0,  # 3 sfc_kg_kwh
    0.0,  # 4 fuel_cg_arm_m
    DESIGN_RPM,  # 5 engine_design_rpm
    IDLE_NG,  # 6 engine_idle_ng
    MAX_NG,  # 7 engine_max_ng
    0.0,  # 8 engine_max_np
    0.0,  # 9 engine_max_torque_nm
    MAX_TGT_C,  # 10 engine_max_tgt_c
    OIL_MIN_KPA,  # 11 engine_oil_pressure_min_kpa
    OIL_MAX_KPA,  # 12 engine_oil_pressure_max_kpa
    0.0,  # 13 transmission_torque_limit_nm
    0.0,  # 14 hydraulic_pressure_kpa
    0.0,  # 15 generator_power_kw
    0.0,  # 16 bus_voltage_v
    0.0,  # 17 battery_capacity_ah
    0.0,  # 18 cabin_pressure_max_kpa
    "",  # 19 fuel_type
    "",  # 20 engine_oil_type
    "",  # 21 oxygen_system
]


class Recorder:
    """The engine commands the kernel calls, captured for assertion."""

    def __init__(self) -> None:
        self.fuel: float | None = None
        self.com: list[float] | None = None


def run_kernel(
    systems: list[object],
    data: list[object],
    fuel_fraction: float = 1.0,
    delta_s: float = DELTA_S,
    is_local: bool = True,
    classes: tuple[str, ...] = ("Helicopter", "Air"),
    enabled: bool = True,
    alive: bool = True,
) -> tuple[object, Recorder]:
    """Run fnc_updateFuelSystem against a stub aircraft and systems row."""
    rec = Recorder()
    globals_: dict[str, object] = {
        "missionNamespace": object(),
        "getVariable": lambda ns, pair: (
            enabled if pair[0] == "__QEGVAR__core_enabled" else pair[1]
        ),
        "isNull": lambda v: v is None,
        "alive": lambda v: alive,
        "local": lambda v: is_local,
        "typeOf": lambda v: "Helicopter",
        "fuel": lambda v: fuel_fraction,
        "isKindOf": lambda obj, cls: cls in classes,
        "setFuel": lambda veh, value: setattr(rec, "fuel", value),
        "setCenterOfMass": lambda veh, value: setattr(rec, "com", value),
        "__FUNC__getAircraftSystems": lambda name: systems,
        "__FUNC__getAircraftData": lambda name: data,
        "__FUNC__calculateFuelBurn": lambda *args: run_sqf(BURN, list(args)),
    }
    result = run_sqf(KERNEL, ["fixture_aircraft", delta_s], globals_)
    return result, rec


class EngineRecorder:
    """The per-vehicle variables the engine kernel writes, captured."""

    def __init__(self) -> None:
        self.variables: dict[str, object] = {}


def run_engine_kernel(
    systems: list[object],
    wanted: float = 1.0,
    delta_s: float = DELTA_S,
    stored_ng: float = IDLE_NG,
    is_local: bool = True,
    classes: tuple[str, ...] = ("Helicopter", "Air"),
    enabled: bool = True,
    alive: bool = True,
    rtd: bool = False,
) -> tuple[object, EngineRecorder]:
    """Run fnc_updateEngineSystem against a stub aircraft and systems row."""
    rec = EngineRecorder()
    mission_ns = object()
    store: dict[str, object] = {"__QGVAR__engineNg": stored_ng}

    def get_variable(ns: object, pair: list[object]) -> object:
        name, default = pair[0], pair[1]
        if ns is mission_ns:
            return enabled if name == "__QEGVAR__core_enabled" else default
        return store.get(name, default)

    def set_variable(veh: object, pair: list[object]) -> None:
        name, value = pair[0], pair[1]
        store[name] = value
        rec.variables[name] = value
        return None

    globals_: dict[str, object] = {
        "missionNamespace": mission_ns,
        "getVariable": get_variable,
        "setVariable": set_variable,
        "isNull": lambda v: v is None,
        "alive": lambda v: alive,
        "local": lambda v: is_local,
        "typeOf": lambda v: "Helicopter",
        "isKindOf": lambda obj, cls: cls in classes,
        "difficultyEnabledRTD": rtd,
        "diag_deltaTime": DELTA_S,
        "AEE_ENGINE_SPOOL_TAU_S": SPOOL_TAU_S,
        "__FUNC__getAircraftSystems": lambda name: systems,
        "__FUNC__calculateEngineNg": lambda *args: run_sqf(NG, list(args)),
        "__FUNC__calculateScriptedTgtOil": lambda *args: run_sqf(TGT_OIL, list(args)),
    }
    result = run_sqf(ENGINE_KERNEL, ["fixture_aircraft", wanted, delta_s], globals_)
    return result, rec


class DamageRecorder:
    """The damage commands and variables the kernel writes, captured."""

    def __init__(self) -> None:
        self.variables: dict[str, object] = {}
        self.fuel: float | None = None
        self.hit_damage: list[tuple[object, object]] = []


def run_damage_kernel(
    systems: list[object],
    hit_names: tuple[str, ...] = ("hitengine",),
    hit_damages: tuple[float, ...] = (ENGINE_HIT_DAMAGE,),
    fuel_fraction: float = 1.0,
    delta_s: float = DELTA_S,
    is_local: bool = True,
    classes: tuple[str, ...] = ("Helicopter", "Air"),
    enabled: bool = True,
    alive: bool = True,
    damage_allowed: bool = True,
) -> tuple[object, DamageRecorder]:
    """Run fnc_updateDamageSystem against a stub aircraft and systems row."""
    rec = DamageRecorder()
    mission_ns = object()
    store: dict[str, object] = {}

    def get_variable(ns: object, pair: list[object]) -> object:
        name, default = pair[0], pair[1]
        if ns is mission_ns:
            return enabled if name == "__QEGVAR__core_enabled" else default
        return store.get(name, default)

    def set_variable(veh: object, pair: list[object]) -> None:
        name, value = pair[0], pair[1]
        store[name] = value
        rec.variables[name] = value
        return None

    def get_hit_point_damage(veh: object, name: object) -> float:
        target = str(name).lower()
        for i, hp in enumerate(hit_names):
            if hp.lower() == target:
                return hit_damages[i]
        return 0.0

    def set_hit_point_damage(veh: object, pair: list[object]) -> None:
        rec.hit_damage.append((pair[0], pair[1]))
        return None

    globals_: dict[str, object] = {
        "missionNamespace": mission_ns,
        "getVariable": get_variable,
        "setVariable": set_variable,
        "isNull": lambda v: v is None,
        "alive": lambda v: alive,
        "local": lambda v: is_local,
        "typeOf": lambda v: "Helicopter",
        "isKindOf": lambda obj, cls: cls in classes,
        "diag_deltaTime": DELTA_S,
        "isDamageAllowed": lambda v: damage_allowed,
        "getAllHitPointsDamage": lambda v: [
            list(hit_names),
            ["" for _ in hit_names],
            list(hit_damages),
        ],
        "getHitPointDamage": get_hit_point_damage,
        "setHitPointDamage": set_hit_point_damage,
        "fuel": lambda v: fuel_fraction,
        "setFuel": lambda veh, value: setattr(rec, "fuel", value),
        "__FUNC__getAircraftSystems": lambda name: systems,
    }
    result = run_sqf(DAMAGE_KERNEL, ["fixture_aircraft", delta_s], globals_)
    return result, rec


class TestPureFuelBurn(unittest.TestCase):
    """The pure arithmetic kernel, executed from its real SQF."""

    def test_a_sentinel_mass_burns_over_a_sentinel_interval(self) -> None:
        remaining, cg = run_sqf(
            BURN,
            [FULL_MASS_KG, SOURCED_RATE, 0.0, 0.0, DELTA_S, FULL_MASS_KG, CG_ARM_M],
        )
        self.assertAlmostEqual(
            remaining, FULL_MASS_KG - SOURCED_RATE * DELTA_S, places=9
        )
        self.assertAlmostEqual(cg, CG_ARM_M * (remaining / FULL_MASS_KG), places=9)

    def test_the_burn_derives_from_sfc_when_no_rate_is_sourced(self) -> None:
        sfc = 0.5  # kg/kWh
        rated_w = 100000.0
        remaining, _cg = run_sqf(
            BURN, [FULL_MASS_KG, 0.0, sfc, rated_w, DELTA_S, FULL_MASS_KG, CG_ARM_M]
        )
        expected_burn = sfc * rated_w / 3.6e6 * DELTA_S
        self.assertAlmostEqual(remaining, FULL_MASS_KG - expected_burn, places=9)

    def test_the_centre_of_gravity_moves_toward_the_datum_as_fuel_burns(self) -> None:
        before = CG_ARM_M * (FULL_MASS_KG / FULL_MASS_KG)
        _remaining, after = run_sqf(
            BURN,
            [FULL_MASS_KG, SOURCED_RATE, 0.0, 0.0, DELTA_S, FULL_MASS_KG, CG_ARM_M],
        )
        self.assertLess(after, before)

    def test_an_empty_tank_clamps_at_zero(self) -> None:
        remaining, cg = run_sqf(
            BURN, [0.5, 1.0, 0.0, 0.0, DELTA_S, FULL_MASS_KG, CG_ARM_M]
        )
        self.assertEqual(remaining, 0.0)
        self.assertEqual(cg, 0.0)

    def test_a_negative_mass_is_refused(self) -> None:
        self.assertEqual(
            run_sqf(
                BURN, [-1.0, SOURCED_RATE, 0.0, 0.0, DELTA_S, FULL_MASS_KG, CG_ARM_M]
            ),
            [-1, -1],
        )

    def test_a_negative_interval_is_refused(self) -> None:
        self.assertEqual(
            run_sqf(
                BURN,
                [FULL_MASS_KG, SOURCED_RATE, 0.0, 0.0, -1.0, FULL_MASS_KG, CG_ARM_M],
            ),
            [-1, -1],
        )

    def test_a_non_positive_full_mass_is_refused(self) -> None:
        self.assertEqual(
            run_sqf(
                BURN, [FULL_MASS_KG, SOURCED_RATE, 0.0, 0.0, DELTA_S, 0.0, CG_ARM_M]
            ),
            [-1, -1],
        )


class TestFuelKernel(unittest.TestCase):
    """The kernel, executed against a stub aircraft and a stub systems row."""

    def test_the_kernel_burns_the_sourced_rate_and_writes_setfuel(self) -> None:
        result, rec = run_kernel(SYSTEMS, DATA)
        self.assertTrue(result)
        expected_remaining = FULL_MASS_KG - SOURCED_RATE * DELTA_S
        self.assertAlmostEqual(rec.fuel, expected_remaining / FULL_MASS_KG, places=9)

    def test_the_kernel_writes_the_centre_of_gravity_delta(self) -> None:
        _result, rec = run_kernel(SYSTEMS, DATA)
        assert rec.com is not None
        expected_remaining = FULL_MASS_KG - SOURCED_RATE * DELTA_S
        expected_cg = CG_ARM_M * (expected_remaining / FULL_MASS_KG)
        self.assertAlmostEqual(rec.com[0], expected_cg, places=9)
        self.assertEqual(rec.com[1], 0)
        self.assertEqual(rec.com[2], 0)
        # The delta from the full-fuel centre of gravity is negative.
        self.assertAlmostEqual(
            rec.com[0] - CG_ARM_M,
            -CG_ARM_M * (SOURCED_RATE * DELTA_S / FULL_MASS_KG),
            places=9,
        )

    def test_the_kernel_uses_the_derived_burn_when_no_rate_is_sourced(self) -> None:
        systems = [FULL_CAPACITY_L, 0.0, DENSITY_KG_L, 0.5, CG_ARM_M]
        _result, rec = run_kernel(systems, [1100.0, 100000.0, 0.688, 0.0])
        assert rec.fuel is not None
        expected_remaining = FULL_MASS_KG - (0.5 * 100000.0 / 3.6e6 * DELTA_S)
        self.assertAlmostEqual(rec.fuel, expected_remaining / FULL_MASS_KG, places=9)

    def test_a_zero_capacity_is_refused_without_dividing(self) -> None:
        result, rec = run_kernel([0.0, SOURCED_RATE, DENSITY_KG_L, 0.0, CG_ARM_M], DATA)
        self.assertFalse(result)
        self.assertIsNone(rec.fuel)
        self.assertIsNone(rec.com)

    def test_a_zero_density_is_refused_without_dividing(self) -> None:
        result, rec = run_kernel(
            [FULL_CAPACITY_L, SOURCED_RATE, 0.0, 0.0, CG_ARM_M], DATA
        )
        self.assertFalse(result)
        self.assertIsNone(rec.fuel)

    def test_an_unknown_class_is_refused(self) -> None:
        result, rec = run_kernel([], DATA)
        self.assertFalse(result)
        self.assertIsNone(rec.fuel)

    def test_a_non_local_vehicle_is_refused(self) -> None:
        result, rec = run_kernel(SYSTEMS, DATA, is_local=False)
        self.assertFalse(result)
        self.assertIsNone(rec.fuel)

    def test_a_disabled_module_is_refused(self) -> None:
        result, rec = run_kernel(SYSTEMS, DATA, enabled=False)
        self.assertFalse(result)
        self.assertIsNone(rec.fuel)

    def test_a_dead_vehicle_is_refused(self) -> None:
        result, rec = run_kernel(SYSTEMS, DATA, alive=False)
        self.assertFalse(result)
        self.assertIsNone(rec.fuel)
        self.assertIsNone(rec.com)

    def test_a_parachute_is_refused(self) -> None:
        result, rec = run_kernel(SYSTEMS, DATA, classes=("Air", "ParachuteBase"))
        self.assertFalse(result)
        self.assertIsNone(rec.fuel)

    def test_a_non_air_vehicle_is_refused(self) -> None:
        result, rec = run_kernel(SYSTEMS, DATA, classes=())
        self.assertFalse(result)
        self.assertIsNone(rec.fuel)

    def test_the_fuel_fraction_is_clamped_to_one(self) -> None:
        # A full tank is 1.0. A stub that reports more must clamp, not overshoot.
        result, rec = run_kernel(SYSTEMS, DATA, fuel_fraction=1.5)
        self.assertTrue(result)
        self.assertEqual(rec.fuel, 1.0)


class TestKernelContract(unittest.TestCase):
    """The source contracts the harness cannot execute."""

    def test_the_kernel_reads_the_systems_row_and_the_pure_helper(self) -> None:
        self.assertIn("FUNC(getAircraftSystems)", KERNEL_SRC)
        self.assertIn("FUNC(calculateFuelBurn)", KERNEL_SRC)

    def test_the_kernel_writes_fuel_and_centre_of_mass(self) -> None:
        self.assertIn("setFuel", KERNEL_SRC)
        self.assertIn("setCenterOfMass", KERNEL_SRC)

    def test_the_kernel_gates_on_local_including_the_server(self) -> None:
        self.assertIn("if (!local _veh) exitWith { false };", KERNEL_SRC)
        header = KERNEL_SRC.split("*/", 1)[0]
        self.assertIn("DETERMINISTIC", header)
        self.assertIn("INCLUDING the server", header)

    def test_the_header_states_the_transfer_and_jettison_ceiling(self) -> None:
        header = KERNEL_SRC.split("*/", 1)[0]
        self.assertIn("TRANSFER", header)
        self.assertIn("JETTISON", header)

    def test_the_kernel_does_not_drive_the_pure_engine_kernel(self) -> None:
        self.assertNotIn("calculateAirEngineLoad", KERNEL_SRC)

    def test_both_functions_are_registered_once(self) -> None:
        for name in ("calculateFuelBurn", "updateFuelSystem"):
            hits = [line for line in PREP_SRC.splitlines() if name in line]
            self.assertEqual(len(hits), 1, hits)


class TestPureEngineNg(unittest.TestCase):
    """The pure spool kernel, executed from its real SQF."""

    def test_the_spool_rises_toward_the_limit(self) -> None:
        ng = run_sqf(NG, [IDLE_NG, MAX_NG, 1.0, SPOOL_TAU_S])
        self.assertGreater(ng, IDLE_NG)
        self.assertLessEqual(ng, MAX_NG)

    def test_the_spool_converges_to_the_limit(self) -> None:
        ng = IDLE_NG
        for _ in range(40):
            ng = run_sqf(NG, [ng, MAX_NG, 1.0, SPOOL_TAU_S])
        self.assertAlmostEqual(ng, MAX_NG, places=3)

    def test_a_zero_interval_holds_the_speed(self) -> None:
        self.assertEqual(run_sqf(NG, [IDLE_NG, MAX_NG, 0.0, SPOOL_TAU_S]), IDLE_NG)

    def test_a_negative_interval_is_refused(self) -> None:
        self.assertEqual(run_sqf(NG, [IDLE_NG, MAX_NG, -1.0, SPOOL_TAU_S]), -1)

    def test_a_non_positive_time_constant_is_refused(self) -> None:
        self.assertEqual(run_sqf(NG, [IDLE_NG, MAX_NG, 1.0, 0.0]), -1)

    def test_a_negative_current_speed_is_refused(self) -> None:
        self.assertEqual(run_sqf(NG, [-0.1, MAX_NG, 1.0, SPOOL_TAU_S]), -1)


class TestPureScriptedTgtOil(unittest.TestCase):
    """The pure scripted readout, executed from its real SQF."""

    def test_a_spooled_sentinel_speed_gives_a_readout_in_the_sourced_band(
        self,
    ) -> None:
        # Drive a sentinel Ng toward the sentinel limit, then map it.
        ng = IDLE_NG
        for _ in range(40):
            ng = run_sqf(NG, [ng, MAX_NG, 1.0, SPOOL_TAU_S])
        tgt, oil = run_sqf(
            TGT_OIL, [ng, IDLE_NG, MAX_NG, MAX_TGT_C, OIL_MIN_KPA, OIL_MAX_KPA]
        )
        self.assertGreaterEqual(tgt, 0.0)
        self.assertLessEqual(tgt, MAX_TGT_C)
        self.assertGreaterEqual(oil, OIL_MIN_KPA)
        self.assertLessEqual(oil, OIL_MAX_KPA)

    def test_the_readout_is_within_the_sourced_band_across_the_range(self) -> None:
        for ng in (IDLE_NG, 0.7, MAX_NG):
            tgt, oil = run_sqf(
                TGT_OIL, [ng, IDLE_NG, MAX_NG, MAX_TGT_C, OIL_MIN_KPA, OIL_MAX_KPA]
            )
            self.assertGreater(tgt, 0.0)
            self.assertLessEqual(tgt, MAX_TGT_C)
            self.assertGreaterEqual(oil, OIL_MIN_KPA)
            self.assertLessEqual(oil, OIL_MAX_KPA)

    def test_the_maximum_speed_gives_the_sourced_maxima(self) -> None:
        tgt, oil = run_sqf(
            TGT_OIL, [MAX_NG, IDLE_NG, MAX_NG, MAX_TGT_C, OIL_MIN_KPA, OIL_MAX_KPA]
        )
        self.assertAlmostEqual(tgt, MAX_TGT_C, places=9)
        self.assertAlmostEqual(oil, OIL_MAX_KPA, places=9)

    def test_the_idle_speed_gives_the_sourced_minimum_oil(self) -> None:
        _tgt, oil = run_sqf(
            TGT_OIL, [IDLE_NG, IDLE_NG, MAX_NG, MAX_TGT_C, OIL_MIN_KPA, OIL_MAX_KPA]
        )
        self.assertAlmostEqual(oil, OIL_MIN_KPA, places=9)

    def test_a_reversed_speed_band_is_refused(self) -> None:
        self.assertEqual(
            run_sqf(
                TGT_OIL,
                [MAX_NG, MAX_NG, IDLE_NG, MAX_TGT_C, OIL_MIN_KPA, OIL_MAX_KPA],
            ),
            [0, 0],
        )

    def test_a_non_positive_maximum_temperature_is_refused(self) -> None:
        self.assertEqual(
            run_sqf(
                TGT_OIL,
                [MAX_NG, IDLE_NG, MAX_NG, 0.0, OIL_MIN_KPA, OIL_MAX_KPA],
            ),
            [0, 0],
        )

    def test_a_reversed_oil_band_is_refused(self) -> None:
        self.assertEqual(
            run_sqf(
                TGT_OIL,
                [MAX_NG, IDLE_NG, MAX_NG, MAX_TGT_C, OIL_MAX_KPA, OIL_MIN_KPA],
            ),
            [0, 0],
        )


class TestEngineKernel(unittest.TestCase):
    """The kernel, executed against a stub aircraft and a stub systems row."""

    def test_the_kernel_spools_and_publishes_the_scripted_readout(self) -> None:
        result, rec = run_engine_kernel(ENGINE_SYSTEMS, wanted=1.0)
        self.assertTrue(result)
        ng = rec.variables["__QGVAR__engineNg"]
        tgt = rec.variables["__QGVAR__engineTgtC"]
        oil = rec.variables["__QGVAR__engineOilKpa"]
        self.assertGreater(ng, IDLE_NG)
        self.assertLessEqual(ng, MAX_NG)
        self.assertGreater(tgt, 0.0)
        self.assertLessEqual(tgt, MAX_TGT_C)
        self.assertGreaterEqual(oil, OIL_MIN_KPA)
        self.assertLessEqual(oil, OIL_MAX_KPA)

    def test_a_zero_command_spools_toward_the_sourced_idle(self) -> None:
        result, rec = run_engine_kernel(ENGINE_SYSTEMS, wanted=0.0, stored_ng=MAX_NG)
        self.assertTrue(result)
        ng = rec.variables["__QGVAR__engineNg"]
        self.assertLess(ng, MAX_NG)
        self.assertGreaterEqual(ng, IDLE_NG)

    def test_an_unknown_class_is_refused(self) -> None:
        result, rec = run_engine_kernel([])
        self.assertFalse(result)
        self.assertEqual(rec.variables, {})

    def test_a_non_local_vehicle_is_refused(self) -> None:
        result, _rec = run_engine_kernel(ENGINE_SYSTEMS, is_local=False)
        self.assertFalse(result)

    def test_a_disabled_module_is_refused(self) -> None:
        result, _rec = run_engine_kernel(ENGINE_SYSTEMS, enabled=False)
        self.assertFalse(result)

    def test_a_dead_vehicle_is_refused(self) -> None:
        result, _rec = run_engine_kernel(ENGINE_SYSTEMS, alive=False)
        self.assertFalse(result)

    def test_a_parachute_is_refused(self) -> None:
        result, _rec = run_engine_kernel(
            ENGINE_SYSTEMS, classes=("Air", "ParachuteBase")
        )
        self.assertFalse(result)

    def test_a_non_air_vehicle_is_refused(self) -> None:
        result, _rec = run_engine_kernel(ENGINE_SYSTEMS, classes=())
        self.assertFalse(result)

    def test_a_reversed_speed_band_is_refused(self) -> None:
        systems = list(ENGINE_SYSTEMS)
        systems[7] = IDLE_NG  # max Ng not above idle Ng
        result, _rec = run_engine_kernel(systems)
        self.assertFalse(result)

    def test_an_over_limit_command_is_accepted(self) -> None:
        # The kernel accepts a commanded ratio above the band and still
        # publishes one spool state and the scripted readout.
        result, rec = run_engine_kernel(ENGINE_SYSTEMS, wanted=2.0, stored_ng=IDLE_NG)
        self.assertTrue(result)
        self.assertGreater(rec.variables["__QGVAR__engineNg"], IDLE_NG)
        self.assertEqual(
            set(rec.variables),
            {"__QGVAR__engineNg", "__QGVAR__engineTgtC", "__QGVAR__engineOilKpa"},
        )

    def test_a_single_engine_systems_row_publishes_one_spool_state(self) -> None:
        # The kernel manages one local engine, so it publishes exactly the
        # three engine variables for that one engine and nothing else.
        result, rec = run_engine_kernel(ENGINE_SYSTEMS, wanted=1.0)
        self.assertTrue(result)
        self.assertEqual(
            set(rec.variables),
            {"__QGVAR__engineNg", "__QGVAR__engineTgtC", "__QGVAR__engineOilKpa"},
        )


class TestEngineKernelContract(unittest.TestCase):
    """The source contracts the harness cannot execute."""

    def test_the_kernel_uses_the_rtd_command_and_not_the_missing_one(self) -> None:
        self.assertIn("setWantedRPMRTD", ENGINE_KERNEL_SRC)
        self.assertNotIn("setEngineRpmRTD", ENGINE_KERNEL_SRC)

    def test_the_kernel_reads_the_live_speed_with_the_real_getter(self) -> None:
        # The phantom reader rpmRTD is not a command; the real getter returns
        # an array of engine RPM values.
        self.assertIn("enginesRpmRTD", ENGINE_KERNEL_SRC)
        self.assertNotIn("rpmRTD", ENGINE_KERNEL_SRC)

    def test_the_kernel_commands_the_array_form(self) -> None:
        # setWantedRPMRTD takes [rpm, seconds, engineIndex], not a bare ratio.
        body = ENGINE_KERNEL_SRC.split("*/", 1)[1]
        self.assertIn("setWantedRPMRTD [", body)

    def test_the_kernel_names_the_target_rpm_fallback(self) -> None:
        self.assertIn("getEngineTargetRPMRTD", ENGINE_KERNEL_SRC)

    def test_the_header_names_the_design_rpm_base(self) -> None:
        header = ENGINE_KERNEL_SRC.split("*/", 1)[0]
        self.assertIn("engine_design_rpm", header)

    def test_the_base_and_fallback_sit_under_the_flight_model_gate(self) -> None:
        body = ENGINE_KERNEL_SRC.split("*/", 1)[1]
        guard = body.find("difficultyEnabledRTD")
        fallback = body.find("getEngineTargetRPMRTD")
        base = body.find("_baseRpm = _designRpm")
        self.assertNotEqual(guard, -1)
        self.assertNotEqual(fallback, -1)
        self.assertNotEqual(base, -1)
        self.assertLess(guard, fallback)

    def test_the_kernel_guards_the_rtd_path_on_the_flight_model(self) -> None:
        # The guard and the command both live in the body, after the header.
        body = ENGINE_KERNEL_SRC.split("*/", 1)[1]
        guard = body.find("difficultyEnabledRTD")
        command = body.find("setWantedRPMRTD")
        self.assertNotEqual(guard, -1)
        self.assertLess(guard, command)

    def test_the_rtd_guard_wraps_the_getter_and_the_command(self) -> None:
        # The getter is compiled from a string and the command is issued only
        # under the advanced flight model, so the guard precedes both.
        body = ENGINE_KERNEL_SRC.split("*/", 1)[1]
        guard = body.find("difficultyEnabledRTD")
        getter = body.find("compile _reader")
        command = body.find("setWantedRPMRTD")
        self.assertNotEqual(guard, -1)
        self.assertNotEqual(getter, -1)
        self.assertNotEqual(command, -1)
        self.assertLess(guard, getter)
        self.assertLess(guard, command)

    def test_the_kernel_clamps_an_over_limit_command(self) -> None:
        # The commanded ratio is clamped to the ratio range before it selects
        # the sourced band, so an over-limit command cannot exceed the sourced
        # maximum in the engine. The kernel carries no separate torque hook:
        # the spool command is the limit.
        self.assertIn("(_wanted max 0 min 1)", ENGINE_KERNEL_SRC)

    def test_the_kernel_reads_the_systems_row_and_both_pure_helpers(self) -> None:
        self.assertIn("FUNC(getAircraftSystems)", ENGINE_KERNEL_SRC)
        self.assertIn("FUNC(calculateEngineNg)", ENGINE_KERNEL_SRC)
        self.assertIn("FUNC(calculateScriptedTgtOil)", ENGINE_KERNEL_SRC)

    def test_the_header_states_the_engine_ceiling(self) -> None:
        header = ENGINE_KERNEL_SRC.split("*/", 1)[0]
        self.assertIn("turbine temperature", header)
        self.assertIn("SCRIPTED", header)
        self.assertIn("NOT A MEASUREMENT", header)

    def test_the_header_states_the_rtd_only_command(self) -> None:
        header = ENGINE_KERNEL_SRC.split("*/", 1)[0]
        self.assertIn("RTD-ONLY", header)
        self.assertIn("no-op", header)

    def test_the_kernel_gates_on_local_including_the_server(self) -> None:
        self.assertIn("if (!local _veh) exitWith { false };", ENGINE_KERNEL_SRC)
        header = ENGINE_KERNEL_SRC.split("*/", 1)[0]
        self.assertIn("INCLUDING the server", header)

    def test_the_kernel_does_not_drive_the_air_engine_load_kernel(self) -> None:
        self.assertNotIn("calculateAirEngineLoad", ENGINE_KERNEL_SRC)

    def test_the_scripted_helper_never_claims_a_measurement(self) -> None:
        self.assertIn("NOT A MEASUREMENT", TGT_OIL_SRC)

    def test_all_three_functions_are_registered_once(self) -> None:
        for name in (
            "calculateEngineNg",
            "calculateScriptedTgtOil",
            "updateEngineSystem",
        ):
            hits = [line for line in PREP_SRC.splitlines() if name in line]
            self.assertEqual(len(hits), 1, hits)


class TestDamageKernel(unittest.TestCase):
    """The damage kernel, executed against a stub aircraft and systems row."""

    def test_a_sentinel_engine_hit_reduces_the_power_fraction(self) -> None:
        result, rec = run_damage_kernel(SYSTEMS)
        self.assertTrue(result)
        severity = (ENGINE_HIT_DAMAGE - DAMAGE_THRESHOLD) / (1 - DAMAGE_THRESHOLD)
        self.assertAlmostEqual(
            rec.variables["aee_enginePowerFraction"], 1 - severity, places=9
        )

    def test_a_damage_refusing_vehicle_is_suppressed(self) -> None:
        result, rec = run_damage_kernel(SYSTEMS, damage_allowed=False)
        self.assertFalse(result)
        self.assertEqual(rec.variables, {})
        self.assertIsNone(rec.fuel)
        self.assertEqual(rec.hit_damage, [])


class TestDamageKernelContract(unittest.TestCase):
    """The source contracts the harness cannot execute."""

    def test_the_kernel_respects_the_damage_allowed_state(self) -> None:
        self.assertIn("isDamageAllowed _veh", DAMAGE_KERNEL_SRC)
        self.assertIn("setHitPointDamage", DAMAGE_KERNEL_SRC)

    def test_the_kernel_reads_both_hit_point_commands(self) -> None:
        self.assertIn("getAllHitPointsDamage", DAMAGE_KERNEL_SRC)
        self.assertIn("getHitPointDamage", DAMAGE_KERNEL_SRC)

    def test_the_kernel_writes_the_existing_power_fraction_variable(self) -> None:
        self.assertIn("aee_enginePowerFraction", DAMAGE_KERNEL_SRC)

    def test_the_header_states_the_damage_ceiling(self) -> None:
        header = DAMAGE_KERNEL_SRC.split("*/", 1)[0]
        self.assertIn("CONFIG-DRIVEN", header)
        self.assertIn("EXTEND", header)
        self.assertIn("REPLACE", header)

    def test_the_function_is_registered_once(self) -> None:
        hits = [line for line in PREP_SRC.splitlines() if "updateDamageSystem" in line]
        self.assertEqual(len(hits), 1, hits)


class TestDamageEffects(unittest.TestCase):
    """The per-system effects, executed against a stub aircraft and row."""

    def test_the_kernel_maps_a_lowercase_engine_hit_to_the_engine_role(self) -> None:
        # getAllHitPointsDamage returns lowercase names. The kernel must
        # normalise to the map case and apply the engine effect.
        result, rec = run_damage_kernel(SYSTEMS, hit_names=("hitengine",))
        self.assertTrue(result)
        self.assertIn("aee_enginePowerFraction", rec.variables)
        self.assertLess(rec.variables["aee_enginePowerFraction"], 1.0)

    def test_the_kernel_ignores_a_hit_point_outside_the_role_map(self) -> None:
        # An unmapped name must not change the effect. The engine hit drives
        # the fraction, so the unmapped high damage is ignored.
        _result, mapped = run_damage_kernel(
            SYSTEMS, hit_names=("hitengine",), hit_damages=(ENGINE_HIT_DAMAGE,)
        )
        _result2, extra = run_damage_kernel(
            SYSTEMS,
            hit_names=("hitengine", "hitsensor"),
            hit_damages=(ENGINE_HIT_DAMAGE, 0.9),
        )
        self.assertEqual(
            mapped.variables["aee_enginePowerFraction"],
            extra.variables["aee_enginePowerFraction"],
        )

    def test_the_power_fraction_falls_as_engine_damage_rises(self) -> None:
        _r1, light = run_damage_kernel(SYSTEMS, hit_damages=(0.3,))
        _r2, heavy = run_damage_kernel(SYSTEMS, hit_damages=(0.9,))
        light_fraction = light.variables["aee_enginePowerFraction"]
        heavy_fraction = heavy.variables["aee_enginePowerFraction"]
        self.assertLess(heavy_fraction, light_fraction)
        self.assertGreater(light_fraction, 0.0)
        self.assertLess(heavy_fraction, 1.0)

    def test_a_sentinel_fuel_hit_leaks_the_sourced_rate(self) -> None:
        result, rec = run_damage_kernel(
            SYSTEMS, hit_names=("hitfuel",), hit_damages=(FUEL_HIT_DAMAGE,)
        )
        self.assertTrue(result)
        assert rec.fuel is not None
        severity = (FUEL_HIT_DAMAGE - DAMAGE_THRESHOLD) / (1 - DAMAGE_THRESHOLD)
        leaked_kg = SOURCED_RATE * severity * DELTA_S
        expected = (FULL_MASS_KG - leaked_kg) / FULL_MASS_KG
        self.assertAlmostEqual(rec.fuel, expected, places=9)

    def test_a_healthy_tank_does_not_leak(self) -> None:
        result, rec = run_damage_kernel(
            SYSTEMS, hit_names=("hitfuel",), hit_damages=(0.0,)
        )
        self.assertTrue(result)
        self.assertIsNone(rec.fuel)

    def test_a_sentinel_rotor_hit_publishes_an_imbalance(self) -> None:
        result, rec = run_damage_kernel(
            SYSTEMS, hit_names=("hitmainrotor",), hit_damages=(ROTOR_HIT_DAMAGE,)
        )
        self.assertTrue(result)
        severity = (ROTOR_HIT_DAMAGE - DAMAGE_THRESHOLD) / (1 - DAMAGE_THRESHOLD)
        self.assertAlmostEqual(
            rec.variables["__QGVAR__rotorImbalance"], severity, places=9
        )

    def test_a_healthy_rotor_publishes_zero_imbalance(self) -> None:
        result, rec = run_damage_kernel(
            SYSTEMS, hit_names=("hitmainrotor",), hit_damages=(0.0,)
        )
        self.assertTrue(result)
        self.assertEqual(rec.variables["__QGVAR__rotorImbalance"], 0.0)

    def test_a_damaged_system_advances_progressively(self) -> None:
        result, rec = run_damage_kernel(SYSTEMS, hit_damages=(ENGINE_HIT_DAMAGE,))
        self.assertTrue(result)
        self.assertEqual(len(rec.hit_damage), 1)
        name, advanced = rec.hit_damage[0]
        self.assertEqual(name, "HitEngine")
        self.assertAlmostEqual(advanced, ENGINE_HIT_DAMAGE + 0.001 * DELTA_S, places=9)

    def test_a_repaired_system_returns_to_healthy(self) -> None:
        result, rec = run_damage_kernel(
            SYSTEMS,
            hit_names=("hitengine", "hitfuel", "hitmainrotor"),
            hit_damages=(0.0, 0.0, 0.0),
        )
        self.assertTrue(result)
        self.assertEqual(rec.variables["aee_enginePowerFraction"], 1.0)
        self.assertEqual(rec.variables["__QGVAR__rotorImbalance"], 0.0)
        self.assertIsNone(rec.fuel)
        self.assertEqual(rec.hit_damage, [])

    def test_the_suppression_stops_the_leak_and_the_imbalance(self) -> None:
        result, rec = run_damage_kernel(
            SYSTEMS,
            hit_names=("hitfuel", "hitmainrotor"),
            hit_damages=(FUEL_HIT_DAMAGE, ROTOR_HIT_DAMAGE),
            damage_allowed=False,
        )
        self.assertFalse(result)
        self.assertEqual(rec.variables, {})
        self.assertIsNone(rec.fuel)
        self.assertEqual(rec.hit_damage, [])


def kernel_role_map() -> dict[str, str]:
    """The role map the kernel holds, read from its source arrays."""
    names = re.search(r"_roleNames = \[(.*?)\]", DAMAGE_KERNEL_SRC, re.DOTALL)
    tokens = re.search(r"_roleTokens = \[(.*?)\]", DAMAGE_KERNEL_SRC, re.DOTALL)
    assert names is not None
    assert tokens is not None
    keys = re.findall(r'"([^"]+)"', names.group(1))
    values = re.findall(r'"([^"]+)"', tokens.group(1))
    return dict(zip(keys, values, strict=True))


def damage_corpus() -> dict[str, object]:
    """The damage role corpus, loaded from the JSON file."""
    path = REPO / "data" / "aircraft" / "damage_roles.json"
    return json.loads(path.read_text(encoding="utf-8"))


class TestDamageRoleMap(unittest.TestCase):
    """The role map the kernel holds must equal the JSON corpus."""

    def test_the_kernel_role_map_matches_the_json_corpus(self) -> None:
        self.assertEqual(kernel_role_map(), damage_corpus()["hit_points"])

    def test_the_kernel_role_tokens_are_a_subset_of_the_roles(self) -> None:
        corpus = damage_corpus()
        roles = set(corpus["roles"])
        self.assertTrue(set(kernel_role_map().values()) <= roles)


class StatusRecorder:
    """The per-vehicle variables the status kernel publishes, captured."""

    def __init__(self) -> None:
        self.variables: dict[str, object] = {}


def run_status_kernel(
    systems: list[object],
    is_local: bool = True,
    classes: tuple[str, ...] = ("Helicopter", "Air"),
    enabled: bool = True,
    alive: bool = True,
) -> tuple[object, StatusRecorder]:
    """Run fnc_updateStatusSystems against a stub aircraft and systems row."""
    rec = StatusRecorder()
    mission_ns = object()
    store: dict[str, object] = {}

    def get_variable(ns: object, pair: list[object]) -> object:
        name, default = pair[0], pair[1]
        if ns is mission_ns:
            return enabled if name == "__QEGVAR__core_enabled" else default
        return store.get(name, default)

    def set_variable(veh: object, pair: list[object]) -> None:
        store[pair[0]] = pair[1]
        rec.variables[pair[0]] = pair[1]
        return None

    globals_: dict[str, object] = {
        "missionNamespace": mission_ns,
        "getVariable": get_variable,
        "setVariable": set_variable,
        "isNull": lambda v: v is None,
        "alive": lambda v: alive,
        "local": lambda v: is_local,
        "typeOf": lambda v: "Helicopter",
        "isKindOf": lambda obj, cls: cls in classes,
        "diag_deltaTime": DELTA_S,
        "__FUNC__getAircraftSystems": lambda name: systems,
    }
    result = run_sqf(STATUS_KERNEL, ["fixture_aircraft", DELTA_S], globals_)
    return result, rec


class TestStatusKernel(unittest.TestCase):
    """The status kernel, executed against a stub aircraft and systems row."""

    def test_the_kernel_publishes_the_sourced_hydraulic_pressure(self) -> None:
        result, rec = run_status_kernel(list(STATUS_SYSTEMS))
        self.assertTrue(result)
        self.assertEqual(
            rec.variables["__QGVAR__statusHydraulicPressureKpa"], HYDRAULIC_KPA
        )

    def test_the_kernel_publishes_the_sourced_generator_power(self) -> None:
        result, rec = run_status_kernel(list(STATUS_SYSTEMS))
        self.assertTrue(result)
        self.assertEqual(rec.variables["__QGVAR__statusGeneratorPowerKw"], GENERATOR_KW)

    def test_the_kernel_publishes_the_sourced_bus_voltage(self) -> None:
        result, rec = run_status_kernel(list(STATUS_SYSTEMS))
        self.assertTrue(result)
        self.assertEqual(rec.variables["__QGVAR__statusBusVoltageV"], BUS_V)

    def test_the_kernel_publishes_the_sourced_battery_charge(self) -> None:
        result, rec = run_status_kernel(list(STATUS_SYSTEMS))
        self.assertTrue(result)
        self.assertEqual(rec.variables["__QGVAR__statusBatteryChargeAh"], BATTERY_AH)

    def test_the_kernel_publishes_the_sourced_cabin_pressure(self) -> None:
        result, rec = run_status_kernel(list(STATUS_SYSTEMS))
        self.assertTrue(result)
        self.assertEqual(rec.variables["__QGVAR__statusCabinPressureMaxKpa"], CABIN_KPA)

    def test_the_kernel_publishes_the_oxygen_token(self) -> None:
        result, rec = run_status_kernel(list(STATUS_SYSTEMS))
        self.assertTrue(result)
        self.assertEqual(rec.variables["__QGVAR__statusOxygenSystem"], OXYGEN)

    def test_the_kernel_publishes_exactly_the_six_status_variables(self) -> None:
        result, rec = run_status_kernel(list(STATUS_SYSTEMS))
        self.assertTrue(result)
        self.assertEqual(
            set(rec.variables),
            {
                "__QGVAR__statusHydraulicPressureKpa",
                "__QGVAR__statusGeneratorPowerKw",
                "__QGVAR__statusBusVoltageV",
                "__QGVAR__statusBatteryChargeAh",
                "__QGVAR__statusCabinPressureMaxKpa",
                "__QGVAR__statusOxygenSystem",
            },
        )

    def test_an_unknown_class_is_refused(self) -> None:
        result, rec = run_status_kernel([])
        self.assertFalse(result)
        self.assertEqual(rec.variables, {})

    def test_a_short_row_is_refused(self) -> None:
        result, rec = run_status_kernel([0] * (STATUS_THRESHOLD - 1))
        self.assertFalse(result)
        self.assertEqual(rec.variables, {})

    def test_a_negative_figure_is_refused(self) -> None:
        systems = list(STATUS_SYSTEMS)
        systems[14] = -1.0
        result, rec = run_status_kernel(systems)
        self.assertFalse(result)
        self.assertEqual(rec.variables, {})

    def test_a_non_local_vehicle_is_refused(self) -> None:
        result, rec = run_status_kernel(list(STATUS_SYSTEMS), is_local=False)
        self.assertFalse(result)
        self.assertEqual(rec.variables, {})

    def test_a_disabled_module_is_refused(self) -> None:
        result, rec = run_status_kernel(list(STATUS_SYSTEMS), enabled=False)
        self.assertFalse(result)
        self.assertEqual(rec.variables, {})

    def test_a_dead_vehicle_is_refused(self) -> None:
        result, rec = run_status_kernel(list(STATUS_SYSTEMS), alive=False)
        self.assertFalse(result)
        self.assertEqual(rec.variables, {})

    def test_a_parachute_is_refused(self) -> None:
        result, rec = run_status_kernel(
            list(STATUS_SYSTEMS), classes=("Air", "ParachuteBase")
        )
        self.assertFalse(result)
        self.assertEqual(rec.variables, {})

    def test_a_non_air_vehicle_is_refused(self) -> None:
        result, rec = run_status_kernel(list(STATUS_SYSTEMS), classes=())
        self.assertFalse(result)
        self.assertEqual(rec.variables, {})


class TestStatusKernelContract(unittest.TestCase):
    """The source contracts the harness cannot execute."""

    def test_the_kernel_reads_the_systems_row(self) -> None:
        self.assertIn("FUNC(getAircraftSystems)", STATUS_KERNEL_SRC)

    def test_the_kernel_never_calls_a_force_mass_or_velocity_command(self) -> None:
        for command in FORBIDDEN_STATUS_COMMANDS:
            self.assertNotIn(command, STATUS_KERNEL_SRC, command)

    def test_the_header_states_the_status_only_ceiling(self) -> None:
        header = STATUS_KERNEL_SRC.split("*/", 1)[0]
        self.assertIn("status only", header)
        self.assertIn("ABSENT", header)
        self.assertIn("NOT engine-observed", header)
        self.assertIn("flight dynamics model", header)

    def test_the_kernel_gates_on_local_including_the_server(self) -> None:
        self.assertIn("if (!local _veh) exitWith { false };", STATUS_KERNEL_SRC)
        header = STATUS_KERNEL_SRC.split("*/", 1)[0]
        self.assertIn("INCLUDING the server", header)

    def test_the_function_is_registered_once(self) -> None:
        hits = [line for line in PREP_SRC.splitlines() if "updateStatusSystems" in line]
        self.assertEqual(len(hits), 1, hits)


class TestSystemsDriverContract(unittest.TestCase):
    """The source contracts the harness cannot execute."""

    def test_exactly_one_per_frame_handler_is_registered_for_the_systems(self) -> None:
        # The driver is registered exactly once...
        self.assertEqual(POSTINIT_SRC.count("call FUNC(updateAircraftSystems)"), 1)
        # ...and that registration is a CBA per-frame handler.
        index = POSTINIT_SRC.index("call FUNC(updateAircraftSystems)")
        tail = POSTINIT_SRC[index:]
        self.assertLess(tail.index("CBA_fnc_addPerFrameHandler"), 200)

    def test_the_driver_calls_all_four_kernels(self) -> None:
        for kernel in DRIVER_KERNELS:
            self.assertIn(f"FUNC({kernel})", SYSTEMS_DRIVER_SRC, kernel)

    def test_the_driver_guards_on_the_kernels_being_present(self) -> None:
        for kernel in DRIVER_KERNELS:
            self.assertIn(f"isNil QFUNC({kernel})", SYSTEMS_DRIVER_SRC, kernel)

    def test_the_driver_runs_on_local_vehicles_including_the_server(self) -> None:
        self.assertIn("local _x", SYSTEMS_DRIVER_SRC)
        header = SYSTEMS_DRIVER_SRC.split("*/", 1)[0]
        self.assertIn("INCLUDING the server", header)

    def test_the_driver_guards_on_the_airframe_being_an_aircraft(self) -> None:
        self.assertIn('isKindOf "Air"', SYSTEMS_DRIVER_SRC)
        self.assertIn('isKindOf "ParachuteBase"', SYSTEMS_DRIVER_SRC)

    def test_the_handler_passes_elapsed_mission_time_not_a_tick_count(self) -> None:
        # The handler computes the elapsed mission time and passes it to the
        # driver, so every machine that owns the airframe agrees.
        self.assertIn("time", POSTINIT_SRC)
        self.assertIn("aircraftSystemsLastTime", POSTINIT_SRC)
        self.assertIn("[_delta] call FUNC(updateAircraftSystems)", POSTINIT_SRC)

    def test_the_driver_is_registered_once_in_prep(self) -> None:
        hits = [
            line for line in PREP_SRC.splitlines() if "updateAircraftSystems" in line
        ]
        self.assertEqual(len(hits), 1, hits)

    def test_the_driver_reads_the_engine_state_not_its_own_output(self) -> None:
        # The commanded band follows isEngineOn and isTouchingGround. The
        # driver must not feed the kernel its own last spool output.
        self.assertIn("isEngineOn", SYSTEMS_DRIVER_SRC)
        self.assertIn("isTouchingGround", SYSTEMS_DRIVER_SRC)
        self.assertNotIn("getVariable [QGVAR(engineNg)", SYSTEMS_DRIVER_SRC)


if __name__ == "__main__":
    unittest.main()
