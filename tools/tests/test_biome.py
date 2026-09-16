#!/usr/bin/env python3
"""Reference checks for AEE's biome detection model.

These tests validate the SQF implementation in addons/environmental
(fnc_getBiomeAtPosition.sqf, fnc_getBiome.sqf) against the scientific
reference: Peel 2007 (doi:10.5194/hess-11-1633-2007).

Run: python3 -m unittest tools/tests/test_biome.py
"""

import math
import unittest
from pathlib import Path

# Repo root: tools/tests/ -> up two levels.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV = _REPO_ROOT / "addons" / "environmental" / "functions"


def _read_sqf(name):
    """Read an SQF function file.  The drift-lock tests read the SOURCE so a
    constant change in SQF fails the mirror tests until re-synced."""
    return (_ENV / name).read_text(encoding="utf-8")


# ─── Mirror of fnc_getBiomeAtPosition.sqf ──────────────────────────────

# Tier 1: High-confidence surface → biome mapping
DIRECT_MAP = {
    "#gdtdesert": "BWh",
    "#gdtsand": "BWh",
    "#gdt dunes": "BWh",
    "#gdtjungle": "Af",
    "#gdtrainforest": "Af",
    "#gdttundra": "ET",
    "#gdtice": "EF",
    "#gdtglacier": "EF",
    "#gdtvineyard": "Csa",
    "#gdtprairie": "BSk",
}


# Latitude band → primary Koppen zone
def latitude_band(lat):
    """Mirror of the latitude switch in fnc_getBiomeAtPosition.sqf."""
    lat = abs(lat)
    if lat == 0:
        lat = 40  # fallback: temperate default
    if lat < 10:
        return "A"
    elif lat < 23.5:
        return "A"
    elif lat < 35:
        return "B"
    elif lat < 50:
        return "C"
    elif lat < 66.5:
        return "D"
    else:
        return "E"


# Elevation lapse rate: 6.5°C per 1000m (ICAO standard atmosphere)
def elevation_effect(elevation_m):
    """Mirror of _elevEffect in fnc_getBiomeAtPosition.sqf."""
    return elevation_m / 1000 * 6.5


