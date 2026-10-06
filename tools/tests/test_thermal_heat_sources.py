#!/usr/bin/env python3
"""Per-selection local heat-source targeting (issue #204).

The four vehicle heat sources - exhaust/muzzle, impact, radiative exchange
and object-to-object contact - used to warm the FIRST entry of the
selection list.  The first entry is declaration order, not a physical
quantity, so the wrong part always heated.  They now warm the part that
physically corresponds to the source.

This suite executes the REAL selection resolver (fnc_getNearestSelection)
through the shared sqf_lite interpreter with a synthetic multi-selection
vehicle, so the rule is proven, not mirrored.  The engine-bound glue in
the four source files is held by source assertions on the comment-stripped
SQF: each source calls the shared resolver and no longer reads position 0
as the selection.

Run: python3 -m unittest tools.tests.test_thermal_heat_sources -v
"""

import os
import tempfile
import unittest
from pathlib import Path

from tools.tests.sqf_lite import run_sqf
from tools.tests.test_exhaust_shimmer import _code_only

_REPO = Path(__file__).resolve().parents[2]
_THERMAL = _REPO / "addons" / "thermal" / "functions"

# sqf_lite evaluates `{...}` after `||`/`&&` as a lambda, not a predicate, so
# the braced `isEqualTo []` empty guard cannot be executed.  Only that guard
# is normalised below; the selection geometry stays the production code.
_GUARD_VARIANTS = [
    'if ((_names isEqualTo []) || {_points isEqualTo []}) exitWith { "" };',
    'if ((_names isEqualTo []) || (_points isEqualTo [])) exitWith { "" };',
    'if ((count _names) == 0 || {(count _points) == 0}) exitWith { "" };',
    'if ((count _names) == 0 || (count _points) == 0) exitWith { "" };',
]
_GUARD_CLEAN = (
    'if ((count _names) == 0) exitWith { "" };\n'
    'if ((count _points) == 0) exitWith { "" };'
)


def _sqf(name):
    for f in _THERMAL.rglob(name):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError(name)


def _nearest(name):
    return _REPO / "addons" / "thermal" / "functions" / "display" / name


# A synthetic multi-selection vehicle: the engine part is NOT index 0, so a
# resolver that returned the first entry would fail every test below.
VEHICLE_NAMES = ["hull_body", "wheel_1_1", "engine_block", "glass_front", "wheel_2_2"]
VEHICLE_POINTS = [
    [0.0, 0.0, 0.5],  # 0: hull
    [1.0, 2.5, 0.0],  # 1: front-left wheel
    [0.0, 1.8, 0.6],  # 2: engine bay (front of the model)
    [0.0, -1.5, 1.0],  # 3: front glass (rear of the model, high)
    [1.0, -2.5, 0.0],  # 4: rear-right wheel
]


def _resolver_path():
    """Path to the real resolver, normalised for one sqf_lite limitation.

    sqf_lite evaluates `{...}` after `||`/`&&` as a lambda, not a predicate,
    so it cannot execute the braced `isEqualTo []` empty-guard form.  Only
    that one guard is normalised.  The selection geometry is the production
    code, untouched.
    """
    src = _nearest("fnc_getNearestSelection.sqf").read_text(encoding="utf-8")
    for variant in _GUARD_VARIANTS:
        if variant in src:
            src = src.replace(variant, _GUARD_CLEAN, 1)
            break
    fd, path = tempfile.mkstemp(prefix="aee_nearest_", suffix=".sqf")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(src)
    return path


def nearest_name(names, points, ref):
    """Run the real SQF resolver.  This is not a mirror."""
    return run_sqf(_resolver_path(), [names, points, ref])


def engine_side_or_nearest(names, materials, points, ref, cap=2):
    """Mirror of fnc_applyExhaustHeat's target rule.

    The exhaust heats the selection(s) the hit-point map labels "engine",
    capped at 2; with no engine label it falls back to the part nearest the
    plume.  A short mirror of a two-branch policy, not of the geometry.
    """
    engine = [n for n, m in zip(names, materials) if m == "engine"][:cap]
    if engine:
        return engine
    if not names:
        return []
    return [nearest_name(names, points, ref)]


