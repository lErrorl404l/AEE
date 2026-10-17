"""Regression tests. Run:  python3 -m unittest discover -s tests -v

Fixtures under tests/fixtures are tiny hand-written mods. Several cases exist because a scan of
real, shipped mods (ACE3, CBA_A3) once produced a false positive; those are labelled REAL-WORLD.
"""
import os
import sys
import unittest
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arma_vqa.analyze import Analyzer  # noqa: E402
from arma_vqa.sqf import tokenize  # noqa: E402

FIX = os.path.join(ROOT, "tests", "fixtures")


def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def scan(*rels):
    an = Analyzer()
    paths = [os.path.join(FIX, r) for r in rels]
    return an.scan(paths if len(paths) > 1 else paths[0])


def by_rule(res):
    return Counter(f.rule for f in res.findings)


def msgs(res, rule):
    return [f.message for f in res.findings if f.rule == rule]


class GapRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = scan("gap_rules")
        cls.c = by_rule(cls.res)

    def test_camera_fov_range_and_commit(self):
        self.assertEqual(self.c["CAM001"], 1)
        self.assertEqual(self.c["CAM002"], 1)

    def test_camera_effect_names_and_positions(self):
        m = msgs(self.res, "CAM003")
        self.assertEqual(len(m), 2, m)  # "Wobble" and "SIDEWAYS"; "terminate"/"back" lower-case is fine

    def test_thermal_rules(self):
        self.assertEqual(self.c["TI008"], 1)
        self.assertEqual(self.c["TI003"], 1)   # no "Loaded" handler in this fixture
        self.assertEqual(self.c["TI009"], 1)   # the (_set > 0) expression form must not count
        self.assertEqual(self.c["TI010"], 2)   # range + shape

    def test_tone_mapping_is_flagged_as_missing_in_arma3(self):
        self.assertEqual(self.c["TM001"], 2)

    def test_templates(self):
        m = msgs(self.res, "TPL001")
        self.assertEqual(len(m), 1)
        self.assertIn("NoSuchTemplate", m[0])
        self.assertEqual(self.c["TPL002"], 1)

    def test_force_in_nvg_needs_bool(self):
        self.assertEqual(self.c["NV004"], 1)

    def test_aperture_in_cfgfunctions_preinit(self):
        m = msgs(self.res, "AP004")
        self.assertEqual(len(m), 2, m)  # setAperture 40 and setAperture -1 both run pre-init
        self.assertTrue(any("preInit = 1" in x for x in m))

    def test_aperture_reset_idiom_is_not_reported(self):
        self.assertEqual([x for x in msgs(self.res, "AP001") if "-1" in x], [])

    def test_optics_config(self):
        self.assertEqual(self.c["CF006"], 1)
        self.assertEqual(self.c["CF005"], 1)  # weapon OpticsModes only; the turret must not count

    def test_real_world_vehicle_turret_zoom_convention_not_flagged(self):
        # REAL-WORLD: ACE3 Javelin turret has opticsZoomMin > opticsZoomMax and works fine
        self.assertTrue(all("MainTurret" not in x for x in msgs(self.res, "CF005")))

    def test_real_world_vanilla_optics_effect_names(self):
        # REAL-WORLD/wiki: the wiki's own example uses OpticsCHAbera5; names follow OpticsBlurN / OpticsCHAberaN
        self.assertEqual(self.c["CF001"], 0)

    def test_real_world_config_expression_strings(self):
        # REAL-WORLD: CBA params[] = {..., "0.35/(getResolution select 4)", ...}
        self.assertEqual([m for m in msgs(self.res, "PP003") if "expected a number" in m], [])

    def test_gvar_handles_are_tracked(self):
        # REAL-WORLD: ACE/CBA store handles in GVAR(...) variables
        bad = [f for f in self.res.findings if "fn_macros.sqf" in f.file]
        rules = Counter(f.rule for f in bad)
        self.assertEqual(rules["PP002"], 1, bad)   # wrong array length on GVAR(bad)
        self.assertEqual(rules["PP008"], 1, bad)   # GVAR(bad) never enabled
        self.assertEqual(rules["PP007"], 1)        # GVAR(bad) is adjusted but never committed
        # the correct GVAR(ppe) block (lines 1-8) may carry the info-level "never destroyed" note
        # (persistent global effects are normal) but must not get the warning-level lifecycle rules
        good_lines = {f.line for f in bad if f.rule in ("PP007", "PP008")}
        self.assertTrue(all(ln >= 17 for ln in good_lines), good_lines)

    def test_gvar_radial_radii_above_one_are_only_info(self):
        # REAL-WORLD: ACE3 uses radii of 10 and 2 in shipped code
        radial = [f for f in self.res.findings if "radialMajor" in f.message or "radialMinor" in f.message]
        self.assertTrue(all(f.sev == "info" for f in radial), radial)

    def test_returned_handles_are_not_lifecycle_noise(self):
        # REAL-WORLD: ACE medical_feedback / CBA optics create a handle in a helper and return it
        noisy = [f for f in self.res.findings if "fn_macros.sqf" in f.file and f.line in range(9, 14) and f.rule in ("PP007", "PP008", "PP009")]
        self.assertEqual(noisy, [])


