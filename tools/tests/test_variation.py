#!/usr/bin/env python3
"""AEE dynamic variation-family kernel tests.

Executes the REAL pure kernels through tools/tests/sqf_lite.py and pins the
generated model and the config registration:

  addons/symbology/functions/symbology/fnc_variationFamilies.sqf
  addons/symbology/functions/symbology/fnc_variationOptions.sqf
  addons/symbology/functions/symbology/fnc_variationResolve.sqf
  addons/symbology/functions/symbology/fnc_variationState.sqf

The marker type and colour that the resolver delegates to are already pinned by
tools/tests/test_symbology.py (TestSymbolResolve); this suite cites that test
and does not duplicate it.

Run: python3 -m unittest tools.tests.test_variation -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))

from sqf_lite import run_sqf  # noqa: E402

SYMBOLOGY = REPO / "addons" / "symbology"
SYM = SYMBOLOGY / "functions" / "symbology"
FAMILIES_KERNEL = SYM / "fnc_variationFamilies.sqf"
OPTIONS_KERNEL = SYM / "fnc_variationOptions.sqf"
RESOLVE_KERNEL = SYM / "fnc_variationResolve.sqf"
STATE_KERNEL = SYM / "fnc_variationState.sqf"
APPLY_KERNEL = SYM / "fnc_variationApply.sqf"
SYMBOL_RESOLVE_KERNEL = SYM / "fnc_symbolResolve.sqf"
MARKER_TYPE_KERNEL = SYM / "fnc_symbologyMarkerType.sqf"
MARKER_COLOR_KERNEL = SYM / "fnc_symbologyMarkerColor.sqf"
TABLES_SQF = SYMBOLOGY / "data" / "symbology_tables.sqf"
VARIATION_SQF = SYMBOLOGY / "data" / "variation_families.sqf"
GENERATOR = REPO / "tools" / "gen_variation_families.py"
CONFIG_SRC = (SYMBOLOGY / "config.cpp").read_text(encoding="utf-8")
VARIATION_CONFIG_SRC = (SYMBOLOGY / "config_variations.hpp").read_text(encoding="utf-8")
RUNNER_SRC = (REPO / "tools" / "run_tests.py").read_text(encoding="utf-8")
PREP_SRC = (SYMBOLOGY / "XEH_PREP.hpp").read_text(encoding="utf-8")
APPLY_SRC = APPLY_KERNEL.read_text(encoding="utf-8")
MARKERS_APPLY_SRC = (SYM / "fnc_symbologyMarkersApply.sqf").read_text(encoding="utf-8")

MODEL = run_sqf(VARIATION_SQF, [])
SYM_TABLES = run_sqf(TABLES_SQF, [])

OPTION_ORDER = ("affiliation", "dimension", "function", "echelon", "palette")
# The derived value count per option, from the shipped tables.
OPTION_COUNTS = (4, 7, 20, 13, 3)

# Every committed variation source, for the provenance guard.
ALL_VARIATION_SRC = "\n".join(
    [
        FAMILIES_KERNEL.read_text(encoding="utf-8"),
        OPTIONS_KERNEL.read_text(encoding="utf-8"),
        RESOLVE_KERNEL.read_text(encoding="utf-8"),
        STATE_KERNEL.read_text(encoding="utf-8"),
        VARIATION_SQF.read_text(encoding="utf-8"),
        VARIATION_CONFIG_SRC,
        GENERATOR.read_text(encoding="utf-8"),
    ]
)

FORBIDDEN_PROVENANCE = (
    "Agent:",
    "opencode",
    "claude",
    "anthropic",
    "openai",
    "deepseek",
    "hephaestus",
)


def _globals() -> dict:
    """The real kernels and the real generated tables, wired as the engine."""
    globals_ = {
        "aee_symbology_variationFamilies": MODEL,
        "aee_symbology_symbologyTables": SYM_TABLES,
        "sideUnknown": 0,
    }
    globals_["__FUNC__variationState"] = lambda pairs: run_sqf(
        STATE_KERNEL, [pairs], globals_
    )
    globals_["__FUNC__symbologyMarkerType"] = lambda aff, cat, dim, ech, pal: run_sqf(
        MARKER_TYPE_KERNEL, [aff, cat, dim, ech, pal], globals_
    )
    globals_["__FUNC__symbologyMarkerColor"] = lambda aff, pal: run_sqf(
        MARKER_COLOR_KERNEL, [aff, pal], globals_
    )
    globals_["__FUNC__symbolResolve"] = lambda side, cat, aff, ech, pal, dim: run_sqf(
        SYMBOL_RESOLVE_KERNEL, [side, cat, aff, ech, pal, dim], globals_
    )
    return globals_


def families() -> list:
    return run_sqf(FAMILIES_KERNEL, [], _globals())


def options(family_id: str) -> list:
    return run_sqf(OPTIONS_KERNEL, [family_id], _globals())


def state(pairs: list) -> list:
    return run_sqf(STATE_KERNEL, [pairs], _globals())


def resolve(family_id: str, selected: list) -> list:
    return run_sqf(RESOLVE_KERNEL, [family_id, selected], _globals())


class TestVariationModel(unittest.TestCase):
    """fnc_variationFamilies and fnc_variationOptions, executed."""

    def test_one_family_with_five_options_in_order(self):
        fam = families()
        self.assertEqual(len(fam), 1)
        family = fam[0]
        self.assertEqual(family[0], "symbol")
        self.assertEqual(family[2], "AEE_Variation")
        self.assertEqual(family[3], "AEE_Variation")
        self.assertEqual(family[4], "symbolResolve")
        self.assertEqual([option[0] for option in family[5]], list(OPTION_ORDER))

    def test_the_option_values_are_derived_from_the_tables(self):
        out = options("symbol")
        self.assertEqual([option[0] for option in out], list(OPTION_ORDER))
        self.assertEqual([len(option[2]) for option in out], list(OPTION_COUNTS))

    def test_every_value_carries_id_label_and_token(self):
        for option in options("symbol"):
            for value in option[2]:
                with self.subTest(option=option[0], value=value):
                    self.assertEqual(len(value), 3)
                    self.assertTrue(value[0])
                    self.assertTrue(value[1])
                    self.assertTrue(value[2])

    def test_an_unknown_family_returns_no_options(self):
        self.assertEqual(options("does_not_exist"), [])


class TestVariationState(unittest.TestCase):
    """fnc_variationState, executed: a normalised state with defaults."""

    def test_a_missing_option_falls_back_to_the_family_default(self):
        self.assertEqual(
            state([["symbol", "affiliation", "hostile"]]),
            [
                ["affiliation", "hostile"],
                ["dimension", "land"],
                ["function", "infantry"],
                ["echelon", "team"],
                ["palette", "NATO"],
            ],
        )

    def test_an_unknown_value_falls_back_to_the_family_default(self):
        normalised = dict(state([["symbol", "affiliation", "not_a_value"]]))
        self.assertEqual(normalised["affiliation"], "friend")

    def test_an_unknown_family_returns_no_state(self):
        self.assertEqual(state([["does_not_exist", "affiliation", "friend"]]), [])


class TestVariationResolve(unittest.TestCase):
    """fnc_variationResolve, executed: an option state -> a concrete symbol.

    The marker type and colour contract is pinned by
    tools/tests/test_symbology.py (TestSymbolResolve); this suite proves the
    variation layer selects the resolver's inputs, not the composition.
    """

    def test_hostile_armour_resolves_to_the_marker_and_colour(self):
        self.assertEqual(
            resolve("symbol", [["affiliation", "hostile"], ["function", "armour"]]),
            ["hostile", "AEE_o_armor", "ColorAEE", "team"],
        )

    def test_a_missing_function_uses_the_family_default(self):
        out = resolve("symbol", [["affiliation", "hostile"]])
        self.assertEqual(out[1], "AEE_o_inf")
        self.assertEqual(out[2], "ColorAEE")

    def test_an_empty_state_resolves_the_family_defaults(self):
        self.assertEqual(
            resolve("symbol", []),
            ["friend", "AEE_b_inf", "ColorAEE", "team"],
        )

    def test_an_unknown_option_id_is_ignored(self):
        out = resolve("symbol", [["nonsense", "x"], ["function", "engineer"]])
        self.assertEqual(out[1], "AEE_b_eng")


class TestVariationConfig(unittest.TestCase):
    """The generated config registers the one option-driven entry."""

    def test_the_entry_is_registered_in_the_config(self):
        self.assertIn('#include "config_variations.hpp"', CONFIG_SRC)
        self.assertIn("class AEE_Variation {", CONFIG_SRC)
        self.assertIn("AEE_Variation", CONFIG_SRC)

    def test_the_generated_header_declares_the_entry(self):
        self.assertIn("class AEE_Variation: AEE_MarkerBase {", VARIATION_CONFIG_SRC)
        self.assertIn('markerClass = "AEE_Variation";', VARIATION_CONFIG_SRC)
        self.assertIn("scope = 2;", VARIATION_CONFIG_SRC)

    def test_the_generated_artifacts_carry_the_generator_header(self):
        self.assertIn(
            "Generated by tools/gen_variation_families.py", VARIATION_CONFIG_SRC
        )
        self.assertIn(
            "Generated by tools/gen_variation_families.py",
            VARIATION_SQF.read_text(encoding="utf-8"),
        )


class TestVariationProvenance(unittest.TestCase):
    """No agent, tooling or model provenance in a variation source."""

    def test_no_forbidden_provenance_token(self):
        for token in FORBIDDEN_PROVENANCE:
            with self.subTest(token=token):
                self.assertNotIn(token, ALL_VARIATION_SRC)


class TestVariationCollapse(unittest.TestCase):
    """The picker collapse: the AEE-produced variants are hidden, the engine
    re-points stay picker-visible.

    The AEE-produced headers (catalogue, cross-product, taxonomy, family
    aliases, modifiers) inherit AEE_MarkerBase and set scope = 0.  The engine
    re-points in config_markers.hpp restate their engine parent and set no
    scope, so they inherit the engine scope (2) and stay visible.
    """

    PRODUCED_HEADERS = (
        "config_markers.hpp",
        "config_crossproduct.hpp",
        "config_taxonomy.hpp",
        "config_family.hpp",
        "config_modifiers.hpp",
    )

    def _produced(self, header: str) -> tuple[int, str]:
        text = (SYMBOLOGY / header).read_text(encoding="utf-8")
        produced = len(re.findall(r"class AEE_\w+: AEE_MarkerBase \{", text))
        return produced, text

    def test_no_aee_produced_class_is_picker_visible(self):
        for header in self.PRODUCED_HEADERS:
            with self.subTest(header=header):
                _produced, text = self._produced(header)
                self.assertEqual(
                    text.count("scope = 2;"), 0, f"{header} shows a concrete variant"
                )

    def test_every_aee_produced_class_is_hidden(self):
        for header in self.PRODUCED_HEADERS:
            with self.subTest(header=header):
                produced, text = self._produced(header)
                self.assertGreater(produced, 0, header)
                self.assertEqual(produced, text.count("scope = 0;"), header)

    def test_the_engine_repoints_stay_visible(self):
        text = (SYMBOLOGY / "config_markers.hpp").read_text(encoding="utf-8")
        overrides = re.findall(r"class \w+: \w+ \{ icon = ", text)
        self.assertGreaterEqual(len(overrides), 43)
        self.assertNotIn("scope = 0;", "\n".join(overrides))


class TestVariationApply(unittest.TestCase):
    """The apply layer re-types the family markers, client-local only.

    The behavioural assertion (a marker of type AEE_Variation resolves to
    AEE_o_armor for the hostile-armour state, and reverts to AEE_Variation on
    restore) runs in the headless probe P143, which drives the real engine
    marker commands.
    """

    def test_the_kernel_is_prepped(self):
        self.assertIn("PREPS(symbology,variationApply)", PREP_SRC)

    def test_it_delegates_to_the_resolver(self):
        self.assertIn("FUNC(variationResolve)", APPLY_SRC)

    def test_it_uses_only_local_marker_commands(self):
        self.assertIn("setMarkerTypeLocal", APPLY_SRC)
        self.assertIn("setMarkerColorLocal", APPLY_SRC)
        for global_command in (
            "setMarkerType ",
            "setMarkerColor ",
            "setMarkerPos ",
            "setMarkerDir ",
            "createMarker ",
            "deleteMarker ",
        ):
            with self.subTest(command=global_command):
                self.assertNotIn(global_command, APPLY_SRC)

    def test_the_apply_pass_handles_the_family_entry(self):
        self.assertIn('"AEE_Variation"', MARKERS_APPLY_SRC)
        self.assertIn("FUNC(variationResolve)", MARKERS_APPLY_SRC)


class TestVariationSettings(unittest.TestCase):
    """The headless route: one CBA LIST setting per option."""

    SETTINGS_SRC = (SYMBOLOGY / "initSettings.inc.sqf").read_text(encoding="utf-8")
    POSTINIT_SRC = (SYMBOLOGY / "XEH_postInit.sqf").read_text(encoding="utf-8")

    def test_the_five_settings_are_declared_as_list(self):
        for key in (
            "variationAffiliation",
            "variationDimension",
            "variationFunction",
            "variationEchelon",
            "variationPalette",
        ):
            with self.subTest(setting=key):
                self.assertIn(f"QGVAR({key})", self.SETTINGS_SRC)
        self.assertIn('"LIST"', self.SETTINGS_SRC)

    def test_the_settings_are_under_aee_hud_symbology(self):
        self.assertIn('["AEE HUD", "Symbology"]', self.SETTINGS_SRC)

    def test_a_setting_change_rebuilds_the_state(self):
        self.assertIn("aee_symbology_fnc_variationSettingsChanged", self.SETTINGS_SRC)
        self.assertIn("PREPS(symbology,variationSettingsChanged)", PREP_SRC)

    def test_the_keybind_opens_the_dialog(self):
        self.assertIn("CBA_fnc_addKeybind", self.POSTINIT_SRC)
        self.assertIn("FUNC(variationDialogOpen)", self.POSTINIT_SRC)


class TestVariationSuiteRegistration(unittest.TestCase):
    """The suite registers itself in the runner, so CI runs it."""

    def test_the_suite_is_registered_in_the_runner(self):
        self.assertIn("tools/tests/test_variation.py", RUNNER_SRC)


if __name__ == "__main__":
    unittest.main()
