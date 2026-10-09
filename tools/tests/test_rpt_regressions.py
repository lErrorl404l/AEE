#!/usr/bin/env python3
"""Regression tests for the three live RPT defects (2026-10-08).

RPT: Arma3_x64_2026-10-08_01-15-54.rpt, world Stratis, single player.

Defect 1  fnc_mgrsMapDraw.sqf   `0 elements provided, 2 expected` every draw
          frame: the plan was read back from a local written inside the
          nested cache-rebuild block, so an empty cache left `_plan` nil and
          the following `params` threw.
Defect 2  fnc_wildlifeTick.sqf  the same shape on the sound schedule; it
          threw once on the first tick, then the persisted namespace value
          satisfied the rebuild test.
Defect 3  fnc_symbologyUnitCategory.sqf  `params` declared `_unit` as a
          String, but every caller passes an Object, so `typeOf` threw on
          every call.

Two kinds of test here.  The RUNTIME tests extract the exact source block
from the shipped file and execute it through tools/tests/sqf_lite.py, so the
test runs the real SQF, not a Python mirror.  The CONTRACT tests pin the
source shape where the harness cannot reach the engine (the `params`
destructuring, `typeOf`, the per-frame event wiring).  Both fail on the
defective source and pass on the fixed source.

Run: python3 -m unittest tools.tests.test_rpt_regressions -v
"""

import os
import re
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MGRS_DRAW = ROOT / "addons/optics/functions/hud/fnc_mgrsMapDraw.sqf"
WILDLIFE_TICK = ROOT / "addons/wildlife/functions/fnc_wildlifeTick.sqf"
SYMBOLOGY_UNIT = (
    ROOT / "addons/optics/functions/symbology/fnc_symbologyUnitCategory.sqf"
)


def source(path):
    return path.read_text(encoding="utf-8")


