#!/usr/bin/env python3
"""Component anchor registry (issue #128).

The engine exposes named selections and hit points as fixed anchors (ADR-001).
The registry maps a component ROLE to the model selections that name that part,
so per-component physics can drive the part by role.

fnc_classifyComponentRole is PURE (no engine call), but the shared sqf_lite
interpreter does not implement the `find` command it uses, so the classifier is
MIRRORED here in Python and driven from the same keyword order the SQF declares.
The engine-glue functions (getComponentAnchors, applyComponentMaterial) and the
wired consumer (getThermalSelectionLag) are held by source assertions on the
comment-stripped SQF, the pattern the other thermal suites use.

Run: python3 -m unittest tools.tests.test_component_anchors -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
THERMAL = REPO / "addons" / "thermal" / "functions"


def _read(name: str) -> str:
    for f in THERMAL.rglob(name):
        return f.read_text(encoding="utf-8")
    raise FileNotFoundError(name)


def _code_only(text: str) -> str:
    """Strip // comments and /* */ blocks so source assertions read code only."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    lines = []
    for line in text.splitlines():
        idx = line.find("//")
        if idx >= 0:
            line = line[:idx]
        lines.append(line)
    return "\n".join(lines)


# ─── Mirror of fnc_classifyComponentRole (keyword order is the contract) ──────
# Each entry: (role, keywords).  A name classifies to the FIRST role whose
# keyword list contains a substring of the lowercased name.  The order below
# is the SQF's order; the test also asserts the SQF lists the keywords in this
# order, so a reorder in the SQF fails here.
ROLE_KEYWORDS = [
    ("wheel", ["wheel", "tyre", "tire"]),
    ("track", ["track"]),
    ("rotor", ["rotor"]),
    ("glass", ["glass", "windshield", "window"]),
    ("engine", ["engine", "motor"]),
    ("fuel", ["fuel"]),
    ("turret", ["turret"]),
    ("gun", ["gun", "barrel"]),
    ("avionics", ["avionics"]),
    ("hull", ["hull", "body"]),
]


def classify_component_role(name: str) -> str:
    n = name.lower()
    for role, keywords in ROLE_KEYWORDS:
        if any(k in n for k in keywords):
            return role
    return ""


class TestClassifier(unittest.TestCase):
    """The role vocabulary, driven on real engine anchor names."""

    def test_hit_point_names(self):
        cases = {
            "HitLFWheel": "wheel",
            "HitRF2Wheel": "wheel",
            "HitLTrack": "track",
            "HitHRotor": "rotor",
            "HitVRotor": "rotor",
            "HitGlass1": "glass",
            "HitWindshield": "glass",
            "HitEngine": "engine",
            "HitMotor": "engine",
            "HitFuel": "fuel",
            "HitTurret": "turret",
            "HitGun": "gun",
            "HitAvionics": "avionics",
            "HitHull": "hull",
            "HitBody": "hull",
        }
        for name, role in cases.items():
            with self.subTest(name=name):
                self.assertEqual(classify_component_role(name), role)

    def test_selection_names(self):
        cases = {
            "wheel_1_1": "wheel",
            "engine_block": "engine",
            "glass_front": "glass",
            "hull_body": "hull",
            "turret_1": "turret",
        }
        for name, role in cases.items():
            with self.subTest(name=name):
                self.assertEqual(classify_component_role(name), role)

    def test_unknown_names_are_unclassified(self):
        for name in ["number_01", "camo1", "", "MFD", "dskjhkjhsad"]:
            with self.subTest(name=name):
                self.assertEqual(classify_component_role(name), "")

    def test_glass_beats_hull_for_a_compound_name(self):
        # "hull_glass" must read glass: the specific part precedes the body.
        self.assertEqual(classify_component_role("hull_glass"), "glass")

    def test_engine_precedes_fuel(self):
        # HitEngine and HitFuel are distinct roles; fuel must not read engine.
        self.assertEqual(classify_component_role("HitEngine"), "engine")
        self.assertEqual(classify_component_role("HitFuel"), "fuel")