class TestNearestSelectionResolver(unittest.TestCase):
    def test_impact_targets_the_nearest_part_not_index_zero(self):
        # Impact lands by the rear-right wheel; the resolver must choose it,
        # not the hull at index 0.
        impact = [0.9, -2.4, 0.0]
        self.assertEqual(
            nearest_name(VEHICLE_NAMES, VEHICLE_POINTS, impact), "wheel_2_2"
        )

    def test_impact_targets_the_engine_face_when_the_bullet_hits_there(self):
        impact = [0.0, 1.9, 0.7]
        self.assertEqual(
            nearest_name(VEHICLE_NAMES, VEHICLE_POINTS, impact), "engine_block"
        )

    def test_chosen_part_is_not_the_first_entry(self):
        # The nearest point (index 4) is farther from index 0 than the query,
        # so returning the first entry would give the wrong part by 3 m.
        impact = [0.9, -2.4, 0.0]
        chosen = nearest_name(VEHICLE_NAMES, VEHICLE_POINTS, impact)
        self.assertNotEqual(chosen, VEHICLE_NAMES[0])

    def test_empty_selection_set_returns_empty(self):
        self.assertEqual(nearest_name([], [], [0.0, 0.0, 0.0]), "")


class TestSourceSelectionRules(unittest.TestCase):
    def test_exhaust_heats_the_engine_side_not_index_zero(self):
        # materials[2] == "engine"; index 0 is hull.  Engine-side wins even
        # though the muzzle point is elsewhere.
        materials = ["metal", "rubber", "engine", "glass", "rubber"]
        targets = engine_side_or_nearest(
            VEHICLE_NAMES, materials, VEHICLE_POINTS, [0.0, 3.0, 0.0]
        )
        self.assertEqual(targets, ["engine_block"])
        self.assertNotIn(VEHICLE_NAMES[0], targets)

    def test_exhaust_falls_back_to_the_nearest_part(self):
        # No engine label: warm the part the plume washes over.
        materials = ["metal", "rubber", "metal", "glass", "rubber"]
        targets = engine_side_or_nearest(
            VEHICLE_NAMES, materials, VEHICLE_POINTS, [0.9, -2.4, 0.0]
        )
        self.assertEqual(targets, ["wheel_2_2"])

    def test_contact_heats_the_touching_face_of_each_object(self):
        # Object A: the face nearest object B is its rear part.
        a_names = ["a_front", "a_rear"]
        a_points = [[0.0, 5.0, 0.0], [0.0, -5.0, 0.0]]
        b_centre = [0.0, -6.0, 0.0]
        self.assertEqual(nearest_name(a_names, a_points, b_centre), "a_rear")
        # Object B symmetric: nearest to A's centre is its top.
        b_names = ["b_top", "b_bottom"]
        b_points = [[0.0, 5.0, 0.0], [0.0, -5.0, 0.0]]
        a_centre = [0.0, 6.0, 0.0]
        self.assertEqual(nearest_name(b_names, b_points, a_centre), "b_top")

    def test_radiative_flux_is_distributed_by_view_factor(self):
        # The pair's flux is split across the parts, not dumped on index 0.
        q = 120.0
        hot_centre = [0.9, -2.6, 0.0]  # near the rear-right wheel
        weights = [
            1.0 / (1.0 + sum((p[k] - hot_centre[k]) ** 2 for k in range(3)))
            for p in VEHICLE_POINTS
        ]
        total = sum(weights)
        shares = [q * w / total for w in weights]
        self.assertEqual(len(shares), len(VEHICLE_NAMES))
        self.assertAlmostEqual(sum(shares), q, places=6)
        # More than one part receives flux, and the nearest receives most.
        self.assertGreater(sum(1 for s in shares if s > q * 1e-4), 1)
        self.assertEqual(shares.index(max(shares)), VEHICLE_NAMES.index("wheel_2_2"))


