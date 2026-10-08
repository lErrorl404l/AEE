#!/usr/bin/env python3
"""AEE terrain and map-feature symbol tests.

Locks the terrain symbol registry, the location and object config re-declares,
the map colour palette, the display reconciliation, the real-image provenance
and the texture set.  The textures are real public-domain drawings (FM 21-31,
USGS), so the provenance guard is part of the contract.

Run: python3 -m unittest tools.tests.test_terrain -v
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

OPTICS = REPO / "addons" / "optics"
TERRAIN = OPTICS / "data" / "terrain"
SRC = TERRAIN / "src"
TABLE_JSON = REPO / "data" / "symbology" / "terrain_symbols.json"
MANIFEST_JSON = REPO / "data" / "symbology" / "terrain_sources.json"
TABLE_SQF = OPTICS / "data" / "terrain_symbols.sqf"
LOC_HPP = OPTICS / "config_locationtypes.hpp"
OBJ_HPP = OPTICS / "config_mapicons.hpp"
COL_HPP = OPTICS / "config_mapcolors.hpp"
DISP_HPP = OPTICS / "config_mapdisplays.hpp"
CUR_HPP = OPTICS / "config_curator.hpp"
CONFIG_SRC = (OPTICS / "config.cpp").read_text(encoding="utf-8")
CUR_SRC = CUR_HPP.read_text(encoding="utf-8")
PREINIT_SRC = (OPTICS / "XEH_preInit.sqf").read_text(encoding="utf-8")
PREP_SRC = (OPTICS / "XEH_PREP.hpp").read_text(encoding="utf-8")
LOC_SRC = LOC_HPP.read_text(encoding="utf-8")
OBJ_SRC = OBJ_HPP.read_text(encoding="utf-8")
COL_SRC = COL_HPP.read_text(encoding="utf-8")
DISP_SRC = DISP_HPP.read_text(encoding="utf-8")
RUN_TESTS_SRC = (REPO / "tools" / "run_tests.py").read_text(encoding="utf-8")
TABLE = json.loads(TABLE_JSON.read_text(encoding="utf-8"))
MANIFEST = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))

AEE_PREFIX = "\\z\\aee\\addons\\optics\\data\\terrain\\"
LOCATION_CLASSES = {row["class"] for row in TABLE["locations"]}
OBJECT_CLASSES = {row["class"] for row in TABLE["objects"]}
ICON_LOCATION_CLASSES = {
    row["class"] for row in TABLE["locations"] if row.get("symbol")
}
REFERENCED = []
for _section in ("locations", "objects"):
    for _row in TABLE[_section]:
        if _row.get("symbol") and _row["symbol"] not in REFERENCED:
            REFERENCED.append(_row["symbol"])

FORBIDDEN_PROVENANCE = (
    "Agent:",
    "opencode",
    "claude",
    "anthropic",
    "openai",
    "deepseek",
    "hephaestus",
)


def classes_in(text: str) -> set[str]:
    return set(re.findall(r"class\s+(\w+)\s*(?::[^{]*)?\{", text))


def colour_of(text: str, field: str) -> list[float] | None:
    m = re.search(rf"{re.escape(field)}\[\]\s*=\s*\{{([^}}]*)\}}", text)
    if not m:
        return None
    return [float(x) for x in m.group(1).split(",")]


class TestTerrainTable(unittest.TestCase):
    def test_every_engine_location_class_has_a_row(self):
        self.assertEqual(len(LOCATION_CLASSES), 25)

    def test_every_engine_object_class_has_a_row(self):
        self.assertEqual(len(OBJECT_CLASSES), 26)

    def test_every_location_row_has_category_colour_size_font(self):
        for row in TABLE["locations"]:
            self.assertIn("category", row, row["class"])
            self.assertEqual(len(row["colour"]), 4, row["class"])
            self.assertIn("size", row, row["class"])
            self.assertIn("font", row, row["class"])
            self.assertIn("textSize", row, row["class"])

    def test_every_object_row_has_icon_category_colour_size(self):
        for row in TABLE["objects"]:
            self.assertIsNotNone(row["symbol"], row["class"])
            self.assertIn("category", row, row["class"])
            self.assertEqual(len(row["colour"]), 4, row["class"])
            self.assertIn("size", row, row["class"])

    def test_every_referenced_symbol_is_defined(self):
        ids = {row["id"] for row in TABLE["symbols"]}
        for symbol in REFERENCED:
            self.assertIn(symbol, ids)

    def test_generated_sqf_names_the_addon_variable(self):
        table_sqf = TABLE_SQF.read_text(encoding="utf-8")
        self.assertIn("GENERATED", table_sqf)


class TestTerrainLocationConfig(unittest.TestCase):
    def test_all_25_location_classes_are_declared(self):
        self.assertTrue(LOCATION_CLASSES.issubset(classes_in(LOC_SRC)))

    def test_the_eight_icon_classes_carry_an_aee_texture(self):
        expected = {
            "Hill": "hill",
            "ViewPoint": "monument",
            "RockArea": "rock",
            "BorderCrossing": "border_crossing",
            "VegetationBroadleaf": "deciduous",
            "VegetationFir": "coniferous",
            "VegetationPalm": "palm",
            "VegetationVineyard": "vineyard",
        }
        self.assertEqual(ICON_LOCATION_CLASSES, set(expected))
        for cls, symbol in expected.items():
            block = re.search(rf"class {cls} \{{(.*?)\n    \}}", LOC_SRC, re.DOTALL)
            self.assertIsNotNone(block, cls)
            self.assertIn(f"{AEE_PREFIX}{symbol}.paa", block.group(1))

    def test_a_name_class_carries_the_label_font(self):
        block = re.search(r"class Name \{(.*?)\n    \}", LOC_SRC, re.DOTALL)
        self.assertIsNotNone(block)
        self.assertIn('font = "AEEFont";', block.group(1))
        self.assertIn("textSize", block.group(1))

    def test_no_drawstyle_is_set(self):
        self.assertIsNone(re.search(r"drawStyle\s*=", LOC_SRC))


class TestTerrainObjectConfig(unittest.TestCase):
    def test_all_26_object_classes_are_declared(self):
        self.assertTrue(OBJECT_CLASSES.issubset(classes_in(OBJ_SRC)))

    def test_every_object_icon_is_in_the_aee_terrain_prefix(self):
        icons = re.findall(r'icon\s*=\s*"([^"]+)"', OBJ_SRC)
        self.assertEqual(len(icons), 26)
        for icon in icons:
            self.assertTrue(icon.startswith(AEE_PREFIX), icon)


class TestTerrainTextures(unittest.TestCase):
    def test_every_referenced_texture_exists(self):
        for symbol in REFERENCED:
            self.assertTrue((TERRAIN / f"{symbol}.paa").is_file(), symbol)

    def test_no_orphan_texture(self):
        produced = {p.stem for p in TERRAIN.glob("*.paa")}
        self.assertEqual(produced, set(REFERENCED))

    def test_every_referenced_symbol_has_a_source_image(self):
        entries = {e["id"]: e for e in MANIFEST["entries"]}
        for symbol in REFERENCED:
            self.assertIn(symbol, entries)
            self.assertTrue((SRC / entries[symbol]["file"]).is_file(), symbol)

    def test_manifest_provenance_is_an_open_source(self):
        for entry in MANIFEST["entries"]:
            self.assertTrue(entry.get("source", "").strip(), entry["id"])
            licence = entry.get("licence", "").lower()
            self.assertTrue(
                "public domain" in licence or "cc by" in licence, entry["id"]
            )
            self.assertIn(entry.get("grade"), ("sourced", "derived"), entry["id"])

    def test_every_register_symbol_names_a_dgiwg_symbol_and_concept(self):
        entries = {e["id"]: e for e in MANIFEST["entries"]}
        for symbol in REFERENCED:
            entry = entries[symbol]
            if entry.get("dgiwg"):
                self.assertRegex(entry["dgiwg"], r"^SO_\d{4}$", symbol)
                self.assertTrue(entry.get("concept", "").strip(), symbol)
                self.assertTrue((SRC / entry["svg"]).is_file(), symbol)

    def test_every_non_register_symbol_is_recorded(self):
        entries = {e["id"]: e for e in MANIFEST["entries"]}
        recorded = {e["id"] for e in MANIFEST.get("no_register_source", [])}
        for symbol in REFERENCED:
            if not entries[symbol].get("dgiwg"):
                self.assertIn(symbol, recorded)

    def test_no_plate_crop_source_remains(self):
        for entry in MANIFEST["entries"]:
            self.assertNotIn("fm 21-31", entry.get("source", "").lower(), entry["id"])

    def test_every_source_image_is_a_svg_render(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO / "tools" / "gen_terrain_symbols.py"),
                "--verify-svg",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class TestTerrainAlpha(unittest.TestCase):
    def test_every_texture_is_a_transparent_mask(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO / "tools" / "validation" / "validate_terrain_alpha.py"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class TestTerrainMapColours(unittest.TestCase):
    def test_every_named_colour_matches_the_register(self):
        for field, value in TABLE["map_colours"].items():
            if field == "note":
                continue
            self.assertEqual(colour_of(COL_SRC, field), value, field)

    def test_relief_is_brown(self):
        levels = colour_of(COL_SRC, "colorLevels")
        self.assertIsNotNone(levels)
        self.assertGreater(levels[0], levels[2])

    def test_water_is_blue(self):
        sea = colour_of(COL_SRC, "colorSea")
        self.assertGreater(sea[2], sea[0])

    def test_vegetation_is_green(self):
        forest = colour_of(COL_SRC, "colorForest")
        self.assertGreater(forest[1], forest[0])

    def test_the_satellite_alpha_lever_is_present(self):
        self.assertRegex(COL_SRC, r"maxSatelliteAlpha\s*=\s*0?\.\d+")

    def test_the_contour_interval_label_is_shown(self):
        self.assertRegex(COL_SRC, r"showCountourInterval\s*=\s*1")

    def test_no_contour_interval_field_exists(self):
        for path in OPTICS.rglob("*.hpp"):
            self.assertNotIn(
                "contourInterval", path.read_text(encoding="utf-8"), path.name
            )


class TestTerrainDisplays(unittest.TestCase):
    def test_the_strategic_map_is_a_separate_target(self):
        self.assertIn("class RscDisplayStrategicMap", DISP_SRC)
        self.assertIn("class controlsBackground", DISP_SRC)
        self.assertIn("class Map", DISP_SRC)

    def test_the_eden_map_is_a_separate_target(self):
        self.assertIn("class ctrlMap", DISP_SRC)
        self.assertIn("class ctrlDefault;", DISP_SRC)

    def test_the_eden_map_carries_the_font_and_the_levers(self):
        m = re.search(r"class ctrlMap[^{]*\{(.*)", DISP_SRC, re.DOTALL)
        self.assertIsNotNone(m)
        block = m.group(1)
        self.assertIn('fontGrid = "AEEFont";', block)
        self.assertIn('fontNames = "AEEFont";', block)
        self.assertIn("maxSatelliteAlpha", block)
        self.assertIn("showCountourInterval", block)


class TestTerrainCurator(unittest.TestCase):
    def test_the_curator_draw_group_is_re_declared(self):
        self.assertIn("class CfgCurator", CUR_SRC)
        self.assertIn("class DrawGroup", CUR_SRC)

    def test_every_side_texture_carries_a_real_nato_symbol(self):
        for side in ("West", "East", "Guer", "Civilian", "Unknown"):
            m = re.search(rf"texture{side}\s*=\s*\"([^\"]+)\"", CUR_SRC)
            self.assertIsNotNone(m, side)
            self.assertIn(".paa", m.group(1))

    def test_the_unknown_side_uses_the_unknown_affiliation_symbol(self):
        m = re.search(r'textureUnknown\s*=\s*"([^"]+)"', CUR_SRC)
        self.assertIn("AEE_u_", m.group(1))

    def test_the_civilian_side_uses_the_civilian_symbol(self):
        m = re.search(r'textureCivilian\s*=\s*"([^"]+)"', CUR_SRC)
        self.assertIn("c_unknown", m.group(1))

    def test_the_3d_and_2d_groups_are_reconciled(self):
        for group in ("3D", "2D"):
            self.assertIn(f"class {group}", CUR_SRC)


class TestTerrainWiring(unittest.TestCase):
    def test_the_registry_is_loaded_at_startup(self):
        self.assertIn("aee_optics_terrainTables", PREINIT_SRC)

    def test_no_hand_drawn_terrain_kernel_remains(self):
        self.assertNotIn("terrainIcon", PREP_SRC)
        self.assertFalse((OPTICS / "functions" / "terrain").exists())

    def test_the_map_font_is_wired(self):
        self.assertIn('fontNames = "AEEFont";', CONFIG_SRC)

    def test_the_app6_marker_surfaces_are_untouched(self):
        self.assertIn('#include "config_markers.hpp"', CONFIG_SRC)
        self.assertIn("class CfgMarkerClasses", CONFIG_SRC)

    def test_no_agent_provenance(self):
        for path in (LOC_HPP, OBJ_HPP, COL_HPP, DISP_HPP, TABLE_JSON, MANIFEST_JSON):
            text = path.read_text(encoding="utf-8")
            for bad in FORBIDDEN_PROVENANCE:
                self.assertNotIn(bad, text, f"{path.name}: {bad}")


class TestSuiteRegistration(unittest.TestCase):
    def test_the_suite_is_registered(self):
        self.assertIn("tools/tests/test_terrain.py", RUN_TESTS_SRC)


if __name__ == "__main__":
    unittest.main()
