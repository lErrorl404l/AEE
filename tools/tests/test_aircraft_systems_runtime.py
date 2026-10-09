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

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools" / "tests"))

from sqf_lite import run_sqf  # noqa: E402

FUNCS = REPO / "addons" / "mobility" / "functions"
BURN = FUNCS / "fnc_calculateFuelBurn.sqf"
KERNEL = FUNCS / "fnc_updateFuelSystem.sqf"
PREP_PATH = REPO / "addons" / "mobility" / "XEH_PREP.hpp"

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


if __name__ == "__main__":
    unittest.main()