class CleanMod(unittest.TestCase):
    def test_no_warnings_or_errors(self):
        res = scan("clean_mod")
        bad = [f for f in res.findings if f.sev in ("warning", "error")]
        self.assertEqual(bad, [], bad)

    def test_loaded_handler_silences_savegame_note(self):
        res = scan("clean_mod")
        self.assertEqual(by_rule(res)["TI003"], 0)


class MultiRoot(unittest.TestCase):
    def test_cross_mod_priority_collision(self):
        res = scan("two_mods/mod_a", "two_mods/mod_b")
        hits = msgs(res, "PP004")
        self.assertEqual(len(hits), 1, hits)
        self.assertIn("cross-mod", hits[0])
        self.assertIn("mod_a", hits[0])
        self.assertIn("mod_b", hits[0])

    def test_each_mod_alone_is_clean(self):
        for m in ("two_mods/mod_a", "two_mods/mod_b"):
            res = scan(m)
            self.assertEqual([f for f in res.findings if f.sev in ("warning", "error")], [], m)


class CameraContext(unittest.TestCase):
    def test_camera_in_same_addon_other_file_is_enough(self):
        # REAL-WORLD: ACE arsenal/spectator call camUseNVG in one file and camCreate in another
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            addon = os.path.join(d, "addons", "viewer")
            os.makedirs(addon)
            write(os.path.join(addon, "config.cpp"), "class CfgPatches { class v {}; };\n")
            write(os.path.join(addon, "fn_open.sqf"), 'GVAR(cam) = "camera" camCreate [0,0,0];\nGVAR(cam) cameraEffect ["Internal","BACK"];\n')
            write(os.path.join(addon, "fn_toggle.sqf"), "camUseNVG true;\ntrue setCamUseTI 0;\n")
            res = Analyzer().scan(d)
            self.assertEqual(by_rule(res)["NV003"], 0)

    def test_no_camera_anywhere_still_warns(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            write(os.path.join(d, "fn_toggle.sqf"), "camUseNVG true;\n")
            res = Analyzer().scan(d)
            self.assertEqual(by_rule(res)["NV003"], 1)
            self.assertEqual([f.sev for f in res.findings if f.rule == "NV003"], ["warning"])


class Lexer(unittest.TestCase):
    def test_gvar_family_collapses_to_one_identifier(self):
        lx = tokenize("GVAR(foo) = 1; EGVAR(common,bar) = 2; GVARMAIN(baz) = 3;", "<mem>")
        ids = [t.val for t in lx.toks if t.kind == "id"]
        self.assertEqual(ids, ["mod_foo", "common_bar", "main_baz"])

    def test_non_symbol_macros_are_left_alone(self):
        lx = tokenize("TRACE_1(x,y); QUOTE(1+1);", "<mem>")
        self.assertEqual([t.val for t in lx.toks if t.kind == "id"], ["TRACE_1", "x", "y", "QUOTE"])


def in_file(res, name, rule=None):
    return [f for f in res.findings if f.file.endswith(name) and (rule is None or f.rule == rule)]


class UiLayers(unittest.TestCase):
    """cutRsc / cutText / cutObj / cutFadeOut / titleText / BIS_fnc_rscLayer."""

    @classmethod
    def setUpClass(cls):
        cls.res = scan("ui_layers")
        cls.c = by_rule(cls.res)

    def test_real_world_idioms_are_silent(self):
        # REAL-WORLD: numeric 135471 (ACE dagr), (name call BIS_fnc_rscLayer) layers (ACE zeus/interaction),
        # `_layer = [..] call BIS_fnc_rscLayer` (ACE scopes), structured text with the flag (ACE hunterkiller),
        # lower-case effect names ("plain down", "black out"), curtains that are lifted again (ACE huntir)
        self.assertEqual(in_file(self.res, "fn_good.sqf"), [], in_file(self.res, "fn_good.sqf"))

    def test_layer_number_rules(self):
        m = msgs(self.res, "UI002")
        self.assertEqual(len(m), 2, m)
        self.assertTrue(any("negative" in x for x in m))
        self.assertTrue(any("rounded" in x for x in m))

    def test_effect_type_must_be_one_of_the_documented_names(self):
        m = msgs(self.res, "UI003")
        self.assertEqual(len(m), 1)
        self.assertIn("FLASH", m[0])

    def test_argument_shape_and_types(self):
        m = msgs(self.res, "UI004")
        self.assertEqual(len(m), 3, m)
        self.assertTrue(any("no layer argument" in x for x in m))
        self.assertTrue(any("speed" in x for x in m))
        self.assertTrue(any("at most 5" in x for x in m))

    def test_structured_text_markup_needs_the_flag(self):
        self.assertEqual(self.c["UI005"], 1)

    def test_unknown_resource_class(self):
        sev = {f.message.split('"')[1]: f.sev for f in self.res.findings if f.rule == "UI006"}
        self.assertEqual(sev["tag_hudd"], "warning")        # near miss of tag_hud
        self.assertIn("did you mean \"tag_hud\"", msgs(self.res, "UI006")[0])
        self.assertEqual(sev["Unknown_Thing"], "info")      # could be vanilla / another addon

    def test_layer_names_are_case_sensitive(self):
        self.assertEqual(self.c["UI009"], 1)

    def test_fade_out_scaling_note(self):
        self.assertEqual(self.c["UI007"], 1)

    def test_default_class_and_reserved_layer_zero(self):
        self.assertEqual(self.c["UI010"], 1)
        self.assertGreaterEqual(self.c["UI008"], 2)

    def test_rsc_layer_needs_a_string(self):
        self.assertEqual(self.c["UI011"], 1)

    def test_curtains(self):
        self.assertEqual(self.c["UI014"], 1)   # WHITE OUT without fade-in
        self.assertEqual(self.c["UI015"], 1)   # BLACK FADED without speed
        self.assertEqual(self.c["UI016"], 2)   # BLACK OUT and WHITE OUT never lifted; the lifted ones in fn_good are fine
        self.assertEqual(in_file(self.res, "fn_good.sqf", "UI016"), [])

    def test_clear_on_a_layer_nothing_shows(self):
        m = msgs(self.res, "UI013")
        self.assertEqual(len(m), 1)
        self.assertIn("ghost", m[0])

    def test_same_layer_different_resources_in_one_mod_is_only_info(self):
        sev = [f.sev for f in self.res.findings if f.rule == "UI001"]
        self.assertTrue(sev and all(x == "info" for x in sev), sev)

    def test_cross_mod_layer_collision_is_a_warning(self):
        res = scan("ui_layer_mods/mod_a", "ui_layer_mods/mod_b")
        hits = [f for f in res.findings if f.rule == "UI001"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].sev, "warning")
        self.assertIn("cross-mod", hits[0].message)

    def test_layer_table_is_reported(self):
        names = {r["layer"] for r in self.res.layers}
        self.assertIn('layer "tag_hud"', names)
        self.assertIn("layer 135471", names)
        self.assertIn('rscLayer "tag_rsc"', names)


