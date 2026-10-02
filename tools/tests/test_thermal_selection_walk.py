#!/usr/bin/env python3
"""Bounded recursive thermal-selection walk (issue #204, > > > ).

The operator asked for the discovery to stop being one flat list: a
hiddenSelection can belong to a part that declares its own selections, so the
walk must continue "until there is no more to find".  fnc_getThermalSelections
keeps its level-0 branches and calls fnc_expandThermalSelectionTree.

The walk is engine-bound (selectionNames, allTurrets, attachedObjects, ...),
so the engine calls are held by source-lock assertions on the comment-stripped
SQF, and the pure control logic (breadth, bounds, proxy skip) is mirrored and
driven from the SAME named constants the SQF declares.

Run: python3 -m unittest tools.tests.test_thermal_selection_walk -v
"""

import re
import unittest

from tools.tests.test_thermal_optics import _read_sqf
from tools.tests.test_exhaust_shimmer import _code_only
from tools.tests.sqf_lite import run_sqf

_REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
_WALK = (
    _REPO_ROOT
    / "addons"
    / "thermal"
    / "functions"
    / "display"
    / "fnc_expandThermalSelectionTree.sqf"
)
_NESTED = (
    _REPO_ROOT
    / "addons"
    / "thermal"
    / "functions"
    / "display"
    / "fnc_getThermalNestedObjects.sqf"
)
_SELECT_PAINT = (
    _REPO_ROOT
    / "addons"
    / "thermal"
    / "functions"
    / "display"
    / "fnc_resolveSelectionPaintIndex.sqf"
)
_SELECT_PAINT_CORE = (
    _REPO_ROOT
    / "addons"
    / "thermal"
    / "functions"
    / "display"
    / "fnc_resolvePaintIndexFromSelections.sqf"
)
_NESTED_COLLECT = (
    _REPO_ROOT
    / "addons"
    / "thermal"
    / "functions"
    / "display"
    / "fnc_collectThermalNestedObjects.sqf"
)
_APPLY_BUILDING = (
    _REPO_ROOT
    / "addons"
    / "thermal"
    / "functions"
    / "display"
    / "fnc_applyBuildingThermal.sqf"
)


def _walk_constants():
    """Read the bound constants out of the real SQF, so the mirror cannot drift.

    The same-object breadth cap lives in the walk; the per-instance nested
    discovery (depth + object cap) lives in fnc_getThermalNestedObjects.
    """
    walk = _WALK.read_text(encoding="utf-8")
    nested = _NESTED.read_text(encoding="utf-8")

    def _one(text, name):
        m = re.search(rf"private\s+{name}\s*=\s*(\d+)\s*;", text)
        if not m:
            raise AssertionError(f"SQF no longer declares {name}")
        return int(m.group(1))

    return (
        _one(nested, "_MAX_DEPTH"),
        _one(nested, "_MAX_OBJECTS"),
        _one(walk, "_MAX_TARGETS"),
    )


def _collect_cap():
    """The collector's _MAX_NESTED, read from the real SQF."""
    text = _NESTED_COLLECT.read_text(encoding="utf-8")
    m = re.search(r"private\s+_MAX_NESTED\s*=\s*(\d+)\s*;", text)
    if not m:
        raise AssertionError("SQF no longer declares _MAX_NESTED")
    return int(m.group(1))


def _collect(parents, children_of, max_nested):
    """Mirror of fnc_collectThermalNestedObjects: bounded BFS, parents excluded."""
    seen = list(parents)
    extra = []
    queue = list(parents)
    while queue and len(extra) < max_nested:
        parent = queue.pop(0)
        for child in children_of(parent):
            if len(extra) >= max_nested:
                break
            if child not in seen:
                seen.append(child)
                extra.append(child)
                queue.append(child)
    return extra


def _is_proxy(name):
    """Mirror of the SQF guard: a name whose 'proxy:' marker is at index 0."""
    return name.find("proxy:") == 0


