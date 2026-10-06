#!/usr/bin/env python3
"""AI and wildlife kernel soak tests under sustained load.

The pure kernels run from their real SQF through tools/tests/sqf_lite.py.  The
owner loops run inside one run_sqf call each, because the harness interprets
SQF in Python and a Python-to-SQF call for every iteration is far too slow.
One run_sqf call binds the real kernel files as callables and drives the whole
loop in a single interpreter pass.

Run: python3 -m unittest tools.tests.test_ai_wildlife_soak -v
"""

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import Lambda, Params, load_sqf, run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AI = ROOT / "addons" / "ai"
AI_FUNCS = AI / "functions"
WILDLIFE = ROOT / "addons" / "wildlife"
WILDLIFE_FUNCS = WILDLIFE / "functions"

DECAY = AI_FUNCS / "fnc_stimulusDecay.sqf"
KEY = AI_FUNCS / "fnc_disturbanceKey.sqf"
APPLY = AI_FUNCS / "fnc_disturbanceApply.sqf"
SAMPLE = AI_FUNCS / "fnc_disturbanceSample.sqf"
PRUNE = AI_FUNCS / "fnc_disturbancePrune.sqf"

SPAWN_BUDGET = WILDLIFE_FUNCS / "fnc_spawnBudget.sqf"
NEEDS_TICK = WILDLIFE_FUNCS / "fnc_needsTick.sqf"
SPECIES_FOR_BIOME = WILDLIFE_FUNCS / "fnc_speciesForBiome.sqf"
SPECIES_MATCH = WILDLIFE_FUNCS / "fnc_getSpeciesMatch.sqf"
PLAY_ONE_SHOT = WILDLIFE_FUNCS / "fnc_playOneShot.sqf"
SPECIES_TABLE = WILDLIFE / "data" / "species_table.sqf"

AI_HEADER = AI / "script_component.hpp"
WILDLIFE_HEADER = WILDLIFE / "script_component.hpp"


def _define(path, name):
    """The numeric value of a #define in a component header."""
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^#define\s+{name}\s+([0-9]+(?:\.[0-9]+)?)", text, re.M)
    assert match, f"{name} is not defined in {path.name}"
    return float(match.group(1))


# The engine constants the soak asserts against.  The harness strips the
# preprocessor header, so the values are read here and passed to the kernels.
CELL_SIZE = int(_define(AI_HEADER, "AI_CELL_SIZE"))
CELL_CAP = int(_define(AI_HEADER, "AI_CELL_CAP"))
CELL_HORIZON = int(_define(AI_HEADER, "AI_CELL_HORIZON"))
STIMULUS_HALF_LIFE = int(_define(AI_HEADER, "AI_STIMULUS_HALF_LIFE"))
SOUND_INSTANCE_CAP = int(_define(WILDLIFE_HEADER, "WILDLIFE_SOUND_INSTANCE_CAP"))


def _kernel(path):
    """A callable Lambda built from the real kernel file, params pre-bound."""
    stmts = load_sqf(path)
    params = []
    body = stmts
    if stmts and isinstance(stmts[0], Params):
        params = [name for name, _default in stmts[0].specs]
        body = stmts[1:]
    return Lambda(params, body, {})


def _run_program(text, globals_):
    """Run one SQF program kept in a temporary file."""
    handle, path = tempfile.mkstemp(suffix=".sqf")
    os.close(handle)
    try:
        Path(path).write_text(text, encoding="utf-8")
        return run_sqf(path, [], globals_=globals_)
    finally:
        os.unlink(path)