class UiLexing(unittest.TestCase):
    def test_qgvar_is_a_string_layer_name(self):
        lx = tokenize("QGVAR(layer) cutRsc [QGVAR(cls), 'PLAIN']; QEGVAR(common,x) cutFadeOut 1;", "<mem>")
        strs = [t.val for t in lx.toks if t.kind == "str"]
        self.assertEqual(strs, ["mod_layer", "mod_cls", "PLAIN", "common_x"])

    def test_unary_minus_layer(self):
        from arma_vqa.sqf import collect_assignments, extract_calls
        lx = tokenize('-1 cutRsc ["a", "PLAIN"]; x = 2; 3 - 1 cutRsc ["b", "PLAIN"];', "<mem>")
        calls = [c for c in extract_calls(lx, {}).calls if c.cmd == "cutrsc"]
        self.assertEqual(calls[0].left, -1)

    def test_array_elements_survive_an_unresolvable_first_element(self):
        from arma_vqa.sqf import extract_calls
        lx = tokenize('"l" cutText [format ["<t>%1</t>", _x], "PLAIN", -1, false, true];', "<mem>")
        c = extract_calls(lx, {}).calls[0]
        self.assertEqual(c.items[1:], ["PLAIN", -1, False, True])

    def test_rsc_layer_call_is_a_distinct_layer_kind(self):
        from arma_vqa.sqf import RscLayer, extract_calls
        lx = tokenize('("abc" call BIS_fnc_rscLayer) cutRsc ["a", "PLAIN"]; _l = ["x"] call BIS_fnc_rscLayer; _l cutFadeOut 1;', "<mem>")
        calls = extract_calls(lx, {}).calls
        lefts = [c.left for c in calls if c.cmd in ("cutrsc", "cutfadeout")]
        self.assertTrue(all(isinstance(v, RscLayer) for v in lefts), lefts)