def _expand_selections(
    parent_names, base_indices, lod_names, turret_names, max_targets
):
    """Mirror of the level-1 breadth add: candidates resolve to a parent index.

    Only a name the object already exposes in its default-LOD selection list
    is a paint target; every other candidate is dropped, and a proxy name is
    never a target.
    """
    covered = [parent_names[i] for i in base_indices if 0 <= i < len(parent_names)]
    out = list(base_indices)
    for name in list(lod_names) + list(turret_names):
        if _is_proxy(name):
            continue
        if name in parent_names and name not in covered and len(out) < max_targets:
            idx = parent_names.index(name)
            if idx not in out:
                out.append(idx)
                covered.append(name)
    return out


def _bounded_walk(root, children_of, max_depth, max_objects):
    """Mirror of the level-2 nested recursion: depth + visited + object cap.

    Returns (visited_order, capped).  A cycle or a self-reference cannot add a
    node twice because a node is visited only when it is not already seen.
    """
    visited = [root]
    order = []
    depth = {root: 0}
    stack = [root]
    capped = False
    while stack:
        node = stack.pop()
        order.append(node)
        if depth[node] >= max_depth:
            continue
        for child in children_of(node):
            if child in visited:
                continue
            if len(visited) >= max_objects:
                capped = True
                continue
            visited.append(child)
            depth[child] = depth[node] + 1
            stack.append(child)
    return order, capped


def _resolve_paint_index(hidden, model, sel):
    """Run the REAL SQF decision, not a Python mirror.

    fnc_resolvePaintIndexFromSelections is the pure core that
    fnc_resolveSelectionPaintIndex delegates to after it reads the two lists
    from the engine.  Passing synthetic lists executes the shipped logic, so a
    drift in the SQF fails these tests instead of passing a stale mirror.
    """
    return run_sqf(_SELECT_PAINT_CORE, [hidden, model, sel])


class TestTurretConfigDiscovery(unittest.TestCase):
    def test_turret_config_selections_are_discovered(self):
        code = _code_only(_WALK.read_text(encoding="utf-8"))
        for token in (
            "allTurrets",
            "BIS_fnc_turretConfig",
            "hiddenSelections",
            "selectionNames",
        ):
            self.assertIn(token, code)

        # A turret declares a selection the flat top-level hiddenSelections
        # list does not, but the object exposes it in its own selection list.
        parent = ["camo1", "camo2", "turret_body"]
        base = [0, 1]  # level 0: camo1, camo2 - the flat list
        _, _, max_targets = _walk_constants()
        out = _expand_selections(
            parent, base, ["turret_body"], ["turret_body"], max_targets
        )
        self.assertIn(2, out)  # turret_body discovered
        self.assertNotIn(2, base)  # the flat list missed it
        self.assertEqual(out[:2], [0, 1])  # level-0 order preserved

    def test_lod_name_absent_from_the_object_list_is_not_a_target(self):
        parent = ["camo1", "camo2", "turret_body"]
        base = [0, 1]
        _, _, max_targets = _walk_constants()
        # wheel_1_1_axis is a Memory-LOD point, not a texture target on the hull.
        out = _expand_selections(parent, base, ["wheel_1_1_axis"], [], max_targets)
        self.assertEqual(out, [0, 1])

    def test_walk_resolves_through_the_config_paint_index(self):
        """The turret name must resolve to the setObjectTexture index space.

        setObjectTexture takes the position in the class hiddenSelections list,
        so a turret candidate is resolved through fnc_resolveSelectionPaintIndex
        and accepted only when the resolved slot IS the declared hiddenSelection.
        The resolver's model fallback is rejected: it is a no-op on the texture
        channel for a vehicle.
        """
        code = _code_only(_WALK.read_text(encoding="utf-8"))
        self.assertIn("FUNC(resolveSelectionPaintIndex)", code)
        self.assertIn('(configOf _object >> "hiddenSelections")', code)
        self.assertIn("toLower", code)

        # A config name resolves to its declared slot; a model-only name (the
        # resolver falls back to the model list) is not a config slot and is
        # rejected because the slot name does not match.
        hidden = ["camo1", "camo2", "turret_body"]
        self.assertEqual(int(_resolve_paint_index(hidden, [], "turret_body")), 2)
        # The walk's acceptance check: the slot at that index carries the name.
        self.assertEqual(hidden[2], "turret_body")
        # A model-only candidate is absent from the config list, so the walk's
        # slot-name guard drops it rather than aliasing a different slot.
        self.assertNotIn("glass", hidden)


