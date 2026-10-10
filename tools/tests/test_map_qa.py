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

import re
import sys
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

MATRIX_SRC = MATRIX.read_text(encoding="utf-8")
MARKERS_SRC = MARKERS_HPP.read_text(encoding="utf-8")
LOC_SRC = LOC_HPP.read_text(encoding="utf-8")
ADR030_SRC = ADR030.read_text(encoding="utf-8")
TOPO_SURFACE_SRC = TOPO_SURFACE.read_text(encoding="utf-8")
COL_SRC = COL_HPP.read_text(encoding="utf-8")

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


class TestSuiteRegistration(unittest.TestCase):
    def test_the_suite_is_registered(self):
        self.assertIn(
            "tools/tests/test_map_qa.py",
            RUN_TESTS.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