def _owner_globals(prune_enabled=True):
    """The real kernels as callables.  The prune can be removed for a control."""
    globals_ = {
        "__FUNC__disturbanceKey": _kernel(KEY),
        "__FUNC__disturbanceApply": _kernel(APPLY),
        "__FUNC__disturbanceSample": _kernel(SAMPLE),
        "__FUNC__stimulusDecay": _kernel(DECAY),
        "AI_STIMULUS_HALF_LIFE": STIMULUS_HALF_LIFE,
    }
    if prune_enabled:
        globals_["__FUNC__disturbancePrune"] = _kernel(PRUNE)
    else:
        # The control that removes the bound.  The prune is the identity.
        globals_["__FUNC__disturbancePrune"] = lambda cells, _now, _cap, _hor: cells
    return globals_


# The field-bound owner loop.  The harness cost is linear in the field length,
# so the literal 100000 stimulus long run takes about 900 s and cannot fit the
# 5 s suite budget.  The reduction keeps the owner-loop semantics and the 600 s
# virtual time, and keeps enough distinct cells and enough applies to saturate
# AI_CELL_CAP and to age cells past AI_CELL_HORIZON.  A short old batch runs
# over the first 480 s and a recent batch runs over the last 120 s.  The
# recent batch exceeds the cap, so the prune must cap it every iteration.
OLD_STIMULI = 8
RECENT_STIMULI = 260
FIELD_APPLIES = OLD_STIMULI + RECENT_STIMULI

_FIELD_OWNER = f"""
private _field = [];
private _maxCount = 0;
for "_i" from 0 to {FIELD_APPLIES - 1} do {{
    private _key = [[(_i * {CELL_SIZE}), 0, 0], {CELL_SIZE}] call FUNC(disturbanceKey);
    private _t = 0;
    if (_i < {OLD_STIMULI}) then {{
        _t = _i * (480 / {OLD_STIMULI});
    }} else {{
        _t = 480 + ((_i - {OLD_STIMULI}) * (120 / {RECENT_STIMULI}));
    }};
    _field = [_field, _key, 0.5, _t] call FUNC(disturbanceApply);
    _field = [_field, _t, {CELL_CAP}, {CELL_HORIZON}] call FUNC(disturbancePrune);
    private _sample = [_field, _key, _t, {STIMULUS_HALF_LIFE}] call FUNC(disturbanceSample);
    _maxCount = _maxCount max (count _field);
}};
[_field, _maxCount]
"""

_FIELD_RESULT = None


def field_bound_run(prune_enabled=True):
    """Run the field-bound owner loop once.  The capped run is cached."""
    global _FIELD_RESULT
    if prune_enabled and _FIELD_RESULT is not None:
        return _FIELD_RESULT
    result = _run_program(_FIELD_OWNER, _owner_globals(prune_enabled))
    if prune_enabled:
        _FIELD_RESULT = result
    return result


class TestFieldBoundSoak(unittest.TestCase):
    """The field bound holds over the long owner run."""

    def test_the_field_never_exceeds_the_cap(self):
        field, max_count = field_bound_run()
        self.assertLessEqual(max_count, CELL_CAP)
        self.assertLessEqual(len(field), CELL_CAP)

    def test_no_kept_cell_is_older_than_the_horizon(self):
        field, _max_count = field_bound_run()
        now = max(entry[2] for entry in field)
        for entry in field:
            self.assertLessEqual(now - entry[2], CELL_HORIZON)

    def test_the_aged_cells_are_dropped(self):
        field, _max_count = field_bound_run()
        kept = {(round(entry[0][0]), round(entry[0][1])) for entry in field}
        # Every old cell is older than the horizon at the final time, so the
        # age prune drops it.  Build each old key with the real key kernel and
        # assert the full key is absent, not just its x index.
        for cell in range(OLD_STIMULI):
            old_key = run_sqf(KEY, [[cell * CELL_SIZE, 0, 0], CELL_SIZE])
            self.assertNotIn((round(old_key[0]), round(old_key[1])), kept)

    def test_the_bound_depends_on_the_prune(self):
        # The apply kernel alone does not bound the field.  Applying one more
        # distinct cell than the cap keeps every cell, so the field exceeds the
        # cap.  The prune is what enforces the bound.
        owner = f"""
private _field = [];
for "_i" from 0 to {CELL_CAP} do {{
    private _key = [[(_i * {CELL_SIZE}), 0, 0], {CELL_SIZE}] call FUNC(disturbanceKey);
    _field = [_field, _key, 0.5, 500] call FUNC(disturbanceApply);
}};
_field
"""
        globals_ = {
            "__FUNC__disturbanceKey": _kernel(KEY),
            "__FUNC__disturbanceApply": _kernel(APPLY),
        }
        field = _run_program(owner, globals_)
        self.assertGreater(len(field), CELL_CAP)


