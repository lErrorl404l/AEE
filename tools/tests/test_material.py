"""Material classification mirror (issue #96).

Mirrors the material addon:
  fnc_classifyBySurfaceType  -> classify_surface_type()   #gdt* -> class
  fnc_getSurfaceMaterial     -> classify_surface_id()    bisurf/CfgSurfaces
  fnc_initMaterialCache      -> the vanilla bisurf table
  fnc_handleHitPart          -> learning per object class

The fallback chain (fastest -> slowest):
  1. material cache (preloaded vanilla bisurf paths)
  2. CfgSurfaces class -> soundEnviron/soundHit keyword
  3. preprocessFile bisurf text -> soundHit keyword
  4. default "ground"

The vanilla bisurf paths were verified against the installed game
files (data_f.pbo, inspected with armake, 2026-09-19).
"""

import re
import unittest

MATERIAL_CLASSES = {
    "ground",
    "rock",
    "wood",
    "concrete",
    "metal",
    "glass",
    "water",
    "vegetation",
}

# Subset of the vanilla cache for tests (full table lives in SQF).
VANILLA_CACHE = {
    "a3\\data_f\\penetration\\armour.bisurf": "metal",
    "a3\\data_f\\penetration\\concrete.bisurf": "concrete",
    "a3\\data_f\\penetration\\wood.bisurf": "wood",
    "a3\\data_f\\penetration\\glass.bisurf": "glass",
    "a3\\data_f\\penetration\\metal.bisurf": "metal",
    "a3\\data_f\\penetration\\water.bisurf": "water",
    "a3\\data_f\\penetration\\foliage.bisurf": "vegetation",
    "a3\\data_f\\penetration\\default.bisurf": "ground",
}

# Real bisurf content (soundHit values extracted from data_f.pbo,
# 2026-09-19).
BISURF_CONTENT = {
    "concrete": "soundHit = Concrete;",
    "armour": "soundHit = Metal;",
    "wood": "soundHit = Wood;",
    "glass": "soundHit = Glass;",
    "metal": "soundHit = Metal;",
    "water": "soundHit = Water;",
    "foliage": "soundHit = Foliage;",
}


def classify_surface_type(surface):
    """Mirror of fnc_classifyBySurfaceType.sqf."""
    s = surface.lower()
    if s in ("#gdtsnow", "#gdtice", "#gdtglacier", "#gdttundra"):
        return "ground"
    if s in ("#gdtrock", "#gdtmountain", "#gdtgravel"):
        return "rock"
    if s in ("#gdtdesert", "#gdtdunes", "#gdtsand", "#gdtprairie"):
        return "ground"
    if s in (
        "#gdtgrass",
        "#gdtgrassland",
        "#gdtforest",
        "#gdtjungle",
        "#gdtrainforest",
        "#gdtconiferous",
        "#gdtcrop",
        "#gdtfield",
        "#gdtvineyard",
        "#gdtorchard",
    ):
        return "vegetation"
    if s in ("#gdtswamp", "#gdtmarsh"):
        return "water"
    return "ground"


def classify_surface_id(surf_id, cache=None):
    """Mirror of fnc_getSurfaceMaterial.sqf."""
    if not surf_id:
        return "ground"
    if cache is None:
        cache = {}
    if surf_id in cache:
        return cache[surf_id]

    # CfgSurfaces or bisurf text: extract the soundHit keyword.
    keyword = ""
    if surf_id.endswith(".bisurf"):
        # Simulate preprocessFile: read the stored content, strip
        # non-alphanumerics, take the soundHit value.
        key = surf_id.split("\\")[-1].replace(".bisurf", "")
        text = BISURF_CONTENT.get(key, "")
        stripped = re.sub(r"[^a-z0-9]", "", text.lower())
        idx = stripped.find("soundhit")
        if idx >= 0:
            keyword = stripped[idx + 8 : idx + 20]
    else:
        keyword = surf_id.lower()

    if "metal" in keyword:
        material = "metal"
    elif "concrete" in keyword:
        material = "concrete"
    elif "wood" in keyword:
        material = "wood"
    elif "glass" in keyword:
        material = "glass"
    elif "granite" in keyword or "rock" in keyword or "gravel" in keyword:
        material = "rock"
    elif "water" in keyword:
        material = "water"
    elif "foliage" in keyword or "grass" in keyword or "hay" in keyword:
        material = "vegetation"
    else:
        material = "ground"
    cache[surf_id] = material
    return material


class TestClassifyBySurfaceType(unittest.TestCase):
    """Layer 1 - terrain taxonomy."""

    def test_vegetation_classes(self):
        for s in (
            "#gdtgrass",
            "#gdtforest",
            "#gdtjungle",
            "#gdtcrop",
            "#gdtvineyard",
            "#gdtorchard",
        ):
            self.assertEqual(classify_surface_type(s), "vegetation", s)

    def test_rock_classes(self):
        for s in ("#gdtrock", "#gdtmountain", "#gdtgravel"):
            self.assertEqual(classify_surface_type(s), "rock", s)

    def test_ground_classes(self):
        for s in ("#gdtsnow", "#gdtdesert", "#gdtsand", "#gdtice", "#gdttundra"):
            self.assertEqual(classify_surface_type(s), "ground", s)

    def test_wetland_is_water(self):
        self.assertEqual(classify_surface_type("#gdtswamp"), "water")
        self.assertEqual(classify_surface_type("#gdtmarsh"), "water")

    def test_unknown_falls_to_ground(self):
        self.assertEqual(classify_surface_type("#gdtunknown_thing"), "ground")

    def test_case_insensitive(self):
        self.assertEqual(classify_surface_type("#GDTGRASS"), "vegetation")


class TestGetSurfaceMaterial(unittest.TestCase):
    """Layer 2/3 - bisurf + CfgSurfaces classification."""

    def test_vanilla_cache_hits(self):
        for path, expected in VANILLA_CACHE.items():
            self.assertEqual(
                classify_surface_id(path, VANILLA_CACHE.copy()),
                expected,
                path,
            )

    def test_bisurf_content_classification(self):
        # The bisurf text carries soundHit = Concrete / Metal.
        self.assertEqual(
            classify_surface_id("a3\\data_f\\penetration\\concrete.bisurf"),
            "concrete",
        )
        self.assertEqual(
            classify_surface_id("a3\\data_f\\penetration\\armour.bisurf"),
            "metal",
        )

    def test_learned_result_is_cached(self):
        cache = {}
        classify_surface_id("a3\\data_f\\penetration\\wood.bisurf", cache)
        classify_surface_id("a3\\data_f\\penetration\\wood.bisurf", cache)
        self.assertEqual(cache["a3\\data_f\\penetration\\wood.bisurf"], "wood")

    def test_empty_returns_ground(self):
        self.assertEqual(classify_surface_id(""), "ground")

    def test_all_results_are_valid_classes(self):
        for path in VANILLA_CACHE:
            self.assertIn(
                classify_surface_id(path, VANILLA_CACHE.copy()),
                MATERIAL_CLASSES,
            )


if __name__ == "__main__":
    unittest.main()