class TestClassifierSource(unittest.TestCase):
    """The SQF keyword order matches the mirror above."""

    def setUp(self):
        self.code = _code_only(_read("fnc_classifyComponentRole.sqf"))

    def test_no_engine_call(self):
        # Pure: no engine read, no namespace read.
        self.assertNotIn("getAllHitPointsDamage", self.code)
        self.assertNotIn("selectionNames", self.code)
        self.assertNotIn("getVariable", self.code)

    def test_lowercases_the_name(self):
        self.assertIn("toLower _name", self.code)

    def test_keyword_order_matches_the_mirror(self):
        # Each role's first keyword must appear after the previous role's,
        # in the SQF body, proving the order the mirror encodes.
        positions = []
        for _role, keywords in ROLE_KEYWORDS:
            first = keywords[0]
            pos = self.code.find(f'find "{first}"')
            self.assertGreaterEqual(pos, 0, f'keyword "{first}" missing from SQF')
            positions.append(pos)
        self.assertEqual(positions, sorted(positions), "SQF keyword order drifted")

    def test_every_keyword_is_present(self):
        for _role, keywords in ROLE_KEYWORDS:
            for kw in keywords:
                with self.subTest(kw=kw):
                    self.assertIn(f'find "{kw}"', self.code)


class TestAnchorRegistrySource(unittest.TestCase):
    """fnc_getComponentAnchors reads the two anchor sources and caches per class."""

    def setUp(self):
        self.code = _code_only(_read("fnc_getComponentAnchors.sqf"))

    def test_reads_hit_points(self):
        self.assertIn("getAllHitPointsDamage", self.code)

    def test_reads_model_selections(self):
        self.assertIn("selectionNames", self.code)

    def test_uses_the_classifier(self):
        self.assertIn("call FUNC(classifyComponentRole)", self.code)

    def test_caches_per_class(self):
        self.assertIn("QGVAR(componentAnchorCache)", self.code)
        self.assertIn("typeOf _vehicle", self.code)

    def test_role_is_a_hashmap_key(self):
        self.assertIn("createHashMap", self.code)
        self.assertIn("pushBackUnique", self.code)

    def test_records_a_ceiling(self):
        # The header must state what the registry cannot reach (issue #128).
        raw = _read("fnc_getComponentAnchors.sqf")
        self.assertIn("ENGINE CEILINGS", raw)


class TestApplyComponentMaterialSource(unittest.TestCase):
    """fnc_applyComponentMaterial is the runtime-anchor application path."""

    def setUp(self):
        self.code = _code_only(_read("fnc_applyComponentMaterial.sqf"))

    def test_resolves_the_role(self):
        self.assertIn("call FUNC(getComponentAnchors)", self.code)

    def test_resolves_the_paint_index(self):
        self.assertIn("call FUNC(resolveSelectionPaintIndex)", self.code)

    def test_applies_the_material(self):
        self.assertIn("setObjectMaterial", self.code)

    def test_guards_the_empty_role(self):
        self.assertIn('_role == ""', self.code)

    def test_documents_the_three_mechanisms_and_ceiling(self):
        raw = _read("fnc_applyComponentMaterial.sqf")
        self.assertIn("PBO path override", raw)
        self.assertIn("config override", raw)
        self.assertIn("CEILINGS", raw)


class TestLagWiring(unittest.TestCase):
    """fnc_getThermalSelectionLag consumes the registry, with the hit-point map
    kept as the fallback, and the wheel-axle fallback unchanged."""

    def setUp(self):
        self.code = _code_only(_read("fnc_getThermalSelectionLag.sqf"))

    def test_reads_the_registry_for_the_engine_role(self):
        self.assertIn("call FUNC(getComponentAnchors)", self.code)
        self.assertIn('getOrDefault ["engine", []]', self.code)

    def test_keeps_the_hit_point_fallback(self):
        self.assertIn("FUNC(getHitPointMaterials)", self.code)

    def test_keeps_the_wheel_axle_fallback(self):
        self.assertIn('"wheel_1_1_axis"', self.code)
        self.assertIn("wheel_2_1_axis", self.code)

    def test_distance_from_the_source_is_unchanged(self):
        self.assertIn("_pos distance _source", self.code)
        self.assertIn("/ _maxDistance", self.code)


class TestPrepRegistration(unittest.TestCase):
    """Every new function is compiled by CBA XEH PREP."""

    def test_new_preps_are_registered(self):
        prep = (REPO / "addons" / "thermal" / "XEH_PREP.hpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("PREPS(surface,classifyComponentRole);", prep)
        self.assertIn("PREPS(display,getComponentAnchors);", prep)
        self.assertIn("PREPS(display,applyComponentMaterial);", prep)


if __name__ == "__main__":
    unittest.main()