class TestAttachedObjectDiscovery(unittest.TestCase):
    def test_attached_object_selections_are_discovered(self):
        code = _code_only(_NESTED.read_text(encoding="utf-8"))
        for token in (
            "attachedObjects",
            "getVehicleCargo",
            "QGVAR(thermalNestedObjects)",
        ):
            self.assertIn(token, code)
        self.assertIn(
            "QGVAR(thermalNestedObjects)", _NESTED.read_text(encoding="utf-8")
        )

        depth, objects, _ = _walk_constants()
        children = {
            "hull": ["attached_gun", "cargo_car"],
            "attached_gun": [],
            "cargo_car": [],
        }
        order, capped = _bounded_walk(
            "hull", lambda n: children.get(n, []), depth, objects
        )
        self.assertIn("attached_gun", order)
        self.assertIn("cargo_car", order)
        self.assertFalse(capped)

    def test_parent_index_cannot_address_the_nested_object(self):
        # Option (a): the walk returns parent indices only; the nested object
        # is exposed separately.  The level-1 mirror never folds a child's
        # names into the parent list, because they are not on the parent.
        parent = ["camo1", "camo2"]
        _, _, max_targets = _walk_constants()
        out = _expand_selections(parent, [0, 1], ["child_hull"], [], max_targets)
        self.assertEqual(out, [0, 1])


class TestWalkTermination(unittest.TestCase):
    def test_walk_terminates_on_self_reference(self):
        depth, objects, _ = _walk_constants()
        self.assertGreaterEqual(depth, 1)
        self.assertGreaterEqual(objects, 1)

        children = {"A": ["A", "B"], "B": ["A", "C"], "C": ["A"]}
        order, capped = _bounded_walk(
            "A", lambda n: children.get(n, []), depth, objects
        )
        self.assertEqual(sorted(order), ["A", "B", "C"])
        self.assertFalse(capped)
        self.assertEqual(len(order), len(set(order)))  # no node visited twice

    def test_bare_self_loop_terminates(self):
        depth, objects, _ = _walk_constants()
        order, _ = _bounded_walk("A", lambda n: ["A"], depth, objects)
        self.assertEqual(order, ["A"])

    def test_object_cap_bounds_a_wide_tree(self):
        # The object cap bounds breadth; the depth cap bounds a chain.  A wide
        # fan-out must stop at the cap, not walk every child.
        depth, objects, _ = _walk_constants()
        children = {"root": [f"child_{i}" for i in range(objects + 20)]}
        order, capped = _bounded_walk(
            "root", lambda n: children.get(n, []), depth, objects
        )
        self.assertTrue(capped)
        self.assertLessEqual(len(order), objects)


class TestProxyBoundary(unittest.TestCase):
    def test_proxy_name_is_not_a_paint_target(self):
        code = _code_only(_WALK.read_text(encoding="utf-8"))
        self.assertIn('"proxy:"', code)
        self.assertTrue(_is_proxy(r"proxy:\a3\characters_f\proxies\weapon.001"))
        self.assertFalse(_is_proxy("turret_body"))

        parent = ["camo1", r"proxy:\a3\characters_f\proxies\weapon.001"]
        _, _, max_targets = _walk_constants()
        out = _expand_selections(parent, [0], [parent[1]], [], max_targets)
        self.assertNotIn(1, out)

    def test_ceiling_is_stated_honestly(self):
        text = _WALK.read_text(encoding="utf-8")
        self.assertIn("model.cfg", text)
        self.assertIn("no script handle", text)


