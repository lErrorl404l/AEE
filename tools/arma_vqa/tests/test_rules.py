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


if __name__ == "__main__":
    unittest.main()