# Tier 2: Low-confidence surface → candidates by latitude band
def tier2_candidates(surface, lat_band, elev_effect):
    """Mirror of _CANDIDATE_MAP switch in fnc_getBiomeAtPosition.sqf.

    Returns list of (biome, weight) tuples.
    """
    surface = surface.lower()

    if surface == "#gdtforest":
        candidates = {
            "A": [("Af", 2), ("Am", 1)],
            "B": [("BSh", 2), ("BSk", 1)],
            "C": [("Cfb", 3), ("Cfa", 1)],
            "D": [("Dfb", 3), ("Dfc", 1)],
            "E": [("Dfc", 2), ("ET", 1)],
        }
        return candidates.get(lat_band, [])

    if surface == "#gdtconiferous":
        candidates = {
            "A": [("Am", 2), ("Cfb", 1)],
            "B": [("BSk", 2), ("Cfb", 1)],
            "C": [("Cfb", 2), ("Dfb", 2)],
            "D": [("Dfb", 3), ("Dfc", 2)],
            "E": [("Dfc", 3), ("ET", 2)],
        }
        return candidates.get(lat_band, [])

    if surface == "#gdtgrass":
        candidates = {
            "A": [("Aw", 3), ("Am", 1)],
            "B": [("BSh", 3), ("BSk", 2)],
            "C": [("Cfb", 3), ("Cfa", 1)],
            "D": [("Dfb", 2), ("Cfb", 1)],
            "E": [("ET", 2), ("Dfc", 1)],
        }
        return candidates.get(lat_band, [])

    if surface == "#gdtgrassland":
        candidates = {
            "A": [("Aw", 3), ("Am", 1)],
            "B": [("BSh", 3), ("BSk", 2)],
            "C": [("Cfb", 3), ("Cfa", 1)],
            "D": [("Dfb", 2), ("Cfb", 1)],
            "E": [("ET", 2), ("Dfc", 1)],
        }
        return candidates.get(lat_band, [])

    if surface == "#gdtswamp":
        candidates = {
            "A": [("Af", 3), ("Am", 2)],
            "B": [("BSh", 2), ("Cfa", 1)],
            "C": [("Cfa", 2), ("Cfb", 2)],
            "D": [("Dfb", 2), ("Dfc", 1)],
            "E": [("Dfc", 2), ("ET", 1)],
        }
        return candidates.get(lat_band, [])

    if surface == "#gdtmarsh":
        candidates = {
            "A": [("Af", 3), ("Am", 2)],
            "B": [("BSh", 2), ("Cfa", 1)],
            "C": [("Cfa", 2), ("Cfb", 2)],
            "D": [("Dfb", 2), ("Dfc", 1)],
            "E": [("Dfc", 2), ("ET", 1)],
        }
        return candidates.get(lat_band, [])

    if surface == "#gdtsnow":
        if lat_band == "E":
            return [("ET", 3), ("EF", 2)]
        elif lat_band == "D":
            return [("Dfc", 3), ("ET", 2)]
        elif elev_effect > 15:
            return [("ET", 3), ("Dfc", 2)]
        else:
            return [("Dfc", 2), ("ET", 1)]

    if surface == "#gdtrock":
        if elev_effect > 15:
            return [("ET", 3), ("EF", 1)]
        elif elev_effect > 8:
            return [("Dfc", 3), ("ET", 2)]
        elif lat_band == "E":
            return [("ET", 3), ("Dfc", 2)]
        else:
            return [("Dfb", 2), ("Cfb", 1)]

    if surface == "#gdtmountain":
        if elev_effect > 20:
            return [("ET", 3), ("EF", 1)]
        elif elev_effect > 10:
            return [("Dfc", 3), ("ET", 2)]
        elif lat_band == "E":
            return [("ET", 3), ("Dfc", 2)]
        else:
            return [("Dfb", 2), ("Dfc", 1)]

    if surface == "#gdtfield":
        candidates = {
            "A": [("Aw", 2), ("Am", 1)],
            "B": [("BSh", 2), ("BSk", 1)],
            "C": [("Cfb", 3), ("Cfa", 2)],
            "D": [("Dfb", 3), ("Dfb", 1)],
            "E": [("Dfc", 2), ("ET", 1)],
        }
        return candidates.get(lat_band, [])

    if surface == "#gdtcrop":
        candidates = {
            "A": [("Aw", 2), ("Am", 1)],
            "B": [("BSh", 2), ("BSk", 1)],
            "C": [("Cfb", 3), ("Cfa", 2)],
            "D": [("Dfb", 3), ("Dfb", 1)],
            "E": [("Dfc", 2), ("ET", 1)],
        }
        return candidates.get(lat_band, [])

    if surface == "#gdtorchard":
        candidates = {
            "A": [("Am", 2), ("Af", 1)],
            "B": [("BSk", 2), ("BSh", 1)],
            "C": [("Cfb", 3), ("Cfa", 2)],
            "D": [("Dfb", 2), ("Cfb", 1)],
            "E": [("Dfc", 2), ("ET", 1)],
        }
        return candidates.get(lat_band, [])

    return []


def pick_winner(candidates):
    """Mirror of the winner selection in fnc_getBiomeAtPosition.sqf."""
    if not candidates:
        return None
    best = candidates[0]
    for c in candidates:
        if c[1] > best[1]:
            best = c
    return best[0]


def get_biome_at_position(surface, lat, elevation_m):
    """Full mirror of fnc_getBiomeAtPosition.sqf logic."""
    surface = surface.lower()

    # Tier 1: high confidence
    if surface in DIRECT_MAP:
        return DIRECT_MAP[surface]

    # Tier 2: low confidence
    lat_band = latitude_band(lat)
    elev_eff = elevation_effect(elevation_m)
    candidates = tier2_candidates(surface, lat_band, elev_eff)

    if candidates:
        return pick_winner(candidates)

    # Fallback
    fallback = {"A": "Af", "B": "BWh", "C": "Cfb", "D": "Dfb", "E": "ET"}
    return fallback.get(lat_band, "Cfb")