class TestFieldBoundIsTheWalkBound(unittest.TestCase):
    """The prune holds the field at the cap, so the per-apply walk is bounded."""

    def test_more_applies_than_the_cap_yet_the_field_stays_at_the_cap(self):
        field, max_count = field_bound_run()
        self.assertGreater(FIELD_APPLIES, CELL_CAP)
        self.assertEqual(max_count, CELL_CAP)
        self.assertEqual(len(field), CELL_CAP)

    def test_the_cap_bounds_the_per_apply_walk(self):
        # The last apply walks the field the prune returned.  The walk is the
        # field length, and the field length never rises above the cap.
        _field, max_count = field_bound_run()
        self.assertLessEqual(max_count, CELL_CAP)


class TestFieldDecaySoak(unittest.TestCase):
    """A stimulus decays and never rises with age."""

    @staticmethod
    def decay(magnitude, age, half_life=STIMULUS_HALF_LIFE):
        return run_sqf(DECAY, [magnitude, age, half_life])

    def test_the_magnitude_never_rises_with_age(self):
        ages = [0, 1, 5, 10, 45, 90, 180, 600, 1000]
        values = [self.decay(1.0, age) for age in ages]
        for earlier, later in zip(values, values[1:]):
            self.assertGreaterEqual(earlier, later)

    def test_a_weak_stimulus_decays_to_zero(self):
        self.assertAlmostEqual(self.decay(0.5, 10 * 1000), 0.0)

    def test_a_negative_age_clamps_to_one(self):
        self.assertAlmostEqual(self.decay(0.5, -100), 1.0)

    def test_the_decay_stays_inside_zero_and_one(self):
        for age in (0, 45, 1000, 100000):
            value = self.decay(1.0, age)
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)


class TestFieldSaturationSoak(unittest.TestCase):
    """One cell absorbs 100000 stimuli and stays a single cell at full."""

    def test_one_cell_absorbs_a_hundred_thousand_stimuli(self):
        owner = f"""
private _field = [];
private _key = [[0, 0, 0], {CELL_SIZE}] call FUNC(disturbanceKey);
for "_i" from 0 to 99999 do {{
    _field = [_field, _key, 1, _i] call FUNC(disturbanceApply);
}};
_field
"""
        globals_ = {
            "__FUNC__disturbanceKey": _kernel(KEY),
            "__FUNC__disturbanceApply": _kernel(APPLY),
        }
        field = _run_program(owner, globals_)
        self.assertEqual(len(field), 1)
        self.assertEqual(field[0][1], 1.0)


class TestSpawnBudgetAtTheCap(unittest.TestCase):
    """The spawn budget at and above the cap."""

    @staticmethod
    def budget(distance, live_count, cap=16, spawn_radius=350, despawn_radius=600):
        return run_sqf(
            SPAWN_BUDGET,
            [distance, spawn_radius, despawn_radius, live_count, cap],
        )

    def test_at_the_cap_allowed_is_zero_and_spawn_is_false(self):
        allowed, should_spawn, _should_despawn = self.budget(100, 16, cap=16)
        self.assertEqual(allowed, 0)
        self.assertFalse(should_spawn)

    def test_allowed_never_goes_negative_above_the_cap(self):
        for live_count in (17, 20, 40, 1000):
            with self.subTest(live_count=live_count):
                allowed, should_spawn, _should_despawn = self.budget(
                    100, live_count, cap=16
                )
                self.assertEqual(allowed, 0)
                self.assertFalse(should_spawn)

    def test_the_live_cap_is_the_engine_animal_cap(self):
        allowed, should_spawn, _should_despawn = self.budget(100, 15, cap=16)
        self.assertEqual(allowed, 1)
        self.assertTrue(should_spawn)


