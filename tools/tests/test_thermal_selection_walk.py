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


def _walk_constants():
    """Read the bound constants out of the real SQF, so the mirror cannot drift."""
    text = _WALK.read_text(encoding="utf-8")

    def _one(name):
        m = re.search(rf"private\s+{name}\s*=\s*(\d+)\s*;", text)
        if not m:
            raise AssertionError(f"SQF no longer declares {name}")
        return int(m.group(1))

    return _one("_MAX_DEPTH"), _one("_MAX_OBJECTS"), _one("_MAX_TARGETS")


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
    """Mirror of fnc_resolveSelectionPaintIndex.

    setObjectTexture's numeric index is the class hiddenSelections position.
    Resolve that first (exact, then case-insensitive), then fall back to the
    default-LOD selectionNames position, else -1 (not paintable).
    """
    if sel == "":
        return -1
    if hidden:
        if sel in hidden:
            return hidden.index(sel)
        want = sel.lower()
        for i, name in enumerate(hidden):
            if name.lower() == want:
                return i
    return model.index(sel) if sel in model else -1


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


class TestAttachedObjectDiscovery(unittest.TestCase):
    def test_attached_object_selections_are_discovered(self):
        code = _code_only(_WALK.read_text(encoding="utf-8"))
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
        code = _code_only(_WALK.read_text(encoding="utf-8"))
        for token in ("_MAX_DEPTH", "_MAX_OBJECTS", "_MAX_TARGETS", "_visited"):
            self.assertIn(token, code)
        # The per-class cache is still the one in fnc_getThermalSelections.
        self.assertIn(
            "QGVAR(thermalSelectionsCache)",
            _read_sqf("fnc_getThermalSelections.sqf", "thermal"),
        )


class TestPaintIndexResolution(unittest.TestCase):
    """The paint index must be the setObjectTexture position (config
    hiddenSelections), not the default-LOD selectionNames position."""

    def test_config_name_resolves_on_a_model_with_a_different_name_form(self):
        # The real MRAP shape: the config declares Camo1/Camo2/riotpolice
        # while the default-LOD selectionNames carry no camo name at all.
        hidden = ["Camo1", "Camo2", "riotpolice"]
        model = ["glass3", "wheel_1_1_hide", "damagehide"]
        self.assertEqual(_resolve_paint_index(hidden, model, "Camo1"), 0)
        self.assertEqual(_resolve_paint_index(hidden, model, "Camo2"), 1)
        self.assertEqual(_resolve_paint_index(hidden, model, "riotpolice"), 2)

    def test_config_name_matches_case_insensitively(self):
        # The UAV shape: config Camo1 against a lower-case, reordered model.
        hidden = ["Camo1", "Camo2", "Camo_engine_fire"]
        model = ["camo1", "camo_engine_fire", "camo2"]
        self.assertEqual(_resolve_paint_index(hidden, model, "camo1"), 0)
        self.assertEqual(_resolve_paint_index(hidden, model, "CAMO2"), 1)

    def test_model_name_falls_back_when_no_hidden_selection_is_declared(self):
        # A man's uniform: no hiddenSelections, so the default-LOD slot is used.
        self.assertEqual(_resolve_paint_index([], ["uniform", "face"], "face"), 1)

    def test_unresolvable_name_is_skipped(self):
        self.assertEqual(
            _resolve_paint_index(["Camo1"], ["glass3"], "not_on_the_object"), -1
        )
        self.assertEqual(_resolve_paint_index([], [], ""), -1)

    def test_sqf_resolves_through_the_config_and_keeps_the_skip(self):
        code = _code_only(_SELECT_PAINT.read_text(encoding="utf-8"))
        for token in (
            'getArray (configOf _object >> "hiddenSelections")',
            "toLower",
            "isNotEqualTo []",
            "find _sel",
            "selectionNames _object",
            "private _idx = -1",
            "exitWith { _idx }",
        ):
            self.assertIn(token, code)
        # The caller still skips a genuinely unresolvable name without error.
        paint = _read_sqf("fnc_applySelectionThermal.sqf", "thermal")
        self.assertIn("FUNC(resolveSelectionPaintIndex)", paint)
        self.assertIn("if (_idx < 0) then { continue; };", paint)


if __name__ == "__main__":
    unittest.main()