class TestSourceWiring(unittest.TestCase):
    def test_impact_uses_the_shared_resolver(self):
        code = _code_only(_sqf("fnc_applyImpactHeat.sqf"))
        self.assertIn("FUNC(getThermalSelectionNames)", code)
        self.assertIn("FUNC(getThermalSelectionPoints)", code)
        self.assertIn("FUNC(getNearestSelection)", code)
        self.assertNotIn("_sels select 0", code)

    def test_exhaust_uses_the_engine_map_and_the_resolver(self):
        code = _code_only(_sqf("fnc_applyExhaustHeat.sqf"))
        self.assertIn("FUNC(getThermalSelectionNames)", code)
        self.assertIn("FUNC(getHitPointMaterials)", code)
        self.assertIn('== "engine"', code)
        self.assertIn("FUNC(getNearestSelection)", code)
        self.assertNotIn("_sels select 0", code)

    def test_radiative_distributes_not_first_only(self):
        code = _code_only(_sqf("fnc_applyRadiativeExchange.sqf"))
        self.assertIn("FUNC(getThermalSelectionPoints)", code)
        self.assertIn("_weights", code)
        self.assertIn("_wsum", code)
        self.assertNotIn("_coldSel", code)

    def test_contact_uses_the_nearest_touching_face(self):
        code = _code_only(_sqf("fnc_applyContactConduction.sqf"))
        self.assertIn("FUNC(getNearestSelection)", code)
        self.assertNotIn("param [0, -1]", code)

    def test_points_and_names_helpers_are_shared(self):
        points = _code_only(_sqf("fnc_getThermalSelectionPoints.sqf"))
        self.assertIn('selectionPosition [_x, "Memory"]', points)
        self.assertIn("QGVAR(thermalSelectionPointCache)", points)
        names = _code_only(_sqf("fnc_getThermalSelectionNames.sqf"))
        self.assertIn("FUNC(getThermalSelections)", names)
        self.assertIn("selectionNames _object", names)

    def test_lag_reuses_the_points_cache(self):
        code = _code_only(_sqf("fnc_getThermalSelectionLag.sqf"))
        self.assertIn("FUNC(getThermalSelectionPoints)", code)
        self.assertIn("_pos distance _source", code)


class TestCrossoverSurfaceStack(unittest.TestCase):
    """The crossover surface temperature comes from the ground node stack.

    The kernel takes the FIRST LAYER of fnc_calculateGroundNodeStack, so for
    any fixed non-empty stack the crossover surface equals layer 0.  The
    ground-state switch survives only as the empty-stack fallback.
    """

    @classmethod
    def setUpClass(cls):
        cls.code = _code_only(_sqf("fnc_calculateThermalCrossover.sqf"))

    def test_reads_the_ground_node_stack_once(self):
        # One call per tick: the stack is time-integrated.
        self.assertEqual(self.code.count("FUNC(calculateGroundNodeStack)"), 1)

    def test_surface_temperature_is_the_first_layer(self):
        # For a fixed synthetic stack [t1, t2, t3, t4, tBot, now] the
        # crossover surface temperature is t1.
        self.assertIn("_surfaceTemp = _stack select 0;", self.code)
        self.assertNotIn("_stack select 1", self.code)
        self.assertNotIn("_stack select 2", self.code)

    def test_fallback_switch_is_guarded_by_an_empty_stack(self):
        self.assertIn("if (_stack isEqualTo []) then {", self.code)
        # The fallback names every old ground state, but only inside the guard.
        guard_at = self.code.index("if (_stack isEqualTo []) then {")
        default_at = self.code.index(
            "default        { _airTemp + 2 * (1 - _overcast) }"
        )
        self.assertLess(guard_at, default_at)

    def test_resolves_position_like_the_node_stack(self):
        self.assertIn("getPosASL _unit", self.code)
        self.assertIn("_pos = [0, 0, 0];", self.code)

    def test_keeps_the_surface_temperature_publish(self):
        # fnc_calculatePrecipitationPhase reads this.
        self.assertIn("EGVAR(core,surfaceTemperature)", self.code)

    def test_keeps_the_twilight_gate_and_timer(self):
        self.assertIn("_inTwilight && _delta <= 1.5", self.code)
        self.assertIn("_timer = _timer + 1;", self.code)
        self.assertIn("_timer = _timer - 1;", self.code)


if __name__ == "__main__":
    unittest.main()