class MapGrid(unittest.TestCase):
    """CfgWorlds >> World >> Grid (community-sourced, see arma_vqa/mapcfg.py)."""

    def test_real_world_grids_are_clean(self):
        # REAL-WORLD: VR (offsetY 8192), abc_sample (zoomMax 1e+030.0 on the last class), the PMC 40960 m tutorial
        # grid with four zoom levels and 4-digit labels, and a Kunduz-style grid that inherits its zoom classes
        res = scan("map_grid_ok")
        bad = [f for f in res.findings if f.sev in ("warning", "error")]
        self.assertEqual(bad, [], bad)
        self.assertEqual(by_rule(res)["MAP008"], 1)   # the 4-digit format is only an info note (sources disagree)

    def test_label_corners_follow_the_community_formula(self):
        from arma_vqa import mapcfg
        res = scan("map_grid_ok")
        g = {x["world"]: x for x in res.grids}
        z1 = g["abc_sample"]["zooms"][0]
        self.assertEqual(z1["corners"]["SW"], "000 000")        # numbers start at 0 in the south-west corner ...
        self.assertEqual(z1["corners"]["NE"], "051 051")        # ... and rise to the north and east (5120 m / 100 m)
        self.assertEqual(z1["labelsY"], [0, 51])
        z2 = g["pmc_40k"]["zooms"][1]
        self.assertEqual(z2["corners"]["NE"], "409 409")        # 40960 m / 100 m
        self.assertEqual(g["vr_like"]["zooms"][0]["corners"]["centre"], "040 040")

    def test_numbers_that_go_negative(self):
        res = scan("map_grid_bad")
        m = [f for f in res.findings if f.rule == "MAP001"]
        self.assertTrue(any("no_offset" in f.message and "-52" in f.message for f in m), [f.message for f in m])
        # a positive stepY with offsetY = mapSize also flips the Y axis out of the map
        self.assertTrue(any("broken_steps" in f.message for f in m))

    def test_digits_that_do_not_fit_the_format(self):
        res = scan("map_grid_bad")
        m = msgs(res, "MAP002")
        self.assertEqual(len(m), 4, m)   # X and Y on two zoom levels of the 102400 m map
        self.assertTrue(all("too_big" in x for x in m))

    def test_zoom_ordering_and_nesting(self):
        res = scan("map_grid_bad")
        self.assertEqual(sum(1 for x in msgs(res, "MAP003") if "messy" in x), 1)
        self.assertEqual(sum(1 for x in msgs(res, "MAP006") if "messy" in x), 2)   # X and Y of the 100 m vs 250 m steps
        self.assertEqual(sum(1 for x in msgs(res, "MAP004") if "messy" in x), 1)

    def test_steps_and_incomplete_classes(self):
        res = scan("map_grid_bad")
        sev = {(f.rule, f.severity if hasattr(f, "severity") else f.sev) for f in res.findings if "broken_steps" in f.message}
        self.assertIn(("MAP005", "error"), sev)
        self.assertIn(("MAP007", "warning"), sev)

    def test_world_basics(self):
        res = scan("map_grid_bad")
        m = msgs(res, "MAP009")
        self.assertTrue(any("centerPosition" in x for x in m))
        self.assertTrue(any("gridNumbersOverLines" in x for x in m))
        self.assertTrue(any("mapArea" in x for x in m))

    def test_inherited_zoom_classes_are_not_flagged_as_incomplete(self):
        res = scan("map_grid_ok")
        self.assertEqual([f for f in res.findings if f.rule == "MAP007"], [])


class MapControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = scan("map_ctrl")

    def test_real_world_overrides_are_silent(self):
        # REAL-WORLD: ACE3 RscMapControl overrides (showCountourInterval!), MicroDAGR mini map (scaleMax 10)
        quiet = [f for f in self.res.findings if "BadMap" not in f.message and f.rule != "MAPUI007"]
        self.assertEqual(quiet, [], quiet)

    def test_helper_map_control_inside_group_is_only_info(self):
        # REAL-WORLD: ACE3 fcs/laser put RscMapControl helpers inside CA_IGUI_elements_group and they work
        hits = [f for f in self.res.findings if f.rule == "MAPUI007"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].sev, "info")

    def test_colours(self):
        m = msgs(self.res, "MAPUI001")
        self.assertEqual(len(m), 3, m)

    def test_grid_text_and_visibility(self):
        self.assertEqual(self.res and by_rule(self.res)["MAPUI002"], 1)
        sev = sorted(f.sev for f in self.res.findings if f.rule == "MAPUI005")
        self.assertEqual(sev, ["info", "warning"])

    def test_scales_and_satellite_alpha(self):
        self.assertEqual(by_rule(self.res)["MAPUI003"], 1)
        self.assertEqual(by_rule(self.res)["MAPUI006"], 1)

    def test_misspelled_properties(self):
        m = msgs(self.res, "MAPUI004")
        self.assertEqual(len(m), 2, m)
        self.assertTrue(any("showCountourInterval" in x for x in m))
        self.assertTrue(any("colorSea" in x for x in m))


if __name__ == "__main__":
    unittest.main()
