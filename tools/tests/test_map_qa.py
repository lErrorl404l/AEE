#!/usr/bin/env python3
"""The map QA matrix and its machine checks.

Every map invariant has one machine check, recorded in
``docs/wiki/research/map-qa-matrix.md``.  This suite proves the record is
complete and that every cited check exists.  It adds a direct check only for an
invariant that no existing suite proves: the engine marker family textures, the
pure echelon size kernel, and the location parent graph the record carries.

Where ``test_terrain.py``, ``test_symbology.py`` or ``test_mgrs_map_layer.py``
already hold an invariant, this suite cites the check and does not repeat it.

Run: python3 -m unittest tools.tests.test_map_qa
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))

from sqf_lite import run_sqf  # noqa: E402

MATRIX = REPO / "docs" / "wiki" / "research" / "map-qa-matrix.md"
SYMBOLOGY = REPO / "addons" / "symbology"
CART = REPO / "addons" / "cartography"
MARKERS_HPP = SYMBOLOGY / "config_markers.hpp"
LOC_HPP = CART / "config_locationtypes.hpp"
ECHELON_KERNEL = SYMBOLOGY / "functions" / "symbology" / "fnc_symbologyEchelonSize.sqf"
KILLED_MARKER_KERNEL = (
    SYMBOLOGY / "functions" / "symbology" / "fnc_symbologyKilledMarker.sqf"
)
ICON_WORLD_SIZE_KERNEL = CART / "functions" / "hud" / "fnc_mapIconWorldSize.sqf"
CART_PREP = (CART / "XEH_PREP.hpp").read_text(encoding="utf-8")
RUN_TESTS = REPO / "tools" / "run_tests.py"
ADR030 = (
    REPO
    / "docs"
    / "adr"
    / "ADR-030-map-legibility-location-inheritance-object-names-grid-and-mgrs-contrast.md"
)
TOPO_SURFACE = REPO / "docs" / "engine" / "topo-map-surface.md"
COL_HPP = CART / "config_mapcolors.hpp"
DISP_HPP = CART / "config_mapdisplays.hpp"
DISP_SRC = DISP_HPP.read_text(encoding="utf-8")
FAMILY_HPP = SYMBOLOGY / "config_family.hpp"

MATRIX_SRC = MATRIX.read_text(encoding="utf-8")
MARKERS_SRC = MARKERS_HPP.read_text(encoding="utf-8")
LOC_SRC = LOC_HPP.read_text(encoding="utf-8")
ADR030_SRC = ADR030.read_text(encoding="utf-8")
TOPO_SURFACE_SRC = TOPO_SURFACE.read_text(encoding="utf-8")
COL_SRC = COL_HPP.read_text(encoding="utf-8")
LEGEND_KERNEL = CART / "functions" / "hud" / "fnc_mapLegendDraw.sqf"
MGRS_DRAW_SRC = (CART / "functions" / "hud" / "fnc_mgrsMapDraw.sqf").read_text(
    encoding="utf-8"
)
MINI_HPP = CART / "config_mapminimap.hpp"
MINI_SRC = MINI_HPP.read_text(encoding="utf-8")
SYMBOLS_JSON = REPO / "data" / "symbology" / "terrain_symbols.json"
TABLE_SRC = json.loads(SYMBOLS_JSON.read_text(encoding="utf-8"))

AEE_MARKER_PREFIX = "\\z\\aee\\addons\\symbology\\data\\markers\\"

# The engine marker families that must render an AEE symbol (ADR-028 defect 2).
# The list is the representative set the live probe P117 also reads.
ENGINE_MARKER_FAMILIES = (
    "b_inf",
    "b_mech_inf",
    "o_naval",
    "n_installation",
    "c_car",
    "hd_dot",
    "hd_ambush",
    "mil_destroy",
    "mil_dot",
    "Contact_arrow1",
    "Contact_art1",
    "GroundSupport_CAS_WEST",
    "GroundSupport_ARTY_EAST",
    "group_0",
    "group_11",
    "respawn_inf",
    "waypoint",
)

# The ten invariants the record must name, keyed to a distinctive phrase.
INVARIANTS = (
    "Exactly one grid",
    "engine numeric numbers and the engine lines",
    "Every engine marker family renders an AEE symbol",
    "The AEE markers carry categories",
    "The echelon overlay is a 1:2 box",
    "The location classes restate their parent",
    "The object icons cover every engine object name",
    "The MGRS grid is cardinal",
    "The MGRS line contrast is dark and high",
    "The terrain symbol size is the vanilla interface-scaled value",
)

# A 4-cell invariant row: | n | invariant | check | file |.
_INVARIANT_ROW = re.compile(r"^\|\s*\d+\s*\|(.+?)\|(.+?)\|(.+?)\|\s*$", re.MULTILINE)
# A 2-cell parent-graph row: | Class | Parent |.
_GRAPH_ROW = re.compile(
    r"^\|\s*([A-Za-z]\w*)\s*\|\s*([A-Za-z]\w*)\s*\|\s*$", re.MULTILINE
)


def _invariant_rows() -> list[tuple[str, str, str]]:
    return [
        (inv.strip(), check.strip(), path.strip())
        for inv, check, path in _INVARIANT_ROW.findall(MATRIX_SRC)
    ]


def _graph_section() -> str:
    head = MATRIX_SRC.split("## The location parent graph", 1)
    if len(head) < 2:
        return ""
    return head[1].split("\n## ", 1)[0]


def _graph_pairs() -> dict[str, str]:
    pairs = dict(_GRAPH_ROW.findall(_graph_section()))
    pairs.pop("Class", None)
    return pairs


def _colour_of(text: str, field: str) -> list[float] | None:
    m = re.search(rf"{re.escape(field)}\[\]\s*=\s*\{{([^}}]*)\}}", text)
    if not m:
        return None
    return [float(x) for x in m.group(1).split(",")]


def _rgba_eq(a, b, tol=1e-6) -> bool:
    return len(a) == len(b) and all(abs(x - y) <= tol for x, y in zip(a, b))


def _array_of(text: str, field: str):
    m = re.search(rf"{re.escape(field)}\[\]\s*=\s*\{{([^}}]*)\}}", text)
    if not m:
        return None
    return [float(x) for x in m.group(1).split(",")]


def _scalar_of(text: str, field: str):
    m = re.search(rf"\b{re.escape(field)}\s*=\s*([0-9.]+)\s*;", text)
    return float(m.group(1)) if m else None


def _text_of(text: str, field: str):
    m = re.search(rf'\b{re.escape(field)}\s*=\s*"([^"]+)"\s*;', text)
    return m.group(1) if m else None


class TestMapQaMatrix(unittest.TestCase):
    def test_the_matrix_names_every_invariant(self):
        missing = [inv for inv in INVARIANTS if inv not in MATRIX_SRC]
        self.assertEqual(missing, [], "invariants not named: " + "; ".join(missing))

    def test_the_matrix_has_one_row_per_invariant(self):
        self.assertEqual(
            len(_invariant_rows()), len(INVARIANTS), "row count does not match"
        )

    def test_every_cited_check_file_exists(self):
        for inv, _check, path in _invariant_rows():
            with self.subTest(invariant=inv):
                self.assertTrue((REPO / path).is_file(), f"cited file missing: {path}")

    def test_every_cited_test_method_exists(self):
        for inv, check, path in _invariant_rows():
            if not path.endswith(".py") or not check:
                continue
            method = check.rsplit(".", 1)[-1]
            with self.subTest(invariant=inv):
                self.assertIn(
                    f"def {method}(",
                    (REPO / path).read_text(encoding="utf-8"),
                    f"{path} has no method {method}",
                )


class TestMapQaChecks(unittest.TestCase):
    def test_every_engine_marker_family_renders_an_aee_symbol(self):
        for name in ENGINE_MARKER_FAMILIES:
            match = re.search(rf"class\s+{re.escape(name)}\b", MARKERS_SRC)
            self.assertIsNotNone(match, f"{name} is not declared")
            block = MARKERS_SRC[match.start() : match.start() + 400]
            with self.subTest(family=name):
                self.assertIn(
                    AEE_MARKER_PREFIX,
                    block,
                    f"{name} does not carry an AEE marker texture",
                )

    def test_the_echelon_overlay_is_a_one_to_two_box(self):
        self.assertEqual(run_sqf(ECHELON_KERNEL, [1], {}), [1, 2])
        self.assertEqual(run_sqf(ECHELON_KERNEL, [0.5], {}), [0.5, 1])
        # A non-positive half-width falls back to 1, so the box stays valid.
        self.assertEqual(run_sqf(ECHELON_KERNEL, [0], {}), [1, 2])

    def test_the_location_parent_graph_matches_the_matrix(self):
        pairs = _graph_pairs()
        self.assertTrue(pairs, "the record carries no parent graph")
        for cls, parent in pairs.items():
            match = re.search(rf"class\s+{cls}\s*:\s*(\w+)\s*\{{", LOC_SRC)
            with self.subTest(cls=cls):
                self.assertIsNotNone(match, f"{cls} is declared without a parent")
                self.assertEqual(match.group(1), parent)

    def test_the_parentless_roots_stay_bare(self):
        for cls in ("Mount", "Name", "Area"):
            with self.subTest(root=cls):
                self.assertRegex(LOC_SRC, rf"class\s+{cls}\s*\{{")
                self.assertIsNone(re.search(rf"class\s+{cls}\s*:", LOC_SRC))


class TestMapQaDocDrift(unittest.TestCase):
    """The engine records match the shipped map config.  Two records once said
    the shipped config did not set a field it sets; this holds the records to
    the config so the drift cannot return."""

    def test_adr030_names_the_shipped_shaded_sea_value(self):
        self.assertNotIn("shadedSea is not set", ADR030_SRC)
        self.assertIn("shadedSea", ADR030_SRC)
        self.assertIn("shadedSea` is set to 1", ADR030_SRC)

    def test_topo_map_surface_names_the_shipped_render_fields(self):
        self.assertNotIn("does not yet set", TOPO_SURFACE_SRC)
        for field in ("drawShaded", "shadedSea", "colorForestTextured"):
            with self.subTest(field=field):
                self.assertIn(field, TOPO_SURFACE_SRC)

    def test_the_named_fields_match_the_shipped_config(self):
        self.assertIn("shadedSea = 1;", COL_SRC)
        self.assertIn("drawShaded = 0.15;", COL_SRC)
        self.assertIn("colorForestTextured", COL_SRC)


class TestMapIconWorldSizeKernel(unittest.TestCase):
    """fnc_mapIconWorldSize, executed: (metres, worldSize, scale) -> pixels.

    The engine draws a map icon at a constant pixel size, so an icon that
    keeps a fixed WORLD size needs a pixel size that scales with the zoom.
    The kernel is pure: the world size and the scale arrive as arguments.
    """

    def test_a_metre_size_on_the_reference_world_at_unit_scale(self):
        # 6.4 * 8192 / 8192 * 1.0 = 6.4, so 64 metres -> 10 pixels.
        self.assertEqual(run_sqf(ICON_WORLD_SIZE_KERNEL, [64, 8192, 1.0], {}), 10.0)

    def test_a_half_world_size_doubles_the_pixels(self):
        # 6.4 * 4096 / 8192 * 1.0 = 3.2, so the same metres -> twice the pixels.
        self.assertEqual(run_sqf(ICON_WORLD_SIZE_KERNEL, [64, 4096, 1.0], {}), 20.0)

    def test_a_double_scale_halves_the_pixels(self):
        # 6.4 * 8192 / 8192 * 2.0 = 12.8, so 64 metres -> 5 pixels.
        self.assertEqual(run_sqf(ICON_WORLD_SIZE_KERNEL, [64, 8192, 2.0], {}), 5.0)

    def test_a_non_positive_scale_is_zero(self):
        self.assertEqual(run_sqf(ICON_WORLD_SIZE_KERNEL, [64, 8192, 0], {}), 0.0)

    def test_a_non_positive_world_size_is_zero(self):
        self.assertEqual(run_sqf(ICON_WORLD_SIZE_KERNEL, [64, 0, 1.0], {}), 0.0)

    def test_the_kernel_is_registered(self):
        self.assertIn("PREPS(hud,mapIconWorldSize);", CART_PREP)


class TestLastKnownContactLifecycle(unittest.TestCase):
    """A killed unit keeps a last-known contact (todo 6).

    The map QA matrix proves every engine marker family renders an AEE
    symbol.  This holds the last-known contact to the same rule: the killed
    kernel keeps the live marker type, which must be a registered class.
    """

    def test_the_killed_kernel_keeps_a_registered_marker_type(self):
        spec = ["friend", "AEE_b_inf", "ColorWEST", "squad"]
        last_known = run_sqf(KILLED_MARKER_KERNEL, [spec], {})
        self.assertEqual(last_known[1], "AEE_b_inf")
        self.assertIn(
            "class AEE_b_inf:",
            FAMILY_HPP.read_text(encoding="utf-8"),
        )


class TestMapDisplayLevers(unittest.TestCase):
    """The zoom range and the density LOD and simple variants (todo 8).

    The base ui_f RscMapControl leaves the density fields unset; AEE sets
    them in config_mapcolors.hpp.  scaleMax is AEE's own; scaleDefault is the
    engine strategic-map scale; the density fields are the engine Eden
    ctrlMap and minimap values.
    """

    def test_the_zoom_range_is_set(self):
        self.assertIn("scaleMax = 2;", COL_SRC)
        self.assertIn("scaleDefault = 0.3;", COL_SRC)

    def test_the_density_lod_and_simple_variants_are_set(self):
        for field, value in (
            ("ptsPerSquareForLod1", "4"),
            ("ptsPerSquareForLod2", "1"),
            ("ptsPerSquareMainRoad", "6"),
            ("ptsPerSquareMainRoadSimple", "1"),
            ("ptsPerSquareRoadSimple", "1"),
            ("ptsPerSquareObjLod1", "2"),
        ):
            with self.subTest(field=field):
                self.assertIn(f"{field} = {value};", COL_SRC)

    def test_the_probe_asserts_the_new_fields(self):
        probe = (
            REPO
            / "tests"
            / "docker"
            / "missions"
            / "aee_test.Stratis"
            / "aee_p134_map_density_probe.sqf"
        ).read_text(encoding="utf-8")
        for field in (
            "scaleMax",
            "scaleDefault",
            "ptsPerSquareForLod1",
            "ptsPerSquareForLod2",
            "ptsPerSquareMainRoad",
            "ptsPerSquareMainRoadSimple",
            "ptsPerSquareRoadSimple",
            "ptsPerSquareObjLod1",
        ):
            with self.subTest(field=field):
                self.assertIn(f'["{field}",', probe)


class TestMapLegend(unittest.TestCase):
    """The scripted topographic legend (todo 9).

    The engine Legend class holds position only and draws its own body, so a
    mod cannot author one (docs/engine/topo-map-surface.md:186-194).  AEE draws
    the legend from SQF.  FUNC(mapLegendDraw) is pure and resolves every swatch
    colour from the palette argument, which the caller builds from the same
    table the map config is pinned to (data/symbology/terrain_symbols.json), so
    the legend and the map share one source.
    """

    MAP_KEYS = (
        ("relief_brown", "colorLevels"),
        ("water_blue", "colorSea"),
        ("vegetation_green", "colorForest"),
        ("transport_red", "colorMainRoads"),
        ("contour_index", "colorMainCountlines"),
        ("contour_intermediate", "colorCountlines"),
    )
    GROUP_KEYS = (
        ("group_relief", "relief_brown"),
        ("group_vegetation", "vegetation_green"),
        ("group_hydrography", "water_blue"),
        ("group_populated", "populated_black"),
        ("group_works", "works_black"),
        ("group_transport", "transport_red"),
        ("group_boundary", "boundary_black"),
        ("group_control", "control_black"),
        ("group_military", "military_green"),
    )
    ROW_COUNT = len(MAP_KEYS) + len(GROUP_KEYS)

    def _shared_palette(self):
        colours = TABLE_SRC["map_colours"]
        palette = TABLE_SRC["palette"]
        rows = [[key, colours[field]] for key, field in self.MAP_KEYS]
        rows += [[key, palette[field]] for key, field in self.GROUP_KEYS]
        return rows

    def test_the_kernel_returns_one_row_per_legend_entry(self):
        rows = run_sqf(LEGEND_KERNEL, [self._shared_palette()], {})
        self.assertEqual(len(rows), self.ROW_COUNT)

    def test_the_kernel_resolves_every_swatch_from_the_shared_table(self):
        palette = self._shared_palette()
        rows = run_sqf(LEGEND_KERNEL, [palette], {})
        by_key = {name: colour for name, colour in palette}
        for (key, _field), (swatch, _label) in zip(self.MAP_KEYS, rows):
            self.assertTrue(_rgba_eq(swatch, by_key[key]), key)

    def test_the_map_swatches_match_the_shipped_config(self):
        # The map draws from the config; the legend reads the same table, so
        # each map swatch equals the config value.  A swatch outside the table
        # (a hardcoded literal) fails here.
        rows = run_sqf(LEGEND_KERNEL, [self._shared_palette()], {})
        for (_key, field), (swatch, _label) in zip(self.MAP_KEYS, rows):
            self.assertTrue(_rgba_eq(swatch, _colour_of(COL_SRC, field)), field)

    def test_a_swatch_not_in_the_shared_table_is_absent(self):
        palette = [row for row in self._shared_palette() if row[0] != "water_blue"]
        rows = run_sqf(LEGEND_KERNEL, [palette], {})
        labels = [label for _swatch, label in rows]
        self.assertNotIn("Water", labels)
        self.assertEqual(len(rows), self.ROW_COUNT - 1)

    def test_the_kernel_reads_the_table_not_a_literal(self):
        # Mutation proof: a changed palette value changes the returned swatch,
        # so the kernel derives the colour from the argument, not a literal.
        palette = self._shared_palette()
        palette[0][1] = [0.0, 0.0, 0.0, 1.0]
        rows = run_sqf(LEGEND_KERNEL, [palette], {})
        self.assertTrue(_rgba_eq(rows[0][0], [0.0, 0.0, 0.0, 1.0]))

    def test_the_legend_kernel_is_registered(self):
        self.assertIn("PREPS(hud,mapLegendDraw);", CART_PREP)

    def test_the_legend_hook_draws_on_the_map_control(self):
        # The Draw hook calls the kernel and draws on the map control.
        self.assertIn("call FUNC(mapLegendDraw)", MGRS_DRAW_SRC)


class TestMapMinimapTargets(unittest.TestCase):
    """The minimap and airborne-minimap targets (todo 10).

    The engine minimap CA_MiniMap forces part of the palette, so AEE
    re-declares the control for the fields the engine does not force, from
    config_mapminimap.hpp.  Every reachable value is the SAME as
    config_mapcolors.hpp, so the minimap and the main map read one source; a
    forced field would be dead and is recorded in the ceiling instead.
    """

    REACH_ARRAYS = (
        "colorOutside",
        "colorInactive",
        "colorForestTextured",
        "colorNames",
        "colorTrails",
        "colorTrailsFill",
    )
    REACH_SCALARS = (
        "sizeExLevel",
        "ptsPerSquareSea",
        "ptsPerSquareCLn",
        "widthRailWay",
        "shadedSea",
    )
    FORCED = (
        "colorSea",
        "colorForest",
        "colorForestBorder",
        "colorRocks",
        "colorRocksBorder",
        "colorLevels",
        "colorMainCountlines",
        "colorCountlines",
        "colorMainCountlinesWater",
        "colorCountlinesWater",
        "colorPowerLines",
        "colorRailWay",
        "colorTracks",
        "colorTracksFill",
        "colorRoads",
        "colorRoadsFill",
        "colorMainRoads",
        "colorMainRoadsFill",
        "colorGrid",
        "colorGridMap",
        "maxSatelliteAlpha",
        "alphaFadeStartScale",
        "alphaFadeEndScale",
        "drawShaded",
        "showCountourInterval",
        "moveOnEdges",
        "ptsPerSquareTxt",
        "ptsPerSquareFor",
        "ptsPerSquareForEdge",
        "ptsPerSquareRoad",
        "ptsPerSquareMainRoad",
        "ptsPerSquareObj",
        "ptsPerSquareObjLod1",
        "ptsPerSquareForLod1",
        "ptsPerSquareForLod2",
        "ptsPerSquareRoadSimple",
        "ptsPerSquareMainRoadSimple",
    )

    def test_the_minimap_and_airborne_targets_are_declared(self):
        self.assertIn("class RscCustomInfoMiniMap {", DISP_SRC)
        self.assertIn(
            "class RscCustomInfoAirborneMiniMap: RscCustomInfoMiniMap {", DISP_SRC
        )
        # Every reopened class restates its vanilla parent, so the engine Empty
        # syntax cannot strip the inherited palette or font fields (ADR-030).
        self.assertIn("class CA_MiniMap: RscMapControl {", DISP_SRC)
        self.assertIn("class CA_MiniMap: CA_MiniMap {", DISP_SRC)
        self.assertIn("class MiniMap: RscControlsGroupNoScrollbars {", DISP_SRC)

    def test_the_targets_include_the_minimap_surface(self):
        self.assertEqual(DISP_SRC.count('#include "config_mapminimap.hpp"'), 2)

    def test_every_reachable_array_matches_config_mapcolors(self):
        for field in self.REACH_ARRAYS:
            with self.subTest(field=field):
                self.assertEqual(
                    _array_of(MINI_SRC, field), _array_of(COL_SRC, field), field
                )

    def test_every_reachable_scalar_matches_config_mapcolors(self):
        for field in self.REACH_SCALARS:
            with self.subTest(field=field):
                self.assertEqual(
                    _scalar_of(MINI_SRC, field), _scalar_of(COL_SRC, field), field
                )

    def test_the_label_font_matches_config_mapcolors(self):
        self.assertEqual(
            _text_of(MINI_SRC, "fontLevel"), _text_of(COL_SRC, "fontLevel")
        )

    def test_no_forced_field_is_set_in_the_minimap_surface(self):
        for field in self.FORCED:
            with self.subTest(field=field):
                self.assertNotRegex(MINI_SRC, rf"\b{re.escape(field)}\s*(\[\])?\s*=")

    def test_the_ceiling_names_every_forced_field(self):
        for field in self.FORCED:
            with self.subTest(field=field):
                self.assertIn(field, MINI_SRC)

    def test_the_probe_asserts_the_new_reach(self):
        probe = (
            REPO
            / "tests"
            / "docker"
            / "missions"
            / "aee_test.Stratis"
            / "aee_p142_map_surface_reach_probe.sqf"
        ).read_text(encoding="utf-8")
        for field in self.REACH_ARRAYS + ("fontLevel",) + self.REACH_SCALARS:
            with self.subTest(field=field):
                self.assertIn(f'["{field}",', probe)


class TestMapMutationProofs(unittest.TestCase):
    """Each new kernel and each new config value is pinned so that one source
    mutation turns exactly one check red.

    A value test proves the shipped value.  These tests prove the suite is
    sensitive to the source.  Each applies one mutation to the real SQF or the
    real config, in memory, and shows the pinned check would fail.  The shipped
    file is never written.  The plan evidence records the same red-to-green,
    run by hand.
    """

    def _mutated_kernel(self, path, args, mutate):
        source = path.read_text(encoding="utf-8")
        mutated = mutate(source)
        self.assertNotEqual(source, mutated, "the mutation anchor must be present")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / path.name
            out.write_text(mutated, encoding="utf-8")
            return run_sqf(out, args, {})

    def test_the_icon_kernel_reference_size_is_pinned(self):
        # The formula divides by the reference world size 8192.  A drift to
        # 8000 changes the pixel result, so the pinned 10.0 catches it.
        def mutate(source):
            return source.replace(
                "6.4 * _worldSize / 8192", "6.4 * _worldSize / 8000", 1
            )

        drifted = self._mutated_kernel(ICON_WORLD_SIZE_KERNEL, [64, 8192, 1.0], mutate)
        self.assertNotEqual(drifted, 10.0)
        self.assertAlmostEqual(drifted, 64 / (6.4 * 8192 / 8000 * 1.0))
        self.assertEqual(run_sqf(ICON_WORLD_SIZE_KERNEL, [64, 8192, 1.0], {}), 10.0)

    def test_the_killed_kernel_marker_field_is_pinned(self):
        # The last-known spec copies field 1, the marker type.  A drift to
        # field 0 returns the affiliation, so the pinned marker type catches it.
        def mutate(source):
            return source.replace(
                "_markerType = _spec select 1;", "_markerType = _spec select 0;", 1
            )

        spec = ["friend", "AEE_b_inf", "ColorWEST", "squad"]
        drifted = self._mutated_kernel(KILLED_MARKER_KERNEL, [spec], mutate)
        self.assertEqual(drifted[1], "friend")
        self.assertNotEqual(drifted[1], "AEE_b_inf")
        self.assertEqual(run_sqf(KILLED_MARKER_KERNEL, [spec], {})[1], "AEE_b_inf")

    def test_the_zoom_range_pin_is_mutation_sensitive(self):
        # The zoom-range pin is a config string.  A changed scaleMax removes
        # the pinned string, so the shipped pin catches a drift.
        self.assertIn("scaleMax = 2;", COL_SRC)
        mutated = COL_SRC.replace("scaleMax = 2;", "scaleMax = 5;", 1)
        self.assertNotEqual(mutated, COL_SRC, "the mutation anchor must be present")
        self.assertNotIn("scaleMax = 2;", mutated)

    def test_the_minimap_reach_pin_is_mutation_sensitive(self):
        # The minimap reach pin ties MINI_SRC to COL_SRC.  A changed value in
        # the minimap file breaks the tie, so the shipped pin catches a drift.
        self.assertEqual(
            _scalar_of(MINI_SRC, "shadedSea"), _scalar_of(COL_SRC, "shadedSea")
        )
        mutated = MINI_SRC.replace("shadedSea = 1;", "shadedSea = 0;", 1)
        self.assertNotEqual(mutated, MINI_SRC, "the mutation anchor must be present")
        self.assertNotEqual(
            _scalar_of(mutated, "shadedSea"), _scalar_of(COL_SRC, "shadedSea")
        )


if __name__ == "__main__":
    unittest.main()