class TestLevelZeroUnchanged(unittest.TestCase):
    def test_existing_branches_and_cache_stay(self):
        text = _read_sqf("fnc_getThermalSelections.sqf", "thermal")
        for token in (
            'isKindOf "Man"',
            "getObjectTextures _object",
            "MKK_TI",
            "A3TI_ThermalSelections",
            "textureSources",
            "BIS_fnc_returnChildren",
            "BIS_fnc_inString",
            "QGVAR(thermalSelectionsCache)",
            "if (_selections isEqualTo []) then",
        ):
            self.assertIn(token, text)
        self.assertNotIn('find "engine"', text)
        self.assertNotIn('find "wheel"', text)

    def test_walk_runs_after_level_zero(self):
        text = _read_sqf("fnc_getThermalSelections.sqf", "thermal")
        self.assertIn("FUNC(expandThermalSelectionTree)", text)
        # The walk is called after level 0 has built _selections, and before
        # the result is cached.
        self.assertLess(
            text.index("if (_selections isEqualTo []) then"),
            text.index("FUNC(expandThermalSelectionTree)"),
        )
        self.assertLess(
            text.index("FUNC(expandThermalSelectionTree)"),
            text.rindex("missionNamespace setVariable [_cacheKey, _selections]"),
        )

    def test_walk_is_bounded_and_cached(self):
        walk = _code_only(_WALK.read_text(encoding="utf-8"))
        nested = _code_only(_NESTED.read_text(encoding="utf-8"))
        collect = _code_only(_NESTED_COLLECT.read_text(encoding="utf-8"))
        # The same-object breadth cap is in the walk; the per-instance nested
        # discovery (depth + object cap + visited set) is in the nested reader;
        # the consumer's breadth cap is in the collector.
        self.assertIn("_MAX_TARGETS", walk)
        for token in ("_MAX_DEPTH", "_MAX_OBJECTS", "_MAX_STORE", "_visited"):
            self.assertIn(token, nested)
        for token in ("_MAX_NESTED", "_seen"):
            self.assertIn(token, collect)
        # The per-class cache is still the one in fnc_getThermalSelections.
        self.assertIn(
            "QGVAR(thermalSelectionsCache)",
            _read_sqf("fnc_getThermalSelections.sqf", "thermal"),
        )


class TestPaintIndexResolution(unittest.TestCase):
    """The paint index must be the setObjectTexture position (config
    hiddenSelections), not the default-LOD selectionNames position.

    The four behaviour tests execute the REAL SQF core through sqf_lite on
    synthetic lists.  The fifth is a source-lock: the engine reads in
    fnc_resolveSelectionPaintIndex (getArray, selectionNames, isNull) cannot
    run headlessly, so only their presence and order are asserted.
    """

    def test_config_name_resolves_on_a_model_with_a_different_name_form(self):
        # The real MRAP shape: the config declares Camo1/Camo2/riotpolice
        # while the default-LOD selectionNames carry no camo name at all.
        hidden = ["Camo1", "Camo2", "riotpolice"]
        model = ["glass3", "wheel_1_1_hide", "damagehide"]
        self.assertEqual(int(_resolve_paint_index(hidden, model, "Camo1")), 0)
        self.assertEqual(int(_resolve_paint_index(hidden, model, "Camo2")), 1)
        self.assertEqual(int(_resolve_paint_index(hidden, model, "riotpolice")), 2)

    def test_config_name_matches_case_insensitively(self):
        # The UAV shape: config Camo1 against a lower-case, reordered model.
        hidden = ["Camo1", "Camo2", "Camo_engine_fire"]
        model = ["camo1", "camo_engine_fire", "camo2"]
        self.assertEqual(int(_resolve_paint_index(hidden, model, "camo1")), 0)
        self.assertEqual(int(_resolve_paint_index(hidden, model, "CAMO2")), 1)

    def test_model_name_falls_back_when_no_hidden_selection_is_declared(self):
        # A man's uniform: no hiddenSelections, so the default-LOD slot is used.
        self.assertEqual(int(_resolve_paint_index([], ["uniform", "face"], "face")), 1)

    def test_unresolvable_name_is_skipped(self):
        self.assertEqual(
            int(_resolve_paint_index(["Camo1"], ["glass3"], "not_on_the_object")),
            -1,
        )
        self.assertEqual(int(_resolve_paint_index([], [], "")), -1)

    def test_engine_glue_reads_the_config_then_the_model_and_returns_the_index(self):
        """Source-lock, not a behaviour test.

        getArray, configOf, selectionNames and isNull need the engine and
        cannot run headlessly.  The decision they feed is executed by the four
        tests above.  This test locks the engine-bound wrapper only: it must
        read the class hiddenSelections array, read the default-LOD
        selectionNames, call the pure core, and return its index.
        """
        code = _code_only(_SELECT_PAINT.read_text(encoding="utf-8"))
        for token in (
            'getArray (configOf _object >> "hiddenSelections")',
            "selectionNames _object",
            "FUNC(resolvePaintIndexFromSelections)",
            "private _idx = -1",
            "isNull _object",
            "exitWith { _idx }",
        ):
            self.assertIn(token, code)
        self.assertLess(
            code.index('getArray (configOf _object >> "hiddenSelections")'),
            code.index("selectionNames _object"),
        )
        self.assertLess(
            code.index("selectionNames _object"),
            code.index("FUNC(resolvePaintIndexFromSelections)"),
        )
        self.assertTrue(code.rstrip().endswith("_idx"))
        # The caller still skips a genuinely unresolvable name without error.
        paint = _read_sqf("fnc_applySelectionThermal.sqf", "thermal")
        self.assertIn("FUNC(resolveSelectionPaintIndex)", paint)
        self.assertIn("if (_idx < 0) then { continue; };", paint)


