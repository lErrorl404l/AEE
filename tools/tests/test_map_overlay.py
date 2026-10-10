#!/usr/bin/env python3
"""The physics-state tactical map overlay (issue #155).

The overlay draws AEE physics state on the map, reusing the ONE existing map
Draw handler (fnc_mgrsMapDraw) so the map keeps a single rendering path.  Its
pure kernels are executed here through tools/tests/sqf_lite.py; the wiring is
pinned by source-contract checks.

Honest scope: only the values AEE computes PER POSITION are drawn as layers
(biome, local wind) or shown at the clicked point (biome, surface, local wind,
terrain height).  The global scalars the issue names (temperature, WBGT, flood,
fire, snow, radio, hypoxia) are computed at the player position only, so they
appear in the click readout as "current" and are NOT drawn as map zones.

Run: python3 -m unittest tools.tests.test_map_overlay -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CART = ROOT / "addons" / "cartography"
HUD = CART / "functions" / "hud"

BIOME_COLOR = HUD / "fnc_mapBiomeColor.sqf"
WIND_ARROW = HUD / "fnc_mapWindArrow.sqf"
DECLINATION = HUD / "fnc_mapDeclinationRose.sqf"
READOUT = HUD / "fnc_mapStateReadout.sqf"
FIELD_PLAN = HUD / "fnc_mapFieldPlan.sqf"

PREP_SRC = (CART / "XEH_PREP.hpp").read_text(encoding="utf-8")
SETTINGS_SRC = (CART / "initSettings.inc.sqf").read_text(encoding="utf-8")
STRINGTABLE_SRC = (CART / "stringtable.xml").read_text(encoding="utf-8")
POSTINIT_SRC = (CART / "XEH_postInit.sqf").read_text(encoding="utf-8")
CONFIG_SRC = (CART / "config.cpp").read_text(encoding="utf-8")
DRAW_SRC = (HUD / "fnc_mgrsMapDraw.sqf").read_text(encoding="utf-8")
CLICK_SRC = (HUD / "fnc_mapClickQuery.sqf").read_text(encoding="utf-8")
OVERLAY_SRC = (HUD / "fnc_mapOverlayDraw.sqf").read_text(encoding="utf-8")


def _close(a, b, tol=1e-6):
    return abs(a - b) <= tol


class TestBiomeColor(unittest.TestCase):
    """fnc_mapBiomeColor: Koppen code -> [RGBA, group label]."""

    def test_temperate_code(self):
        tint, label = run_sqf(BIOME_COLOR, ["Cfb"], {})
        self.assertTrue(_close(tint[0], 0.45))
        self.assertTrue(_close(tint[1], 0.75))
        self.assertTrue(_close(tint[2], 0.35))
        self.assertEqual(label, "Temperate")

    def test_tropical_code(self):
        _tint, label = run_sqf(BIOME_COLOR, ["Af"], {})
        self.assertEqual(label, "Tropical")

    def test_arid_code(self):
        _tint, label = run_sqf(BIOME_COLOR, ["BWh"], {})
        self.assertEqual(label, "Arid")

    def test_continental_code(self):
        _tint, label = run_sqf(BIOME_COLOR, ["Dfb"], {})
        self.assertEqual(label, "Continental")

    def test_polar_code(self):
        _tint, label = run_sqf(BIOME_COLOR, ["ET"], {})
        self.assertEqual(label, "Polar")

    def test_unknown_code_is_grey(self):
        tint, label = run_sqf(BIOME_COLOR, [""], {})
        self.assertEqual(label, "Unknown")
        self.assertTrue(_close(tint[0], 0.50))

    def test_lower_case_code_still_groups(self):
        _tint, label = run_sqf(BIOME_COLOR, ["cfb"], {})
        self.assertEqual(label, "Temperate")


class TestWindArrow(unittest.TestCase):
    """fnc_mapWindArrow: [e, n] m/s + length -> a centred segment."""

    def test_easterly_points_east(self):
        seg = run_sqf(WIND_ARROW, [[1, 0], 100], {})
        self.assertTrue(_close(seg[0][0], -50.0))
        self.assertTrue(_close(seg[0][1], 0.0))
        self.assertTrue(_close(seg[1][0], 50.0))
        self.assertTrue(_close(seg[1][1], 0.0))

    def test_northerly_points_north(self):
        seg = run_sqf(WIND_ARROW, [[0, 2], 100], {})
        self.assertTrue(_close(seg[1][0], 0.0))
        self.assertTrue(_close(seg[1][1], 50.0))

    def test_calm_is_a_zero_segment(self):
        seg = run_sqf(WIND_ARROW, [[0, 0], 100], {})
        self.assertEqual(seg, [[0, 0], [0, 0]])

    def test_zero_length_is_a_zero_segment(self):
        seg = run_sqf(WIND_ARROW, [[1, 0], 0], {})
        self.assertEqual(seg, [[0, 0], [0, 0]])


class TestDeclinationRose(unittest.TestCase):
    """fnc_mapDeclinationRose: declination deg -> [trueN, magN] rays."""

    def test_zero_declination_rays_align(self):
        true_n, mag_n = run_sqf(DECLINATION, [0, 100], {})
        self.assertTrue(_close(true_n[0], 0.0))
        self.assertTrue(_close(true_n[1], 100.0))
        self.assertTrue(_close(mag_n[0], 0.0))
        self.assertTrue(_close(mag_n[1], 100.0))

    def test_east_declination_rotates_clockwise(self):
        true_n, mag_n = run_sqf(DECLINATION, [90, 100], {})
        self.assertTrue(_close(true_n[1], 100.0))
        # 90 deg east: magnetic north is due east of true north.
        self.assertTrue(_close(mag_n[0], 100.0))
        self.assertTrue(_close(mag_n[1], 0.0))

    def test_non_positive_radius_is_zero(self):
        true_n, mag_n = run_sqf(DECLINATION, [10, 0], {})
        self.assertEqual(true_n, [0, 0])
        self.assertEqual(mag_n, [0, 0])


class TestStateReadout(unittest.TestCase):
    """fnc_mapStateReadout: title + rows -> the weather-report block."""

    def test_block_header_and_rows(self):
        text = run_sqf(
            READOUT, ["AEE Map Query", [["Biome", "Cfb"], ["Terrain", "12 m"]]], {}
        )
        self.assertTrue(text.startswith("=== AEE Map Query ==="))
        # The separator is a newline in SQF; the harness keeps the escape
        # literal, so assert the row content, not the separator.
        self.assertIn("Biome: Cfb", text)
        self.assertIn("Terrain: 12 m", text)

    def test_empty_value_row_is_skipped(self):
        text = run_sqf(READOUT, ["T", [["A", "1"], ["B", ""]]], {})
        self.assertIn("A: 1", text)
        self.assertNotIn("B:", text)

    def test_empty_rows_is_just_the_header(self):
        text = run_sqf(READOUT, ["T", []], {})
        self.assertEqual(text, "=== T ===")


class TestFieldPlan(unittest.TestCase):
    """fnc_mapFieldPlan: samples the per-position kernels over a rect."""

    def _run(self, rect):
        calls = {"biome": [], "wind": []}

        def biome(pos):
            calls["biome"].append(pos)
            return "Cfb"

        def wind(pos, _height):
            calls["wind"].append(pos)
            return [1.0, 0.0]

        plan = run_sqf(
            FIELD_PLAN,
            [rect],
            {
                "getTerrainHeightASL": lambda _p: 0.0,
                "__EFUNC__weather_getBiomeAtPosition": biome,
                "__EFUNC__atmos_getLocalWind": wind,
                "__FUNC__mapBiomeColor": lambda _code: [
                    [0.45, 0.75, 0.35, 0.35],
                    "Temperate",
                ],
                "__FUNC__mapWindArrow": lambda wind_vec, length: [
                    [-50.0, 0.0],
                    [50.0, 0.0],
                ],
            },
        )
        return plan, calls

    def test_returns_cells_arrows_and_cell_size(self):
        plan, _calls = self._run([0, 0, 800, 600])
        biome_cells, wind_arrows, cell_w, cell_h = plan
        self.assertEqual(len(biome_cells), 8 * 6)
        self.assertEqual(len(wind_arrows), 6 * 5)
        self.assertTrue(_close(cell_w, 100.0))
        self.assertTrue(_close(cell_h, 100.0))

    def test_every_cell_samples_the_real_biome_kernel(self):
        plan, calls = self._run([0, 0, 800, 600])
        self.assertEqual(len(calls["biome"]), 8 * 6)
        self.assertEqual(len(calls["wind"]), 6 * 5)
        # Each sample carries a real position (x, y, z).
        self.assertEqual(len(calls["biome"][0]), 3)

    def test_a_short_rect_yields_an_empty_plan(self):
        plan = run_sqf(FIELD_PLAN, [[0, 0, 1]], {})
        self.assertEqual(plan, [[], [], 0, 0])


class TestWiring(unittest.TestCase):
    """The kernels are registered, the settings declared, the hook reused."""

    def test_prep_registers_the_overlay_kernels(self):
        for name in (
            "mapBiomeColor",
            "mapClickQuery",
            "mapDeclinationRose",
            "mapFieldPlan",
            "mapOverlayDraw",
            "mapStateReadout",
            "mapWindArrow",
        ):
            with self.subTest(name=name):
                self.assertIn(f"PREPS(hud,{name});", PREP_SRC)

    def test_the_master_setting_is_registered_default_off(self):
        self.assertIn(
            'AEE_SETTING_CHECKBOX(mapOverlayEnabled,"AEE HUD","Displays",false)',
            SETTINGS_SRC,
        )

    def test_the_layer_settings_are_registered(self):
        for name in (
            "mapBiomeLayer",
            "mapWindLayer",
            "mapDeclinationRose",
            "mapClickQuery",
        ):
            with self.subTest(name=name):
                self.assertIn(
                    f'AEE_SETTING_CHECKBOX({name},"AEE HUD","Displays",true)',
                    SETTINGS_SRC,
                )

    def test_the_stringtable_keys_exist(self):
        for name in (
            "mapOverlayEnabled",
            "mapBiomeLayer",
            "mapWindLayer",
            "mapDeclinationRose",
            "mapClickQuery",
        ):
            with self.subTest(name=name):
                self.assertIn(f"STR_AEE_Cartography_{name}_Name", STRINGTABLE_SRC)
                self.assertIn(
                    f"STR_AEE_Cartography_{name}_Description", STRINGTABLE_SRC
                )

    def test_the_overlay_draws_from_the_existing_draw_hook(self):
        # One rendering path: the Draw handler calls the overlay function.
        self.assertIn("call FUNC(mapOverlayDraw)", DRAW_SRC)

    def test_the_overlay_does_not_register_its_own_draw_handler(self):
        # Red-before: a second Draw handler would be a second path.
        self.assertNotIn('ctrlAddEventHandler ["Draw"', OVERLAY_SRC)

    def test_the_click_query_is_installed_at_post_init(self):
        self.assertIn("call FUNC(mapClickQuery)", POSTINIT_SRC)

    def test_the_click_query_uses_the_stackable_event(self):
        # The recommended replacement for the global onMapSingleClick.
        self.assertIn('addMissionEventHandler ["MapSingleClick"', CLICK_SRC)

    def test_the_new_cross_addon_dependencies_are_declared(self):
        for dep in ("aee_core", "aee_weather", "aee_atmos", "aee_material"):
            with self.subTest(dep=dep):
                self.assertIn(f'"{dep}"', CONFIG_SRC)

    def test_the_overlay_samples_only_real_per_position_kernels(self):
        # The layers are grounded: biome and local wind, both per position.
        self.assertIn(
            "EFUNC(weather,getBiomeAtPosition)",
            (HUD / "fnc_mapFieldPlan.sqf").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "EFUNC(atmos,getLocalWind)",
            (HUD / "fnc_mapFieldPlan.sqf").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