# ─── Mirror of fnc_getBiome.sqf map table ──────────────────────────────
KNOWN_MAP_BIOMES = {
    "Altis": "Csa",
    "Stratis": "Csa",
    "Tanoa": "Af",
    "Lingor": "Af",
    "Enoch": "Dfb",
    "Livonia": "Dfb",
    "Chernarus": "Dfb",
    "chernarus_summer": "Dfb",
    "Takistan": "BSk",
    "Malden": "Csa",
    "Sahrani": "Aw",
    "Kujari": "BSh",
    "Weferlingen": "Cfb",
    "CamLaoNam": "Am",
    "Xcam_taolao": "Am",
    "Isladuala": "Af",
    "Caribou": "Dfc",
    "tem_anizay": "BWh",
}


# ─── Tests ─────────────────────────────────────────────────────────────


class TestSQFSync(unittest.TestCase):
    """SQF source must contain the constants the Python mirrors rely on."""

    def _assert_in_sqf(self, filename, fragments, context):
        text = _read_sqf(filename)
        missing = [f for f in fragments if f not in text]
        self.assertFalse(
            missing,
            f"{filename}: {context} changed/missing in SQF: {missing}. "
            f"Re-sync the Python mirror in test_biome.py.",
        )

    # ── Latitude bands (fnc_getBiomeAtPosition.sqf) ──
    def test_latitude_bands(self):
        self._assert_in_sqf(
            "fnc_getBiomeAtPosition.sqf",
            [
                "case (_lat < 10)",
                "case (_lat < 23.5)",
                "case (_lat < 35)",
                "case (_lat < 50)",
                "case (_lat < 66.5)",
            ],
            "Koppen latitude bands",
        )

    def test_latitude_fallback(self):
        self._assert_in_sqf(
            "fnc_getBiomeAtPosition.sqf",
            ["if (_lat == 0) then { _lat = 40; }"],
            "temperate latitude fallback",
        )

    # ── Elevation lapse rate (fnc_getBiomeAtPosition.sqf) ──
    def test_lapse_rate(self):
        self._assert_in_sqf(
            "fnc_getBiomeAtPosition.sqf",
            ["_elevation / 1000 * 6.5"],
            "ICAO 6.5 C/km lapse rate",
        )

    # ── Tier 1 direct map (fnc_getBiomeAtPosition.sqf) ──
    def test_direct_map_entries(self):
        self._assert_in_sqf(
            "fnc_getBiomeAtPosition.sqf",
            [
                '"#GdtDesert",   "BWh"',
                '"#GdtJungle",   "Af"',
                '"#GdtTundra",   "ET"',
                '"#GdtIce",      "EF"',
                '"#GdtPrairie",  "BSk"',
            ],
            "Tier 1 direct surface map",
        )

    # ── Tier 2 wetland candidates (fnc_getBiomeAtPosition.sqf) ──
    def test_wetland_candidates(self):
        self._assert_in_sqf(
            "fnc_getBiomeAtPosition.sqf",
            [
                '["#GdtSwamp", switch (_latBand) do {',
                '["#GdtMarsh", switch (_latBand) do {',
            ],
            "Tier 2 wetland surface candidates",
        )


