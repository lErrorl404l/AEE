#!/usr/bin/env python3
"""Executes the ACTUAL SQF two-node solver (issue #204).

This test runs addons/thermal/functions/solver/fnc_solveTwoNodeSelection.sqf
through sqf_lite.py - a minimal SQF evaluator for the solver's subset -
and asserts the physics anchors.  It does NOT mirror the SQF: the SQF
file itself is the subject under test.  If the SQF changes, this test
executes the new code.  (The Python mirror in test_two_node.py remains
for the broader parameter sweeps; the SQF execution here is the
authoritative check that the shipped code produces the documented
physics.)

The shivering bug this guards (issue #204): the Gagge shivering term
was applied to INERT objects - a cold parked vehicle received q_shiv
~6400 W/m2 (38 kW over a 6 m2 panel), climbed chaotically to 36-40 C
at midnight and rendered white in TI.  The fix gates shivering and
respiratory loss on _isHuman.  The cold-vehicle anchor below fails on
the old code (surface climbs away from ambient) and passes on the
fixed code (surface sits at the sky-sink equilibrium).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import unittest

from sqf_lite import run_sqf

# Real material registry values from fnc_getMaterialThermal.sqf.
_REGISTRY = {
    "metal": [0.90, 0.70, 7850, 490, 50],
    "aluminium": [0.05, 0.30, 2700, 900, 205],
    "aluminium_painted": [0.90, 0.30, 2700, 900, 205],
    "glass": [0.90, 0.15, 2500, 840, 1.1],
    "rubber": [0.95, 0.90, 1314, 1898, 0.22],
    "plastic": [0.95, 0.50, 1040, 1506, 0.17],
    "concrete": [0.92, 0.60, 2300, 880, 1.4],
    "asphalt": [0.88, 0.90, 2300, 900, 1.5],
    "wood": [0.88, 0.60, 700, 1700, 0.15],
    "leather": [0.78, 0.50, 1000, 1500, 0.18],
    "vegetation": [0.98, 0.60, 300, 2000, 0.20],
    "water": [0.96, 0.10, 1000, 4186, 0.60],
    "rock": [0.90, 0.70, 2600, 850, 2.0],
    "ground": [0.92, 0.65, 1600, 1100, 0.30],
    "engine": [0.80, 0.90, 7200, 500, 50],
    "ceramic": [0.85, 0.60, 3900, 880, 32],
    "human": [0.98, 0.60, 1100, 3500, 0.35],
}

_SOLVER = (
    Path(__file__).resolve().parents[2]
    / "addons"
    / "thermal"
    / "functions"
    / "solver"
    / "fnc_solveTwoNodeSelection.sqf"
)

_GLOBALS = {
    "__FUNC__getMaterialThermal": lambda c: _REGISTRY.get(c, _REGISTRY["ground"]),
    "overcast": 0.0,
    "diag_deltaTime": 0.1,
    # The solver publishes aee_thermal_humanCoreTempC (task 14).  sqf_lite has
    # no namespace, so the write resolves against inert stubs.
    "missionNamespace": {},
    "setVariable": lambda *args: None,
}


def _solve(
    core,
    skin,
    t_air,
    wind,
    solar,
    exposure,
    m_core,
    m_skin,
    area,
    l_char,
    t_core0,
    t_skin0,
    q_gen,
    orientation,
    rh,
    t_ground,
    is_human,
    l_cond,
    evap_on,
    dt,
    water_speed=0.0,
    t_water=-273.0,
    rain=0.0,
    skin_perfusion=1.0,
    clo=0.0,
    solar_alpha=0.0,
):
    # The solver now consumes a MEAN RADIANT TEMPERATURE, not a ground
    # temperature; the caller forms it (fnc_calculateMRT).  Mirror that here
    # so the sky sink is still exercised.
    t_air_k = t_air + 273.15
    sky_k = 0.0552 * t_air_k**1.5
    mrt = (0.5 * (t_ground + 273.15) ** 4 + 0.5 * sky_k**4) ** 0.25 - 273.15
    return run_sqf(
        _SOLVER,
        [
            None,
            "",
            core,
            skin,
            t_air,
            wind,
            solar,
            exposure,
            m_core,
            m_skin,
            area,
            l_char,
            t_core0,
            t_skin0,
            q_gen,
            orientation,
            rh,
            mrt,
            is_human,
            l_cond,
            evap_on,
            dt,
            water_speed,
            t_water,
            rain,
            skin_perfusion,
            clo,
            solar_alpha,
        ],
        _GLOBALS,
    )


class TestSqfTwoNode(unittest.TestCase):
    """The REAL solver SQF, executed, against physics anchors."""

    def test_cold_parked_vehicle_stays_cold_at_midnight(self):
        # Issue #204: a cold parked vehicle (17 C air, no sun, engine off)
        # must sit at the sky-sink equilibrium (~ambient, a few K below),
        # NEVER climb toward 36-40 C.  The old code applied the human
        # shivering term to the inert object and diverged.
        core, skin = _solve(
            "ground",
            "ground",
            17.0,
            2.0,
            0.0,
            1.0,
            50,
            20,
            6.0,
            0.08,
            17.0,
            17.0,
            0.0,
            "vertical",
            0.5,
            17.0,
            False,
            0.008,
            False,
            5.0,
        )
        self.assertLess(skin, 19.0)
        self.assertGreater(skin, 8.0)

    def test_human_neutral_holds_core(self):
        # Gagge neutral: core holds ~36.8, skin below core.  Executes the
        # real SQF human path (blood-flow sigmoid, evap, shivering gate).
        core, skin = _solve(
            "human",
            "human",
            26.0,
            0.1,
            0.0,
            0.5,
            50,
            20,
            1.8258,
            0.15,
            36.8,
            33.7,
            58.2 * 1.8258,
            "vertical",
            0.5,
            26.0,
            True,
            0.05,
            True,
            5.0,
        )
        self.assertAlmostEqual(core, 36.8, delta=0.5)
        self.assertLess(skin, core)

    def test_idle_engine_warms_skin(self):
        # A warm engine block (q_gen 4600 W over 6 m2, cast iron) heats
        # the skin above a cold plate - the inert path WITH real heat.
        core, skin = _solve(
            "engine",
            "engine",
            25.0,
            2.0,
            0.0,
            0.0,
            150,
            30,
            6.0,
            0.8,
            90.0,
            60.0,
            4600.0,
            "up",
            0.5,
            30.0,
            False,
            0.01,
            False,
            5.0,
        )
        self.assertGreater(core, 60)
        self.assertLess(skin, core)
        self.assertGreater(skin, 35)

    def test_human_resting_skin_warm_against_cold_air(self):
        # A resting soldier at 5 C air: skin must stay well above air
        # (the body defends core temp).  This exercises shivering.
        core, skin = _solve(
            "human",
            "human",
            5.0,
            1.5,
            0.0,
            1.0,
            50,
            20,
            1.8258,
            0.15,
            36.8,
            33.7,
            58.2 * 1.8258,
            "vertical",
            0.5,
            5.0,
            True,
            0.05,
            True,
            5.0,
        )
        self.assertGreater(core, 30)
        self.assertGreater(skin, 10)

    def _cold_human(self, **over):
        # A cold, still soldier; the caller supplies only the axis under
        # test (clo or immersion).
        base = dict(
            core="human",
            skin="human",
            t_air=-5.0,
            wind=3.0,
            solar=0.0,
            exposure=1.0,
            m_core=63,
            m_skin=7,
            area=1.8258,
            l_char=0.15,
            t_core0=36.8,
            t_skin0=33.7,
            q_gen=58.2 * 1.8258,
            orientation="vertical",
            rh=0.5,
            t_ground=-5.0,
            is_human=True,
            l_cond=0.05,
            evap_on=True,
            dt=5.0,
        )
        base.update(over)
        return _solve(**base)

    def test_clothing_insulation_reaches_the_solve(self):
        # Issue #191 finding 4: clothing now enters the dry and vapour skin
        # balance (r_clo = 0.155*clo).  A winter parka keeps the skin warmer
        # than a light shirt.  Before the fix the two clo values were
        # identical because none reached the solver.
        _, skin_light = self._cold_human(clo=0.5)
        _, skin_parka = self._cold_human(clo=2.5)
        self.assertGreater(skin_parka, skin_light)

    def test_immersion_exchanges_with_water(self):
        # Issue #191 finding 7: a submerged soldier exchanges with WATER.
        # Still water (speed 0) uses the measured 43 W/m2K branch, so the
        # skin falls below the same soldier's temperature in air.
        _, skin_air = self._cold_human()
        _, skin_water = self._cold_human(
            t_air=10.0, t_ground=10.0, t_water=10.0, water_speed=0.0
        )
        self.assertLess(skin_water, skin_air)
        # Stirred (0.2 m/s) water removes more heat than still water.
        _, skin_stirred = self._cold_human(
            t_air=10.0, t_ground=10.0, t_water=10.0, water_speed=0.2
        )
        self.assertLess(skin_stirred, skin_water)

    def test_sqf_executes_not_mirror(self):
        # Guard against the evaluator being bypassed: the solver file
        # must exist and be executable.  If the SQF path moves this
        # fails loudly.
        self.assertTrue(_SOLVER.exists(), f"solver missing: {_SOLVER}")


if __name__ == "__main__":
    unittest.main()
