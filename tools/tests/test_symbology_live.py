#!/usr/bin/env python3
"""AEE live marker tracking tests: death, echelon and dimension.

Executes the REAL pure kernels through tools/tests/sqf_lite.py and pins the
contract of the map, 3D and restore layer and of the re-pointed CfgMarkers
textures:

  addons/symbology/functions/symbology/fnc_symbologyEchelon.sqf
  addons/symbology/functions/symbology/fnc_symbologyEchelonMarker.sqf
  addons/symbology/functions/symbology/fnc_symbologyDimension.sqf

The executed-kernel tests are the regression test for this change: on the
pre-change tree the three kernels do not exist, so run_sqf cannot read them
and every executed test fails.  They pass after the kernels are added.

Run: python3 -m unittest tools.tests.test_symbology_live -v
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))

from sqf_lite import run_sqf  # noqa: E402

SYM_ADDON = REPO / "addons" / "symbology"
SYM = SYM_ADDON / "functions" / "symbology"
ECHELON_KERNEL = SYM / "fnc_symbologyEchelon.sqf"
ECHELON_MARKER_KERNEL = SYM / "fnc_symbologyEchelonMarker.sqf"
DIMENSION_KERNEL = SYM / "fnc_symbologyDimension.sqf"
KILLED_MARKER_KERNEL = SYM / "fnc_symbologyKilledMarker.sqf"
HAS_TRACKER_KERNEL = SYM / "fnc_symbologyHasTracker.sqf"
TABLES_SQF = SYM_ADDON / "data" / "symbology_tables.sqf"
TABLES_JSON = REPO / "data" / "symbology" / "symbology_tables.json"
MODIFIERS_SRC = (SYM_ADDON / "config_modifiers.hpp").read_text(encoding="utf-8")
CONFIG_SRC = (SYM_ADDON / "config.cpp").read_text(encoding="utf-8")
FAMILY_SRC = (SYM_ADDON / "config_family.hpp").read_text(encoding="utf-8")
MARKERS_SRC = (SYM_ADDON / "config_markers.hpp").read_text(encoding="utf-8")
APPLY_SRC = (SYM / "fnc_symbologyMarkersApply.sqf").read_text(encoding="utf-8")
RESTORE_SRC = (SYM / "fnc_symbologyMarkersRestore.sqf").read_text(encoding="utf-8")
WORLD_SRC = (SYM / "fnc_symbologyWorldDraw.sqf").read_text(encoding="utf-8")
MARKERS_INSTALLER_SRC = (SYM / "fnc_symbologyMarkers.sqf").read_text(encoding="utf-8")
RESOLVE_SRC = (SYM / "fnc_symbolResolve.sqf").read_text(encoding="utf-8")

SYM_TABLES = run_sqf(TABLES_SQF, [])
DIMENSION_SECTION = SYM_TABLES[6] if len(SYM_TABLES) > 6 else []
JSON_TABLES = json.loads(TABLES_JSON.read_text(encoding="utf-8"))
# The glyph token ("plane") and the category name ("fixed_wing") both carry the
# same dimension.  The repoint test keys by token, the section test by name.
GLYPH_DIMENSION_BY_TOKEN = {
    row["category"]: row["dimension"] for row in JSON_TABLES["glyphs"]
}
GLYPH_DIMENSION_BY_NAME = {
    row["name"]: row["dimension"] for row in JSON_TABLES["glyphs"]
}

ECHELON_TOKENS = (
    "team",
    "squad",
    "section",
    "platoon",
    "company",
    "battalion",
    "regiment",
    "brigade",
    "division",
    "corps",
    "army",
    "army_group",
    "region",
)

# The simple classes re-pointed to a dimension-correct catalogue texture.
REPOINTED = ("plane", "uav", "air", "naval", "installation")
DIMENSION_LETTER = {"air": "A", "sea": "S", "installation": "I"}

# The runtime family aliases live in the generated config_family.hpp, not in
# config.cpp.  Each alias is either a one-line alias of a real catalogue
# marker ("class AEE_b_plane: AEE_FA_... {};") or a full AEE_MarkerBase class
# for the five glyphs the catalogue does not publish.
ALIAS_RE = re.compile(r"class (AEE_\w+): ([A-Za-z0-9_]+) \{(.*?)\};", re.DOTALL)
FAMILY_ALIASES = {
    m.group(1): (m.group(2), m.group(3)) for m in ALIAS_RE.finditer(FAMILY_SRC)
}
# The catalogue marker blocks in config_markers.hpp carry the icon the
# aliases inherit.
MARKER_BLOCK_RE = re.compile(
    r"class (AEE_\w+): AEE_MarkerBase \{(.*?)\n    \};", re.DOTALL
)
MARKER_BLOCKS = {m.group(1): m.group(2) for m in MARKER_BLOCK_RE.finditer(MARKERS_SRC)}


def echelon(size):
    """Run the real echelon kernel."""
    return run_sqf(ECHELON_KERNEL, [size], {})


def echelon_marker(token):
    """Run the real echelon-marker kernel."""
    return run_sqf(ECHELON_MARKER_KERNEL, [token], {})


def dimension(category):
    """Run the real dimension kernel against the real generated table."""
    return run_sqf(
        DIMENSION_KERNEL, [category], {"aee_symbology_symbologyTables": SYM_TABLES}
    )


def killed(spec):
    """Run the real killed-marker kernel."""
    return run_sqf(KILLED_MARKER_KERNEL, [spec], {})


def has_tracker(items):
    """Run the real blue-force-tracker kernel."""
    return run_sqf(HAS_TRACKER_KERNEL, [items], {})


class TestEchelonKernel(unittest.TestCase):
    """fnc_symbologyEchelon, executed: group size -> echelon token."""

    def test_the_band_edges(self):
        self.assertEqual(echelon(1), "team")
        self.assertEqual(echelon(6), "squad")
        self.assertEqual(echelon(7), "section")
        self.assertEqual(echelon(13), "section")
        self.assertEqual(echelon(14), "platoon")

    def test_a_huge_group_is_a_region(self):
        self.assertEqual(echelon(300001), "region")

    def test_a_zero_group_clamps_to_team(self):
        self.assertEqual(echelon(0), "team")

    def test_a_negative_group_clamps_to_team(self):
        self.assertEqual(echelon(-25), "team")

    def test_every_token_is_reachable(self):
        seen = {
            echelon(size)
            for size in (
                1,
                2,
                6,
                7,
                13,
                14,
                40,
                41,
                150,
                151,
                500,
                501,
                2000,
                2001,
                6000,
                6001,
                15000,
                15001,
                60000,
                60001,
                120000,
                120001,
                300000,
                300001,
            )
        }
        self.assertEqual(seen, set(ECHELON_TOKENS))

    def test_the_bands_are_monotone(self):
        order = {token: rank for rank, token in enumerate(ECHELON_TOKENS)}
        last = -1
        for size in range(0, 310000, 1000):
            rank = order[echelon(size)]
            self.assertGreaterEqual(rank, last, f"not monotone at {size}")
            last = rank


class TestEchelonMarkerKernel(unittest.TestCase):
    """fnc_symbologyEchelonMarker, executed: token -> CfgMarkers class."""

    def test_the_named_tokens_map(self):
        self.assertEqual(echelon_marker("squad"), "AEE_Ech_Squad")
        self.assertEqual(echelon_marker("army_group"), "AEE_Ech_Army_Group")
        self.assertEqual(echelon_marker("region"), "AEE_Ech_Region")

    def test_an_unknown_token_defaults_to_team(self):
        self.assertEqual(echelon_marker("bogus"), "AEE_Ech_Team")

    def test_every_returned_class_is_registered(self):
        for token in ECHELON_TOKENS:
            with self.subTest(token=token):
                marker_class = echelon_marker(token)
                self.assertIn(f"class {marker_class}: AEE_MarkerBase {{", MODIFIERS_SRC)


class TestDimensionKernel(unittest.TestCase):
    """fnc_symbologyDimension, executed: category -> dimension."""

    def test_the_dimensions(self):
        self.assertEqual(dimension("rotary"), "air")
        self.assertEqual(dimension("fixed_wing"), "air")
        self.assertEqual(dimension("uav"), "air")
        self.assertEqual(dimension("sea_surface"), "sea")
        self.assertEqual(dimension("subsurface"), "subsurface")
        self.assertEqual(dimension("installation"), "installation")
        self.assertEqual(dimension("infantry"), "land")

    def test_an_unknown_category_is_land(self):
        self.assertEqual(dimension("bogus"), "land")

    def test_section_six_exists_and_every_row_is_a_four_tuple(self):
        self.assertGreater(len(SYM_TABLES), 6)
        self.assertTrue(DIMENSION_SECTION)
        for row in DIMENSION_SECTION:
            self.assertEqual(len(row), 4)

    def test_section_six_matches_the_json_dimensions(self):
        rows = {row[0]: row[1] for row in DIMENSION_SECTION}
        for name, expected in GLYPH_DIMENSION_BY_NAME.items():
            with self.subTest(category=name):
                self.assertEqual(rows.get(name), expected)


class TestKilledMarkerKernel(unittest.TestCase):
    """fnc_symbologyKilledMarker, executed: live spec -> last-known spec."""

    def test_the_last_known_spec_keeps_the_affiliation_and_category(self):
        spec = ["friend", "AEE_b_inf", "ColorWEST", "squad"]
        self.assertEqual(killed(spec), spec)

    def test_the_ceiling_keeps_every_field(self):
        # No destroyed-status symbol exists in the catalogue, so the
        # last-known form is the live form for the affiliation and category.
        spec = ["hostile", "AEE_o_armor", "ColorEAST", "company"]
        last_known = killed(spec)
        self.assertEqual(last_known[0], spec[0])
        self.assertEqual(last_known[1], spec[1])
        self.assertEqual(last_known[2], spec[2])
        self.assertEqual(last_known[3], spec[3])

    def test_a_malformed_spec_falls_back_to_unknown(self):
        self.assertEqual(killed(["friend"]), ["unknown", "", "ColorUNKNOWN", "unknown"])
        self.assertEqual(killed([]), ["unknown", "", "ColorUNKNOWN", "unknown"])


class TestTrackerKernel(unittest.TestCase):
    """fnc_symbologyHasTracker, executed: item list -> tracker present."""

    def test_each_tracker_device_is_recognised(self):
        for device in (
            "ItemGPS",
            "B_UavTerminal",
            "O_UavTerminal",
            "I_UavTerminal",
            "ACE_microDAGR",
            "ACE_DAGR",
        ):
            with self.subTest(device=device):
                self.assertTrue(has_tracker([device]))

    def test_a_tracker_among_other_items_is_found(self):
        self.assertTrue(has_tracker(["map", "compass", "watch", "ItemGPS"]))

    def test_no_tracker_returns_false(self):
        self.assertFalse(has_tracker([]))
        self.assertFalse(has_tracker(["map", "compass", "binocular"]))


class TestApplyContract(unittest.TestCase):
    """fnc_symbologyMarkersApply carries the alive gate, the echelon layer and
    the dimension argument."""

    def test_the_alive_guard_gates_the_player(self):
        # The player is drawn only when alive; a dead player is not drawn.
        self.assertIn("alive _player", APPLY_SRC)

    def test_the_unit_pass_is_gated_on_a_carried_tracker(self):
        # The unit pass is skipped when the setting is on and the player
        # carries no tracker.  The mission-marker pass is not gated.
        self.assertIn("symbologyHasTracker", APPLY_SRC)
        self.assertIn("bftRequired", APPLY_SRC)
        self.assertIn("assignedItems _player", APPLY_SRC)
        self.assertIn("items _player", APPLY_SRC)
        # The gate sits after the mission-marker pass and before the units.
        self.assertLess(
            APPLY_SRC.index("forEach allMapMarkers"),
            APPLY_SRC.index("symbologyHasTracker"),
        )
        self.assertLess(
            APPLY_SRC.index("symbologyHasTracker"),
            APPLY_SRC.index("private _units = []"),
        )

    def test_a_dead_tracked_unit_keeps_a_last_known_contact(self):
        # The old guard `if ((alive _x) && ...)` deleted a dead unit's marker.
        # The layer now keeps a LAST-KNOWN contact for a dead unit the
        # EntityKilled handler recorded, so the cleanup does not remove it.
        self.assertIn("symbologyKilledUnits", APPLY_SRC)
        self.assertIn("call FUNC(symbologyKilledMarker)", APPLY_SRC)
        self.assertIn("!(alive _unit)", APPLY_SRC)

    def test_the_death_handler_records_the_position_and_a_state_flag(self):
        self.assertIn('addMissionEventHandler ["EntityKilled"', MARKERS_INSTALLER_SRC)
        self.assertIn("symbologyKilledUnits", MARKERS_INSTALLER_SRC)
        self.assertIn("getPos _killed", MARKERS_INSTALLER_SRC)

    def test_restore_clears_the_last_known_state(self):
        self.assertIn("symbologyKilledUnits", RESTORE_SRC)

    def test_the_echelon_companion_marker_is_named(self):
        self.assertIn('"AEE_ECH_"', APPLY_SRC)

    def test_the_echelon_cache_is_tracked(self):
        self.assertIn("symbologyUnitEchelonMarkers", APPLY_SRC)

    def test_the_cba_current_unit_call_is_untouched(self):
        self.assertIn("CBA_fnc_currentUnit", APPLY_SRC)

    def test_the_frame_marker_is_created_before_the_echelon_marker(self):
        frame = APPLY_SRC.index("createMarkerLocal [_markerName")
        echelon = APPLY_SRC.index("createMarkerLocal [_echelonName")
        self.assertLess(frame, echelon)

    def test_the_resolver_call_carries_the_dimension(self):
        self.assertIn("_resolvedPalette, _dimension", APPLY_SRC)
        self.assertIn("call FUNC(symbolResolve)", APPLY_SRC)


class TestWorldContract(unittest.TestCase):
    """fnc_symbologyWorldDraw carries the dimension and the echelon overlay."""

    def test_the_resolver_call_carries_the_dimension(self):
        # The draw worker resolves "Auto" to _resolvedPalette before the
        # resolver calls (as the map layer does), so the dimension rides on
        # the resolved palette, not on the raw _palette read at the top.
        self.assertIn("_resolvedPalette, _dimension", WORLD_SRC)
        self.assertIn("call FUNC(symbolResolve)", WORLD_SRC)

    def test_the_echelon_overlay_is_drawn(self):
        self.assertIn("_echelonClass", WORLD_SRC)
        self.assertIn("3.0", WORLD_SRC)
        self.assertIn(">> _echelonClass >>", WORLD_SRC)


class TestResolverContract(unittest.TestCase):
    """fnc_symbolResolve gains the sixth dimension argument."""

    def test_the_dimension_parameter_exists(self):
        self.assertIn('["_dimension", "land", [""]]', RESOLVE_SRC)

    def test_the_dimension_is_passed_to_the_type_kernel(self):
        self.assertIn(
            "_affiliation, _category, _dimension, _echelon, _palette", RESOLVE_SRC
        )


class TestRestoreContract(unittest.TestCase):
    """fnc_symbologyMarkersRestore deletes the echelon cache."""

    def test_restore_deletes_the_echelon_cache(self):
        self.assertIn("symbologyUnitEchelonMarkers", RESTORE_SRC)
        self.assertIn("deleteMarkerLocal", RESTORE_SRC)


class TestModifierRegistration(unittest.TestCase):
    """The echelon overlay classes must be included in the live config."""

    def test_the_modifier_block_is_included_in_the_markers_config(self):
        # config_modifiers.hpp carries AEE_Ech_*; without the include the
        # classes are never registered in CfgMarkers and the overlay silently
        # fails to draw.
        self.assertIn('#include "config_modifiers.hpp"', CONFIG_SRC)

    def test_every_echelon_class_is_declared_in_the_modifier_block(self):
        for token in ECHELON_TOKENS:
            marker_class = echelon_marker(token)
            with self.subTest(token=token):
                self.assertIn(f"class {marker_class}: AEE_MarkerBase {{", MODIFIERS_SRC)


class TestRepointedFrames(unittest.TestCase):
    """Every re-pointed simple class uses a dimension-correct texture."""

    @staticmethod
    def _resolved(glyph, family):
        """Return (icon, direct) for AEE_<family>_<glyph>.

        direct is True when the alias of an AEE_MarkerBase owns its icon
        (the catalogue publishes no texture for that glyph).
        """
        class_name = f"AEE_{family}_{glyph}"
        parent, body = FAMILY_ALIASES[class_name]
        if parent == "AEE_MarkerBase":
            block = body
            direct = True
        else:
            block = MARKER_BLOCKS[parent]
            direct = False
        match = re.search(r'icon = "([^"]+)"', block)
        assert match is not None, f"{class_name} resolves to no icon"
        return match.group(1), direct

    def test_repointed_classes_use_dimension_correct_textures(self):
        prefix = "\\z\\aee\\addons\\symbology\\data\\markers\\"
        for glyph in REPOINTED:
            dimension_name = GLYPH_DIMENSION_BY_TOKEN[glyph]
            letter = DIMENSION_LETTER[dimension_name]
            for family in ("b", "o", "n"):
                with self.subTest(glyph=glyph, family=family):
                    self.assertIn(f"AEE_{family}_{glyph}", FAMILY_ALIASES)
                    icon, direct = self._resolved(glyph, family)
                    self.assertTrue(icon.startswith(prefix), icon)
                    basename = icon.rsplit("\\", 1)[-1]
                    if not direct:
                        # A catalogue parent names the battle dimension in the
                        # second token, e.g. AEE_FA_... for air and AEE_FS_...
                        # for sea.
                        token_parts = basename.split("_")
                        self.assertGreaterEqual(len(token_parts), 2)
                        self.assertIn(letter, token_parts[1])
                    else:
                        # installation travels as AEE_FI_/HI_/NI_Installation,
                        # a family+dimension composite, so the standalone
                        # dimension token is not asserted.  The directory and
                        # the on-disk file are the honest checks.
                        self.assertIn(basename.split("_")[1], {"FI", "HI", "NI"})
                    # The virtual path \z\aee\ maps to the repo root, so the
                    # first two components are dropped to reach the file.
                    path_parts = [
                        part for part in icon.lstrip("\\").split("\\") if part
                    ]
                    self.assertTrue(REPO.joinpath(*path_parts[2:]).is_file(), icon)

    def test_repointed_classes_no_longer_reference_vanilla_frames(self):
        for glyph in REPOINTED:
            for family in ("b", "o", "n"):
                with self.subTest(glyph=glyph, family=family):
                    class_name = f"AEE_{family}_{glyph}"
                    parent, body = FAMILY_ALIASES[class_name]
                    self.assertNotIn("\\A3\\ui_f\\", body)
                    if parent != "AEE_MarkerBase":
                        self.assertNotIn("\\A3\\ui_f\\", MARKER_BLOCKS[parent])


if __name__ == "__main__":
    unittest.main()