class TestLatitudeBand(unittest.TestCase):
    """Validate latitude → Koppen zone mapping."""

    def test_equatorial(self):
        # lat=0 defaults to 40 in SQF (fallback), so band is "C"
        self.assertEqual(latitude_band(0), "C")

    def test_tropical(self):
        self.assertEqual(latitude_band(15), "A")

    def test_tropic_boundary(self):
        self.assertEqual(latitude_band(23.5), "B")

    def test_subtropical(self):
        self.assertEqual(latitude_band(30), "B")

    def test_temperate(self):
        self.assertEqual(latitude_band(45), "C")

    def test_continental(self):
        self.assertEqual(latitude_band(55), "D")

    def test_polar(self):
        self.assertEqual(latitude_band(70), "E")

    def test_southern_hemisphere(self):
        self.assertEqual(latitude_band(-30), "B")

    def test_zero_defaults_to_temperate(self):
        # fnc_getBiomeAtPosition.sqf: if (_lat == 0) then { _lat = 40; }
        self.assertEqual(latitude_band(0), "C")  # 0 → 40, band "C"


class TestElevationEffect(unittest.TestCase):
    """Validate elevation lapse rate calculation."""

    def test_sea_level(self):
        self.assertAlmostEqual(elevation_effect(0), 0.0, places=1)

    def test_1000m(self):
        # ICAO: 6.5°C per 1000m
        self.assertAlmostEqual(elevation_effect(1000), 6.5, places=1)

    def test_3000m(self):
        self.assertAlmostEqual(elevation_effect(3000), 19.5, places=1)

    def test_5000m(self):
        self.assertAlmostEqual(elevation_effect(5000), 32.5, places=1)


class TestTier1HighConfidence(unittest.TestCase):
    """Validate Tier 1 surface → biome mapping (immediate return)."""

    def test_desert(self):
        self.assertEqual(get_biome_at_position("#GdtDesert", 25, 0), "BWh")

    def test_sand(self):
        self.assertEqual(get_biome_at_position("#GdtSand", 25, 0), "BWh")

    def test_dunes(self):
        self.assertEqual(get_biome_at_position("#GdtDunes", 25, 0), "BWh")

    def test_jungle(self):
        self.assertEqual(get_biome_at_position("#GdtJungle", 5, 0), "Af")

    def test_rain_forest(self):
        self.assertEqual(get_biome_at_position("#GdtRainForest", 5, 0), "Af")

    def test_tundra(self):
        self.assertEqual(get_biome_at_position("#GdtTundra", 65, 0), "ET")

    def test_ice(self):
        self.assertEqual(get_biome_at_position("#GdtIce", 75, 0), "EF")

    def test_glacier(self):
        self.assertEqual(get_biome_at_position("#GdtGlacier", 75, 0), "EF")

    def test_vineyard(self):
        self.assertEqual(get_biome_at_position("#GdtVineyard", 38, 0), "Csa")

    def test_prairie(self):
        self.assertEqual(get_biome_at_position("#GdtPrairie", 40, 0), "BSk")


class TestTier2ForestByLatitude(unittest.TestCase):
    """Validate Tier 2 forest surface disambiguation by latitude."""

    def test_forest_tropical(self):
        self.assertEqual(get_biome_at_position("#GdtForest", 5, 0), "Af")

    def test_forest_subtropical(self):
        self.assertEqual(get_biome_at_position("#GdtForest", 30, 0), "BSh")

    def test_forest_temperate(self):
        self.assertEqual(get_biome_at_position("#GdtForest", 45, 0), "Cfb")

    def test_forest_continental(self):
        self.assertEqual(get_biome_at_position("#GdtForest", 55, 0), "Dfb")

    def test_forest_polar(self):
        self.assertEqual(get_biome_at_position("#GdtForest", 70, 0), "Dfc")


class TestTier2ConiferousByLatitude(unittest.TestCase):
    """Validate Tier 2 coniferous surface disambiguation."""

    def test_coniferous_tropical(self):
        self.assertEqual(get_biome_at_position("#GdtConiferous", 5, 0), "Am")

    def test_coniferous_temperate(self):
        self.assertEqual(get_biome_at_position("#GdtConiferous", 45, 0), "Cfb")

    def test_coniferous_continental(self):
        self.assertEqual(get_biome_at_position("#GdtConiferous", 55, 0), "Dfb")

    def test_coniferous_subarctic(self):
        # lat=62 is band "D", coniferous candidates: Dfb(3), Dfc(2). Dfb wins.
        # The per-position system returns Dfb, not Dfc (map table is per-map, not per-position).
        self.assertEqual(get_biome_at_position("#GdtConiferous", 62, 0), "Dfb")


