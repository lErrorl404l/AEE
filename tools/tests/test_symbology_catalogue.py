#!/usr/bin/env python3
"""The AEE NATO/OPFOR symbology catalogue contract tests.

Pins the engine-family override in addons/optics/config_markers.hpp to the exact
APP-6 symbol each engine class means, so the mapping cannot drift to a loose
keyword match again.  A keyword match once pinned b_armor to the anti-tank glyph
("armour" is a substring of "armoured") and b_plane to an engineer glyph.

Run: python3 -m unittest tools.tests.test_symbology_catalogue -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
CONFIG_MARKERS = (REPO / "addons" / "optics" / "config_markers.hpp").read_text(
    encoding="utf-8"
)
CATALOGUE = REPO / "data" / "symbology" / "nato_catalogue.json"

# Every engine class AEE overwrites, pinned to the exact catalogue marker name.
# The engine ships these classes in Addons/ui_f.pbo (CfgMarkers NATO families).
ENGINE_OVERRIDE = {
    "b_inf": "AEE_FL_Friendly_Unit_Infantry",
    "b_motor_inf": "AEE_FL_Friendly_Unit_Infantry_Motorized",
    "b_armor": "AEE_FL_Friendly_Unit_Armour",
    "b_recon": "AEE_FL_Friendly_Unit_Reconnaissance",
    "b_plane": "AEE_FA_Friendly_Unit_Aviation_Fixed_Win",
    "b_uav": "AEE_FA_Friendly_Unit_Unmanned_Aerial_Ve",
    "b_med": "AEE_FL_Friendly_Unit_Medical",
    "b_art": "AEE_FL_Friendly_Unit_Artillery",
    "b_mortar": "AEE_FL_Friendly_Unit_Mortars",
    "b_hq": "AEE_FL_Friendly_Unit_Headquarters_Unit",
    "b_support": "AEE_FL_Friendly_Unit_CSS_Combat_Service",
    "b_maint": "AEE_FL_Friendly_Unit_CSS_Maintenance",
    "b_service": "AEE_FL_Friendly_Unit_CSS_Supply",
    "b_antiair": "AEE_FL_Friendly_Unit_Air_Defence",
    "o_inf": "AEE_HL_Hostile_Unit_Infantry",
    "o_motor_inf": "AEE_HL_Hostile_Unit_Infantry_Motorized",
    "o_armor": "AEE_HL_Hostile_Unit_Armour",
    "o_recon": "AEE_HL_Hostile_Unit_Reconnaissance",
    "o_plane": "AEE_HA_Hostile_Unit_Aviation_Fixed_Wing",
    "o_uav": "AEE_HA_Hostile_Unit_Unmanned_Aerial_Veh",
    "o_med": "AEE_HL_Hostile_Unit_Medical",
    "o_art": "AEE_HL_Hostile_Unit_Artillery",
    "o_mortar": "AEE_HL_Hostile_Unit_Mortars",
    "o_hq": "AEE_HL_Hostile_Unit_Headquarters_Unit",
    "o_support": "AEE_HL_Hostile_Unit_CSS_Combat_Service",
    "o_maint": "AEE_HL_Hostile_Unit_CSS_Maintenance",
    "o_service": "AEE_HL_Hostile_Unit_CSS_Supply",
    "o_antiair": "AEE_HL_Hostile_Unit_Air_Defence",
    "n_inf": "AEE_NL_Neutral_Unit_Infantry",
    "n_motor_inf": "AEE_NL_Neutral_Unit_Infantry",
    "n_armor": "AEE_NL_Neutral_Unit_Armour",
    "n_recon": "AEE_NL_Neutral_Unit_Reconnaissance",
    "n_uav": "AEE_NA_Neutral_Unit_Unmanned_Aerial_Veh",
    "n_med": "AEE_NL_Neutral_Unit_Medical",
    "n_art": "AEE_NL_Neutral_Unit_Artillery",
    "n_mortar": "AEE_NL_Neutral_Unit_Mortars",
    "n_hq": "AEE_NL_Neutral_Unit_Headquarters_Unit",
    "n_support": "AEE_NL_Neutral_Unit_CSS_Combat_Service",
    "n_maint": "AEE_NL_Neutral_Unit_CSS_Maintenance",
    "n_service": "AEE_NL_Neutral_Unit_CSS_Supply",
    "n_antiair": "AEE_NL_Neutral_Unit_Air_Defence",
    "c_air": "AEE_FA_APP_6_Army_Aviation",
    "c_plane": "AEE_FL_APP_6_Air_Force",
}

# The engine class family -> the affiliation the override must resolve to.
FAMILY_PREFIX = {"b": "F", "o": "H", "n": "N"}
# The engine class -> the battle dimension letter its symbol must carry.
ENGINE_DIM = {
    "plane": "A",
    "uav": "A",
    "air": "A",
}


def override_icons() -> dict[str, str]:
    """Parse the engine-override block into {engine class: icon path}."""
    block = CONFIG_MARKERS.split("// Overwrite the engine")[-1]
    found: dict[str, str] = {}
    for m in re.finditer(
        r'class (\w+) \{ icon = "([^"]+)"; texture = "([^"]+)"; \};', block
    ):
        found[m.group(1)] = m.group(2)
    return found


def asset_name(icon: str) -> str:
    """The .paa file name from an engine icon path (backslash-separated)."""
    return icon.replace("\\", "/").rsplit("/", 1)[-1]


def asset_stem(icon: str) -> str:
    return (
        asset_name(icon)[:-4] if asset_name(icon).endswith(".paa") else asset_name(icon)
    )


class TestEngineOverrideMapping(unittest.TestCase):
    """Every engine class is pinned to its exact APP-6 symbol."""

    def test_the_override_count_is_43(self):
        self.assertEqual(len(override_icons()), 43)

    def test_every_class_resolves_to_its_exact_symbol(self):
        icons = override_icons()
        for cls, expected in ENGINE_OVERRIDE.items():
            with self.subTest(cls=cls):
                self.assertIn(cls, icons)
                self.assertEqual(asset_stem(icons[cls]), expected)

    def test_every_override_asset_exists(self):
        for cls, icon in override_icons().items():
            with self.subTest(cls=cls):
                name = asset_name(icon)
                self.assertTrue(
                    (REPO / "addons" / "optics" / "data" / "markers" / name).is_file(),
                    f"{cls} points at a missing asset {name}",
                )

    def test_the_affiliation_prefix_matches_the_engine_family(self):
        for cls, icon in override_icons().items():
            family = cls.split("_", 1)[0]
            if family not in FAMILY_PREFIX:
                continue
            with self.subTest(cls=cls):
                stem = asset_stem(icon)
                self.assertTrue(
                    stem.startswith(f"AEE_{FAMILY_PREFIX[family]}"),
                    f"{cls} must carry the {FAMILY_PREFIX[family]} affiliation prefix",
                )

    def test_the_dimension_matches_the_engine_class(self):
        for cls, icon in override_icons().items():
            family = cls.split("_", 1)[0]
            if family not in FAMILY_PREFIX:
                continue
            glyph = cls.split("_", 1)[1]
            expected = ENGINE_DIM.get(glyph)
            if expected is None:
                continue
            with self.subTest(cls=cls):
                stem = asset_stem(icon)
                self.assertEqual(
                    stem.split("_")[1][1],
                    expected,
                    f"{cls} must carry the {expected} battle dimension",
                )


class TestCatalogueEncoding(unittest.TestCase):
    """The asset prefix {fam}{dim} matches the symbol's affiliation and dimension.

    The operator's rule: an AEE_FA_* asset must be friend + air, an AEE_HL_* one
    hostile + land, and so on.  This is the truth table the prefix must obey.
    """

    AFFIL_LETTER = {"Friend": "F", "Hostile": "H", "Neutral": "N", "Unknown": "U"}
    DIM_LETTER = {
        "Land": "L",
        "Air/Space": "A",
        "Sea Surface": "S",
        "Subsurface": "U",
        "Installation": "I",
        "Equipment": "E",
    }

    def test_every_symbol_entry_encodes_its_affiliation_and_dimension(self):
        import sys

        sys.path.insert(0, str(REPO))
        from tools import gen_symbology_catalogue as gen

        seen: set[str] = set()
        for entry in gen.symbol_entries():
            name = gen.marker_name(entry, seen)
            prefix = name.split("_")[1]
            with self.subTest(asset=name):
                self.assertEqual(prefix[0], self.AFFIL_LETTER[entry["affil"]])
                self.assertEqual(prefix[1], self.DIM_LETTER[entry["dim"]])

    def test_every_symbol_is_registered(self):
        import sys

        sys.path.insert(0, str(REPO))
        from tools import gen_symbology_catalogue as gen

        seen: set[str] = set()
        for entry in gen.symbol_entries():
            name = gen.marker_name(entry, seen)
            with self.subTest(asset=name):
                self.assertIn(f"class {name}: AEE_MarkerBase {{", CONFIG_MARKERS)


class TestNoDuplicateClasses(unittest.TestCase):
    """Every generated header defines each class exactly once.

    Two catalogue functions can slug to the same marker name ("Sub surface" and
    "Sub-surface"); the generator must suffix the collision, not emit the class
    twice, or hemtt fails with L-C03.
    """

    def _classes(self, name: str) -> list[str]:
        text = (REPO / "addons" / "optics" / name).read_text(encoding="utf-8")
        return re.findall(r"^\s*class (AEE_\w+): AEE_MarkerBase", text, re.M)

    def test_no_duplicate_class_names(self):
        for header in (
            "config_markers.hpp",
            "config_crossproduct.hpp",
            "config_taxonomy.hpp",
            "config_modifiers.hpp",
        ):
            with self.subTest(header=header):
                names = self._classes(header)
                dupes = [n for n in set(names) if names.count(n) > 1]
                self.assertEqual(dupes, [], f"{header} defines {dupes} twice")


if __name__ == "__main__":
    unittest.main()