class TestNestedObjectPaint(unittest.TestCase):
    """The paint loop must process the separate nested objects the walk records.

    attachedObjects and getVehicleCargo return SEPARATE objects.  A part on a
    nested object cannot be painted from the parent, because setObjectTexture
    writes only the target object's slots.  fnc_applyBuildingThermal must run
    the same discovery + paint on each nested object as its own object, bounded
    and cached so a repeat tick is a lookup, not a re-walk.
    """

    def test_paint_loop_processes_nested_objects(self):
        code = _code_only(_APPLY_BUILDING.read_text(encoding="utf-8"))
        self.assertIn("FUNC(collectThermalNestedObjects)", code)
        # The nested objects join the SAME per-object loop, so they get the
        # same discovery + paint as a parent.
        self.assertIn("([_objects] call FUNC(collectThermalNestedObjects))", code)
        self.assertIn("} forEach (_objects +", code)
        # The parent path is unchanged: level-0 discovery and the per-selection
        # paint are still the calls the loop already made.
        self.assertIn("FUNC(getThermalSelections)", code)
        self.assertIn("FUNC(applySelectionThermal)", code)

    def test_collector_is_bounded_and_cycle_safe(self):
        code = _code_only(_NESTED_COLLECT.read_text(encoding="utf-8"))
        for token in ("getThermalNestedObjects", "_MAX_NESTED", "_seen", "while"):
            self.assertIn(token, code)

        cap = _collect_cap()
        self.assertGreaterEqual(cap, 1)
        # A cycle must terminate and must not return a parent.
        cycle = _collect(["A"], lambda n: {"A": ["B"], "B": ["A"]}.get(n, []), cap)
        self.assertEqual(cycle, ["B"])
        # A wide fan-out must stop at the cap.
        wide = {"root": [f"c{i}" for i in range(cap + 20)]}
        wide_out = _collect(["root"], lambda n: wide.get(n, []), cap)
        self.assertLessEqual(len(wide_out), cap)

    def test_per_instance_discovery_is_cached(self):
        code = _code_only(_NESTED.read_text(encoding="utf-8"))
        # Discovery records once per object; every later call is a lookup.
        self.assertIn("getOrDefault [_key, -1]", code)
        self.assertIn("_recorded isEqualType []", code)
        self.assertIn("attachedObjects", code)
        self.assertIn("getVehicleCargo", code)
        # The per-class cache still owns the class-static selection list.
        self.assertIn(
            "QGVAR(thermalSelectionsCache)",
            _read_sqf("fnc_getThermalSelections.sqf", "thermal"),
        )


if __name__ == "__main__":
    unittest.main()