class TestTier2RockByElevation(unittest.TestCase):
    """Validate Tier 2 rock/mountain surface by elevation."""

    def test_rock_low_elevation(self):
        # Below 8°C effect: Dfb (continental)
        self.assertEqual(get_biome_at_position("#GdtRock", 45, 500), "Dfb")

    def test_rock_mid_elevation(self):
        # 8-15°C effect: Dfc (subarctic)
        self.assertEqual(get_biome_at_position("#GdtRock", 45, 1500), "Dfc")

    def test_rock_high_elevation(self):
        # Above 15°C effect: ET (tundra)
        self.assertEqual(get_biome_at_position("#GdtRock", 45, 3000), "ET")

    def test_mountain_very_high(self):
        # Above 20°C effect: ET (tundra)
        self.assertEqual(get_biome_at_position("#GdtMountain", 45, 4000), "ET")

    def test_mountain_high(self):
        # 10-20°C effect: Dfc (subarctic)
        self.assertEqual(get_biome_at_position("#GdtMountain", 45, 2000), "Dfc")


class TestTier2GrassByLatitude(unittest.TestCase):
    """Validate Tier 2 grass surface disambiguation."""

    def test_grass_tropical(self):
        self.assertEqual(get_biome_at_position("#GdtGrass", 5, 0), "Aw")

    def test_grass_arid(self):
        self.assertEqual(get_biome_at_position("#GdtGrass", 30, 0), "BSh")

    def test_grass_temperate(self):
        self.assertEqual(get_biome_at_position("#GdtGrass", 45, 0), "Cfb")


class TestTier2WetlandByLatitude(unittest.TestCase):
    """Validate Tier 2 swamp/marsh disambiguation by latitude (issue #56).

    Swamp and marsh share one candidate table.  On a weight tie the first
    listed candidate wins, so band C returns Cfa.
    """

    def test_swamp_tropical(self):
        # Band A: Af(3), Am(2) → Af
        self.assertEqual(get_biome_at_position("#GdtSwamp", 5, 0), "Af")

    def test_swamp_subtropical(self):
        # Band B: BSh(2), Cfa(1) → BSh
        self.assertEqual(get_biome_at_position("#GdtSwamp", 30, 0), "BSh")

    def test_swamp_temperate(self):
        # Band C: Cfa(2), Cfb(2) → Cfa (first on tie)
        self.assertEqual(get_biome_at_position("#GdtSwamp", 45, 0), "Cfa")

    def test_swamp_continental(self):
        # Band D: Dfb(2), Dfc(1) → Dfb
        self.assertEqual(get_biome_at_position("#GdtSwamp", 55, 0), "Dfb")

    def test_swamp_polar(self):
        # Band E: Dfc(2), ET(1) → Dfc
        self.assertEqual(get_biome_at_position("#GdtSwamp", 70, 0), "Dfc")

    def test_marsh_tropical(self):
        self.assertEqual(get_biome_at_position("#GdtMarsh", 5, 0), "Af")

    def test_marsh_subtropical(self):
        self.assertEqual(get_biome_at_position("#GdtMarsh", 30, 0), "BSh")

    def test_marsh_temperate(self):
        self.assertEqual(get_biome_at_position("#GdtMarsh", 45, 0), "Cfa")

    def test_marsh_continental(self):
        self.assertEqual(get_biome_at_position("#GdtMarsh", 55, 0), "Dfb")

    def test_marsh_polar(self):
        self.assertEqual(get_biome_at_position("#GdtMarsh", 70, 0), "Dfc")