class TestSoundInstanceCapInvariant(unittest.TestCase):
    """The playOneShot source keeps the instance cap at 8 and expires by time."""

    def test_the_instance_cap_constant_is_eight(self):
        self.assertEqual(SOUND_INSTANCE_CAP, 8)

    def test_the_kernel_refuses_at_the_cap(self):
        text = PLAY_ONE_SHOT.read_text(encoding="utf-8")
        self.assertIn("WILDLIFE_SOUND_INSTANCE_CAP", text)
        self.assertRegex(text, r"count\s+_live\)\s*>=\s*WILDLIFE_SOUND_INSTANCE_CAP")

    def test_the_kernel_expires_instances_by_time(self):
        text = PLAY_ONE_SHOT.read_text(encoding="utf-8")
        self.assertIn("_expiry > _now", text)
        self.assertIn("_now + 3", text)


class TestNeedsSaturationSoak(unittest.TestCase):
    """The needs clamp at one over a long run and the goal stays in range."""

    def test_needs_clamp_and_the_goal_stays_in_range(self):
        owner = """
private _hunger = 0;
private _thirst = 0;
private _goal = 0;
private _bad = 0;
for "_i" from 0 to 9999 do {
    private _result = [_hunger, _thirst, 1, 0.02, 0.03] call FUNC(needsTick);
    _hunger = _result select 0;
    _thirst = _result select 1;
    _goal = _result select 2;
    if ((_goal < 0) || (_goal > 2)) then { _bad = _bad + 1; };
};
[_hunger, _thirst, _goal, _bad]
"""
        globals_ = {"__FUNC__needsTick": _kernel(NEEDS_TICK)}
        hunger, thirst, goal, bad = _run_program(owner, globals_)
        self.assertEqual(hunger, 1.0)
        self.assertEqual(thirst, 1.0)
        self.assertIn(goal, (0, 1, 2))
        self.assertEqual(bad, 0)


def load_species_table():
    return run_sqf(SPECIES_TABLE, [])


def _kernel(path):
    """A callable Lambda built from a real kernel file, params pre-bound."""
    stmts = load_sqf(path)
    params, body = [], stmts
    if stmts and isinstance(stmts[0], Params):
        params = [name for name, _default in stmts[0].specs]
        body = stmts[1:]
    return Lambda(params, body, {})


def species_for_biome(biome, is_night, water_frac, veg_score, seed, table):
    return run_sqf(
        SPECIES_FOR_BIOME,
        [biome, is_night, water_frac, veg_score, seed, table],
        globals_={
            "__FUNC__getSpeciesMatch": _kernel(SPECIES_MATCH),
            "__FUNC__speciesDeprecation": lambda: None,
        },
    )


class TestSpeciesForBiomeDeterminism(unittest.TestCase):
    """The same inputs give the same mix and a seed step moves it."""

    @classmethod
    def setUpClass(cls):
        cls.TABLE = load_species_table()

    def _mix(self, seed):
        return species_for_biome("Cfb", False, 0.0, 0.8, seed, self.TABLE)

    def test_same_biome_time_water_vegetation_and_seed_give_the_same_mix(self):
        first = self._mix(7)
        second = self._mix(7)
        self.assertEqual(first, second)
        self.assertGreater(len(first), 0)

    def test_a_one_step_seed_change_moves_the_mix(self):
        self.assertNotEqual(self._mix(7), self._mix(8))


if __name__ == "__main__":
    unittest.main()
