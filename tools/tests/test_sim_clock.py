#!/usr/bin/env python3
"""The one real-time simulation clock (Pillar 1).

The framework owns a single authoritative monotonic time source.  The clock
module advances ``aee_core_simTime`` from ``diag_tickTime`` once per frame and
publishes it.  It publishes no shared per-frame delta: a throttled model that
read one would read about ``1/FPS`` and under-integrate (the eye-driver and
thermal-AGC defect class, probe P79).

Every throttled model keeps its own ``_lastSimTime`` and computes
``_dt = aee_core_simTime - _lastSimTime`` once per run.  The engine's
``diag_deltaTime`` (the previous rendered frame) is banned outside the clock
module; that ban and its line-scoped allowlist live in
``test_sim_clock_guard``.

This suite is a source contract: the clock body and its wiring are pinned from
the real SQF, and the monotonic publish is modelled over a non-decreasing tick
series (``diag_tickTime`` never decreases, engine-commands-and-features.md:424).
"""

from __future__ import annotations

import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLOCK = os.path.join(ROOT, "addons", "core", "functions", "fnc_updateSimClock.sqf")
CORE_PREP = os.path.join(ROOT, "addons", "core", "XEH_PREP.hpp")
CORE_POSTINIT = os.path.join(ROOT, "addons", "core", "XEH_postInit.sqf")

# Every throttled model migrated onto the clock in this change set.  Each reads
# the published clock and keeps its own last-sample variable (a new
# _lastSimTime, or the model's existing last-tick variable).
MIGRATED = (
    "addons/thermal/functions/display/fnc_applyWeaponBarrelHeat.sqf",
    "addons/thermal/functions/display/fnc_applyEngineThermal.sqf",
    "addons/nightvision/functions/fnc_applyNVGTubeModel.sqf",
    "addons/mobility/functions/fnc_applyRollover.sqf",
    "addons/thermal/functions/display/fnc_applyThermalVision.sqf",
    "addons/optics/functions/eye/fnc_updateEyeAdaptation.sqf",
    "addons/thermal/functions/solver/fnc_updateThermalAGC.sqf",
)

# The per-model last-sample store each migrated file must keep.
LAST_SAMPLE = {
    "addons/thermal/functions/display/fnc_applyWeaponBarrelHeat.sqf": "barrelLastSimTime",
    "addons/thermal/functions/display/fnc_applyEngineThermal.sqf": "engThermLastSimTime",
    "addons/nightvision/functions/fnc_applyNVGTubeModel.sqf": "nvgLastSimTime",
    "addons/mobility/functions/fnc_applyRollover.sqf": "rolloverLastSimTime",
    "addons/thermal/functions/display/fnc_applyThermalVision.sqf": "thermalVisLastSimTime",
    "addons/optics/functions/eye/fnc_updateEyeAdaptation.sqf": "eyeLastTick",
    "addons/thermal/functions/solver/fnc_updateThermalAGC.sqf": "agcLastT",
}


def code_only(text: str) -> str:
    """Blank out line and block comments, preserving structure."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class TestClockModule(unittest.TestCase):
    """The clock publishes the monotonic time from diag_tickTime."""

    def setUp(self):
        self.raw = read(CLOCK)
        self.code = code_only(self.raw)

    def test_reads_the_monotonic_engine_clock(self):
        self.assertIn("private _now = diag_tickTime;", self.code)

    def test_publishes_aee_core_sim_time_every_tick(self):
        # One assignment per tick, from the monotonic sample.
        self.assertIn("missionNamespace setVariable [QGVAR(simTime), _now];", self.code)
        self.assertEqual(
            len(re.findall(r"setVariable \[QGVAR\(simTime\)", self.code)),
            1,
            "the clock must publish simTime exactly once",
        )

    def test_publishes_no_per_frame_delta(self):
        # A shared per-frame delta is the exact defect.  The clock must not
        # publish one and must not read diag_deltaTime.
        self.assertNotIn("diag_deltaTime", self.code)
        self.assertNotIn("simDt", self.code)


class TestClockWiring(unittest.TestCase):
    """The clock is prepped and registered first in the frame."""

    def test_clock_is_prepped(self):
        self.assertIn("PREP(updateSimClock);", read(CORE_PREP))

    def test_clock_handler_runs_before_every_other_handler(self):
        postinit = read(CORE_POSTINIT)
        clock_at = postinit.index(
            "[FUNC(updateSimClock), 0] call CBA_fnc_addPerFrameHandler;"
        )
        # The environment tick and the model handlers register after the clock,
        # so the published clock is current when any model reads it this frame.
        for later in (
            "[] call FUNC(init);",
            "[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;",
        ):
            self.assertLess(clock_at, postinit.index(later), later)


class TestMigratedModels(unittest.TestCase):
    """Every throttled model reads the clock, not a frame delta."""

    def test_every_migrated_model_reads_the_clock(self):
        for rel in MIGRATED:
            code = code_only(read(os.path.join(ROOT, rel)))
            self.assertIn(
                "EGVAR(core,simTime)", code, f"{rel} does not read aee_core_simTime"
            )

    def test_no_migrated_model_reads_a_frame_delta(self):
        for rel in MIGRATED:
            code = code_only(read(os.path.join(ROOT, rel)))
            self.assertNotIn(
                "diag_deltaTime", code, f"{rel} still reads diag_deltaTime"
            )

    def test_every_migrated_model_keeps_its_own_last_sim_time(self):
        for rel in MIGRATED:
            code = code_only(read(os.path.join(ROOT, rel)))
            marker = LAST_SAMPLE[rel]
            self.assertIn(
                marker, code, f"{rel} does not keep its own last-sample store"
            )


class TestMonotonicPublish(unittest.TestCase):
    """The published clock is monotonic over a non-decreasing tick series."""

    def test_publish_is_monotonic(self):
        # The body binds simTime to the diag_tickTime sample.  diag_tickTime is
        # real monotonic seconds, so the published series never decreases.
        ticks = [0.0, 0.0, 0.0125, 0.0125, 0.025, 1.5, 1.5001, 900.0]
        published = [t for t in ticks]  # body: simTime := diag_tickTime
        self.assertEqual(
            published,
            sorted(published),
            "a non-decreasing tick series must publish a non-decreasing clock",
        )

    def test_the_binding_is_the_monotonic_sample(self):
        # Guard the simulation above from drifting off the real SQF: the only
        # simTime assignment must bind the _now sample, and _now must be the
        # monotonic engine read.
        code = code_only(read(CLOCK))
        self.assertRegex(
            code,
            r"private _now = diag_tickTime;\s*\n\s*missionNamespace setVariable "
            r"\[QGVAR\(simTime\), _now\];",
        )


if __name__ == "__main__":
    sys.exit(unittest.main())