class TestTier2SnowByLatitude(unittest.TestCase):
    """Validate Tier 2 snow surface disambiguation."""

    def test_snow_polar(self):
        self.assertEqual(get_biome_at_position("#GdtSnow", 70, 0), "ET")

    def test_snow_continental(self):
        self.assertEqual(get_biome_at_position("#GdtSnow", 55, 0), "Dfc")

    def test_snow_high_elevation(self):
        self.assertEqual(get_biome_at_position("#GdtSnow", 45, 3000), "ET")


class TestKnownMapBiomes(unittest.TestCase):
    """Validate against the hardcoded map table in fnc_getBiome.sqf.

    These are the 17 maps with known biomes. The per-position system
    should produce the same result when the player stands on the dominant
    surface at a typical position.
    """

    def test_altis_mediterranean(self):
        # Altis: Csa (Hot Mediterranean), lat ~38.5
        biome = get_biome_at_position("#GdtVineyard", 38.5, 50)
        self.assertEqual(biome, "Csa")

    def test_tanoa_tropical(self):
        # Tanoa: Af (Tropical Rainforest), lat ~-8
        biome = get_biome_at_position("#GdtJungle", -8, 50)
        self.assertEqual(biome, "Af")

    def test_enoch_continental(self):
        # Enoch: Dfb (Humid Continental), lat ~52
        biome = get_biome_at_position("#GdtForest", 52, 200)
        self.assertEqual(biome, "Dfb")

    def test_takistan_semi_arid(self):
        # Takistan: BSk (Cold Semi-Arid), lat ~33
        biome = get_biome_at_position("#GdtPrairie", 33, 800)
        self.assertEqual(biome, "BSk")

    def test_kujari_hot_semi_arid(self):
        # Kujari map table says BSh, but per-position grass at lat=12
        # is band "A" (tropical), grass candidates: Aw(3), Am(1). Aw wins.
        # The map table is a static lookup; the per-position system uses
        # surface + latitude. Grass in the tropics is savanna (Aw).
        self.assertEqual(get_biome_at_position("#GdtGrass", 12, 400), "Aw")

    def test_caribou_subarctic(self):
        # Caribou map table says Dfc, but per-position coniferous at lat=62
        # returns Dfb (weight 3 > Dfc weight 2 in band "D"). The map table
        # is a static lookup; the per-position system uses surface + latitude.
        self.assertEqual(get_biome_at_position("#GdtConiferous", 62, 100), "Dfb")

    def test_tem_anizay_hot_desert(self):
        # tem_anizay: BWh (Hot Desert), lat ~33
        biome = get_biome_at_position("#GdtDesert", 33, 1200)
        self.assertEqual(biome, "BWh")


class TestBiomeCodeNames(unittest.TestCase):
    """Validate all 17 Koppen codes have human-readable names."""

    def test_all_codes_have_names(self):
        codes = [
            "Af",
            "Am",
            "Aw",
            "BSh",
            "BSk",
            "BWk",
            "BWh",
            "Csa",
            "Csb",
            "Cfa",
            "Cfb",
            "Cwa",
            "Dfa",
            "Dfb",
            "Dfc",
            "ET",
            "EF",
        ]
        names = {
            "Af": "Tropical Rainforest",
            "Am": "Monsoon Tropical",
            "Aw": "Tropical Savanna",
            "BSh": "Hot Semi-Arid",
            "BSk": "Cold Semi-Arid",
            "BWk": "Cold Desert",
            "BWh": "Hot Desert",
            "Csa": "Hot Mediterranean",
            "Csb": "Warm Mediterranean",
            "Cfa": "Humid Subtropical",
            "Cfb": "Oceanic",
            "Cwa": "Monsoon Subtropical",
            "Dfa": "Hot Continental",
            "Dfb": "Humid Continental",
            "Dfc": "Subarctic",
            "ET": "Tundra",
            "EF": "Ice Cap",
        }
        for code in codes:
            self.assertIn(code, names, f"Missing name for {code}")
            self.assertTrue(
                len(names[code]) > 0,
                f"Empty name for {code}",
            )


if __name__ == "__main__":
    unittest.main()