def extract_block(text, start_marker, end_marker):
    """The exact source lines from the line holding start_marker through the
    line holding end_marker, dedented so the harness can parse it."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if start_marker in line]
    ends = [i for i, line in enumerate(lines) if end_marker in line]
    assert starts, f"start marker not found: {start_marker!r}"
    assert ends, f"end marker not found: {end_marker!r}"
    return textwrap.dedent("\n".join(lines[starts[0] : ends[0] + 1]))


def run_program(text, globals_):
    handle, path = tempfile.mkstemp(suffix=".sqf")
    os.close(handle)
    try:
        Path(path).write_text(text, encoding="utf-8")
        return run_sqf(path, [], globals_)
    finally:
        os.unlink(path)


def mission_globals(store):
    return {
        "missionNamespace": store,
        "getVariable": lambda ns, arr: store.get(arr[0], arr[1]),
        "setVariable": lambda ns, arr: store.__setitem__(arr[0], arr[1]),
    }


class TestMgrsMapDrawCacheRead(unittest.TestCase):
    """Defect 1: fnc_mgrsMapDraw.sqf, line 116."""

    def test_runtime_empty_cache_returns_a_wellformed_plan(self):
        # Runs the real cache-read block with a fresh missionNamespace, the
        # first draw frame.  The defect read `_cache select 1` after a nested
        # rebuild, so an empty cache left the plan nil.
        block = extract_block(
            source(MGRS_DRAW),
            "private _key = _rect apply",
            '_plan params ["_segments", "_labels"];',
        )
        program = (
            "private _rect = [100, 100, 300, 300];\n"
            "private _anchor = [0, 0, 0, 0, 0, 0, 0, 0, 0];\n"
            "private _gridInterval = 0;\n"
            f"{block}\n"
            "[_segments, _labels]\n"
        )
        store = {}
        globs = mission_globals(store)
        globs["__FUNC__mgrsGridLines"] = lambda anchor, rect, base: [
            [1, 2],
            [3, 4],
            100,
        ]
        segments, labels = run_program(program, globs)
        self.assertEqual(segments, [1, 2])
        self.assertEqual(labels, [3, 4])

    def test_runtime_reuses_a_valid_cache(self):
        # A populated cache must be read, not rebuilt.  The stub raises if the
        # rebuild path is taken, so this asserts the cache hit.
        block = extract_block(
            source(MGRS_DRAW),
            "private _key = _rect apply",
            '_plan params ["_segments", "_labels"];',
        )
        program = (
            "private _rect = [100, 100, 300, 300];\n"
            "private _anchor = [0, 0, 0, 0, 0, 0, 0, 0, 0];\n"
            "private _gridInterval = 0;\n"
            f"{block}\n"
            "[_segments, _labels]\n"
        )
        key = [10, 10, 30, 30]
        store = {"__QGVAR__mgrsGridCache": [key, ["CACHED_SEG", "CACHED_LBL"]]}

        def never_rebuild(anchor, rect, base):
            raise AssertionError("cache hit expected, rebuild ran")

        globs = mission_globals(store)
        globs["__FUNC__mgrsGridLines"] = never_rebuild
        segments, labels = run_program(program, globs)
        self.assertEqual(segments, "CACHED_SEG")
        self.assertEqual(labels, "CACHED_LBL")

    def test_contract_no_unguarded_plan_select(self):
        # The exact failing form must be gone.
        self.assertIsNone(
            re.search(r"private _plan = _cache select 1;", source(MGRS_DRAW)),
            "fnc_mgrsMapDraw reads _cache select 1 unguarded; a short cache "
            "leaves _plan nil and the following params throws",
        )

    def test_contract_plan_assigned_from_an_if_expression(self):
        # The plan is assigned at one scope level, never from a nested block.
        self.assertRegex(
            source(MGRS_DRAW),
            r"private _plan = if \(",
            "the plan must be assigned at one scope level from an "
            "if-expression so a nested-block rebuild cannot leave it stale",
        )

    def test_contract_plan_guarded_before_params(self):
        text = source(MGRS_DRAW)
        idx = text.find('_plan params ["_segments", "_labels"];')
        self.assertGreater(idx, 0)
        self.assertRegex(
            text[:idx],
            r"if !\(_plan isEqualType \[\]\) then \{ _plan = \[\]; \};",
            "the plan must be defaulted to [] when the cache is malformed, "
            "so a nil can never reach params",
        )


class TestWildlifeScheduleRead(unittest.TestCase):
    """Defect 2: fnc_wildlifeTick.sqf, line 339."""

    def test_runtime_empty_schedule_returns_a_wellformed_schedule(self):
        # Runs the real schedule block with a fresh missionNamespace, the
        # first tick.  The defect read `_schedule select 1` after a nested
        # rebuild, so an empty schedule left the read undefined.
        block = extract_block(
            source(WILDLIFE_TICK),
            "private _hourKey = floor (_now / 3600);",
            "private _emissions = _schedule select 1;",
        )
        program = (
            "private _now = 3600;\n"
            'private _biome = "temperate";\n'
            "private _nearWater = 0;\n"
            "private _vegScore = 0;\n"
            "private _settlement = 0;\n"
            "private _wind = 0;\n"
            "private _rainAmount = 0;\n"
            "private _gain = 0;\n"
            "private _seed = 0;\n"
            f"{block}\n"
            "[_schedule select 0, _schedule select 1, _emissions]\n"
        )
        store = {}
        globs = mission_globals(store)
        globs.update(
            {
                "configFile": "config",
                "isClass": lambda path: False,
                "date": [2026, 10, 8, 12, 0, 0],
                "__EFUNC__lib_readState": lambda key, default, type_: default,
                "__FUNC__getSpeciesMatch": lambda *args: [],
                "__FUNC__soundTick": lambda *args: [],
            }
        )
        hour_key, emissions, read_back = run_program(program, globs)
        self.assertEqual(hour_key, 1)
        self.assertEqual(emissions, [])
        self.assertEqual(read_back, [])
        # The namespace value is a well-formed 3-element schedule.
        self.assertEqual(len(store["__QGVAR__soundSchedule"]), 3)

    def test_contract_schedule_assigned_from_an_if_expression(self):
        self.assertRegex(
            source(WILDLIFE_TICK),
            r"private _schedule = if \(",
            "the schedule must be assigned at one scope level from an "
            "if-expression so a nested-block rebuild cannot leave it stale",
        )


class TestSymbologyUnitCategoryContract(unittest.TestCase):
    """Defect 3: fnc_symbologyUnitCategory.sqf, lines 14 and 18."""

    def test_params_declares_object_not_string(self):
        text = source(SYMBOLOGY_UNIT)
        self.assertIsNone(
            re.search(r'\["_unit", "", \[""\]\]', text),
            "the unit parameter is typed String; the callers pass an Object, "
            "so typeOf throws on every call",
        )
        self.assertRegex(
            text,
            r'\["_unit", objNull, \[objNull\]\]',
            "the unit parameter must be typed Object",
        )

    def test_doc_comment_declares_object(self):
        text = source(SYMBOLOGY_UNIT)
        self.assertRegex(text, r"0: _unit <OBJECT>")
        self.assertIsNone(re.search(r"0: _unit <STRING>", text))


if __name__ == "__main__":
    unittest.main()
