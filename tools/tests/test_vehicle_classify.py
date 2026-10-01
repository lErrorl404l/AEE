#!/usr/bin/env python3
"""Vehicle property band classifier tests (dynamic vehicle identity, wave 3).

The band table is generated from the sourced catalogue by
``tools/validation/gen_vehicle_data.py``. The classifier
``addons/mobility/functions/fnc_classifyVehicle.sqf`` reads the table and the
live engine properties. The engine calls cannot run in this harness, so the
band selection and the tie rule are mirrored here in Python and pinned against
the same table the SQF reads. The SQF source is checked structurally for the
route order, the token order, the return shape and the function registration.

The mirror reads the table only. It is not a second authority: the committed
band table is proven equal to a fresh render, so the mirror and the SQF always
select over the same rows.

Run: python3 -m unittest tools.tests.test_vehicle_classify -v
"""

from __future__ import annotations

import ast
import contextlib
import io
import re
import sys
import unittest
from collections.abc import Sequence
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_vehicle_data as gen  # noqa: E402

FUNCTIONS = REPO / "addons" / "mobility" / "functions"
BANDS_PATH = FUNCTIONS / "fnc_getVehicleBands.sqf"
CLASSIFY_PATH = FUNCTIONS / "fnc_classifyVehicle.sqf"
WRAPPER_PATH = FUNCTIONS / "fnc_estimateVehicleMass.sqf"
PREP_PATH = REPO / "addons" / "mobility" / "XEH_PREP.hpp"

BANDS = BANDS_PATH.read_text(encoding="utf-8")
CLASSIFY = CLASSIFY_PATH.read_text(encoding="utf-8")

# The seven band columns.
BAND_COLUMNS = 7
COL_ID = 0
COL_TYPE = 1
COL_TRACKED = 2
COL_MASS = 3
COL_LENGTH = 4
COL_WIDTH = 5
COL_HEIGHT = 6

# The classifier routes, strongest first.
ROUTES = ("corpus", "band", "token", "none")

# The engine ground tokens, most specific first. This order is the
# fnc_calculateSSF track-table precedent.
GROUND_TOKENS = (
    "MRAP",
    "Wheeled_APC",
    "Tank",
    "Tracked_APC",
    "Car",
    "Truck",
    "Wheeled_APC_F",
)


def table_body(text: str = BANDS) -> str:
    """Return the rendered band rows between the assignment and the close."""
    match = re.search(r"private _table = \[(.*?)\n\];", text, re.S)
    if match is None:
        raise AssertionError("the generated band table is missing")
    return match.group(1)


def parse_bands(text: str = BANDS) -> list[list[object]]:
    """Parse the committed band rows. SQF numeric arrays are Python literals."""
    body = table_body(text)
    parsed = ast.literal_eval("[" + body + "]")
    assert isinstance(parsed, list)
    return parsed


def select_band(
    rows: Sequence[Sequence[object]],
    vehicle_type: str,
    mass_kg: float,
    length_mm: float,
    width_mm: float,
    height_mm: float,
) -> list[object] | None:
    """Mirror the SQF band selection: type, then nearest mass, then extent.

    A zero mass selects nothing, because the engine mass is the selector and a
    zero means it was not read. The nearest weight keeps the rows at the
    smallest mass distance. The nearest extent keeps the rows at the smallest
    extent distance. A tie at the extent selects no row, so the classifier
    never guesses between two catalogue entries.
    """
    if mass_kg <= 0:
        return None
    typed = [row for row in rows if row[COL_TYPE] == vehicle_type and row[COL_MASS] > 0]
    if not typed:
        return None
    min_mass = min(abs(float(row[COL_MASS]) - mass_kg) for row in typed)
    near = [row for row in typed if abs(float(row[COL_MASS]) - mass_kg) == min_mass]
    scored: list[tuple[float, list[object]]] = []
    for row in near:
        extent = 0.0
        if row[COL_LENGTH] > 0 and length_mm > 0:
            extent += abs(float(row[COL_LENGTH]) - length_mm)
        if row[COL_WIDTH] > 0 and width_mm > 0:
            extent += abs(float(row[COL_WIDTH]) - width_mm)
        if row[COL_HEIGHT] > 0 and height_mm > 0:
            extent += abs(float(row[COL_HEIGHT]) - height_mm)
        scored.append((extent, list(row)))
    min_extent = min(score for score, _row in scored)
    winners = [row for score, row in scored if score == min_extent]
    return winners[0] if len(winners) == 1 else None


def row(
    catalogue_id: str,
    vehicle_type: str = "tracked",
    mass: float = 10000,
    length: float = 6000,
    width: float = 3000,
    height: float = 2500,
) -> list[object]:
    """One synthetic band row. Fixture only, one sentinel per field."""
    return [
        catalogue_id,
        vehicle_type,
        1 if vehicle_type == "tracked" else 0,
        mass,
        length,
        width,
        height,
    ]


class GeneratedBandTableTest(unittest.TestCase):
    """The committed band table is a fresh, complete projection."""

    def test_the_table_is_marked_generated(self) -> None:
        self.assertIn("GENERATED", BANDS)
        self.assertIn("gen_vehicle_data.py", BANDS)
        self.assertIn("aee_mobility_fnc_getVehicleBands", BANDS)

    def test_the_header_states_the_column_contract(self) -> None:
        header = BANDS.split("*/", 1)[0]
        for token in (
            "catalogue_id",
            "vehicle_type",
            "is_tracked",
            "mass_kg",
            "length_mm",
            "width_mm",
            "height_mm",
        ):
            self.assertIn(token, header, f"the header does not state {token}")

    def test_the_committed_table_equals_a_fresh_render(self) -> None:
        fresh = gen.render_bands(gen.load_band_rows(gen.DEFAULT_DATA))
        self.assertEqual(BANDS, fresh, "fnc_getVehicleBands is stale")

    def test_the_freshness_gate_passes(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(gen.check_outputs(gen.DEFAULT_DATA), 0)

    def test_the_table_carries_one_row_per_catalogue_entry(self) -> None:
        parsed = parse_bands()
        names = {str(item[COL_ID]) for item in parsed}
        self.assertEqual(len(names), len(parsed), "a catalogue id repeats")
        # One row per catalogue entry, and the fresh render pins the exact set.
        self.assertEqual(len(parsed), len(gen.load_band_rows(gen.DEFAULT_DATA)))

    def test_every_row_has_seven_columns(self) -> None:
        for item in parse_bands():
            self.assertEqual(len(item), BAND_COLUMNS, item)

    def test_the_rows_are_sorted_by_catalogue_id(self) -> None:
        names = [str(item[COL_ID]) for item in parse_bands()]
        self.assertEqual(names, sorted(names))

    def test_the_tracked_flag_follows_the_vehicle_type(self) -> None:
        for item in parse_bands():
            expected = 1 if item[COL_TYPE] == "tracked" else 0
            self.assertEqual(item[COL_TRACKED], expected, item[COL_ID])

    def test_every_mass_is_the_resolved_operating_weight(self) -> None:
        # The band mass is the catalogue resolution: a held value or a named
        # derivation. It is never a raw engine value.
        load = gen.catalogue.load(gen.DEFAULT_DATA)
        by_id = {entry.catalogue_id: entry for entry in load.entries}
        for item in parse_bands():
            entry = by_id[str(item[COL_ID])]
            resolved = gen.catalogue.resolve_field(entry.values, "operating_weight_kg")
            self.assertEqual(float(item[COL_MASS]), float(resolved.value), item[COL_ID])

    def test_the_table_reads_no_engine_call(self) -> None:
        self.assertNotIn("getMass", BANDS)
        self.assertNotIn("boundingBoxReal", BANDS)
        self.assertNotIn("isKindOf", BANDS)


class BandSelectionTest(unittest.TestCase):
    """The mirrored selection: type, nearest weight, nearest extent, tie rule."""

    def test_the_nearest_weight_wins_even_with_a_poor_extent(self) -> None:
        rows = [
            row("far", mass=20000, length=100),
            row("near", mass=10100, length=9000),
        ]
        chosen = select_band(rows, "tracked", 10000, 6000, 3000, 2500)
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen[COL_ID], "near")

    def test_the_nearest_extent_breaks_a_weight_tie(self) -> None:
        rows = [
            row("poor", mass=10000, length=9000, width=3000, height=2500),
            row("good", mass=10000, length=6000, width=3000, height=2500),
        ]
        chosen = select_band(rows, "tracked", 10000, 6000, 3000, 2500)
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen[COL_ID], "good")

    def test_an_extent_tie_selects_no_row(self) -> None:
        rows = [
            row("twin_a", mass=10000, length=6000, width=3000, height=2500),
            row("twin_b", mass=10000, length=6000, width=3000, height=2500),
        ]
        self.assertIsNone(select_band(rows, "tracked", 10000, 6000, 3000, 2500))

    def test_a_weight_tie_with_one_extent_winner_is_not_a_tie(self) -> None:
        # Two rows at the nearest weight. Only one matches the extent.
        rows = [
            row("twin_a", mass=10000, length=6000, width=3000, height=2500),
            row("twin_b", mass=10000, length=6100, width=3000, height=2500),
        ]
        chosen = select_band(rows, "tracked", 10000, 6000, 3000, 2500)
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen[COL_ID], "twin_a")

    def test_the_vehicle_type_filters_the_rows(self) -> None:
        rows = [
            row("wheel", vehicle_type="wheeled", mass=10000),
            row("track", vehicle_type="tracked", mass=10000),
        ]
        chosen = select_band(rows, "wheeled", 10000, 6000, 3000, 2500)
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen[COL_ID], "wheel")

    def test_a_zero_engine_mass_selects_nothing(self) -> None:
        rows = [row("any", mass=10000)]
        self.assertIsNone(select_band(rows, "tracked", 0, 6000, 3000, 2500))

    def test_a_row_with_no_mass_is_skipped(self) -> None:
        rows = [row("absent", mass=0), row("held", mass=10000)]
        chosen = select_band(rows, "tracked", 10000, 6000, 3000, 2500)
        self.assertIsNotNone(chosen)
        assert chosen is not None
        self.assertEqual(chosen[COL_ID], "held")

    def test_a_row_with_no_extents_falls_to_a_zero_extent(self) -> None:
        # The live extents are unread, so every near row scores zero. Two rows
        # then tie and the selection refuses a guess.
        rows = [
            row("bare_a", mass=10000, length=0, width=0, height=0),
            row("bare_b", mass=10000, length=0, width=0, height=0),
        ]
        self.assertIsNone(select_band(rows, "tracked", 10000, 0, 0, 0))

    def test_the_real_corpus_selects_the_nearest_tracked_mass(self) -> None:
        rows = parse_bands()
        # The M1 Abrams holds 62000 kg. A live mass of 62000 tracked must
        # select a real tracked row, and the row must be the nearest in mass.
        chosen = select_band(rows, "tracked", 62000, 9800, 3700, 2900)
        self.assertIsNotNone(chosen)
        assert chosen is not None
        nearest = min(
            abs(float(item[COL_MASS]) - 62000)
            for item in rows
            if item[COL_TYPE] == "tracked" and item[COL_MASS] > 0
        )
        self.assertEqual(abs(float(chosen[COL_MASS]) - 62000), nearest)


class ClassifierSourceTest(unittest.TestCase):
    """The SQF source states the routes, the tie rule and the return shape."""

    def test_the_file_names_itself(self) -> None:
        self.assertIn("aee_mobility_fnc_classifyVehicle", CLASSIFY)

    def test_the_return_is_the_documented_nine_element_array(self) -> None:
        self.assertIn(
            "[_classToken, _vehicleType, _tracked, _hasTurret, _massKg, "
            "_lengthM, _widthM, _heightM, _matchedBy]",
            CLASSIFY,
        )

    def test_the_corpus_route_runs_first(self) -> None:
        self.assertIn("call FUNC(getVehicleMatch)", CLASSIFY)
        corpus = CLASSIFY.index('_matchedBy = "corpus";')
        band = CLASSIFY.index('_matchedBy = "band";')
        token = CLASSIFY.index('_matchedBy = "token";')
        self.assertLess(corpus, band)
        self.assertLess(band, token)

    def test_the_band_route_reads_the_generated_table(self) -> None:
        self.assertIn("call FUNC(getVehicleBands)", CLASSIFY)
        self.assertIn("_minMass", CLASSIFY)
        self.assertIn("_minExtent", CLASSIFY)
        self.assertIn("_hits", CLASSIFY)

    def test_the_band_route_selects_only_a_unique_row(self) -> None:
        self.assertIn("if ((_hits == 1) && (_best isNotEqualTo [])) then", CLASSIFY)

    def test_the_token_order_is_most_specific_first(self) -> None:
        block = CLASSIFY.index("private _groundTokens = [")
        tail = CLASSIFY[block:]
        positions = [tail.index(f'"{token}"') for token in GROUND_TOKENS]
        self.assertEqual(positions, sorted(positions))

    def test_the_classifier_reads_the_live_properties(self) -> None:
        for call in (
            "getMass _vehicle",
            "boundingBoxReal _vehicle",
            "allTurrets _vehicle",
        ):
            self.assertIn(call, CLASSIFY)

    def test_the_classifier_reads_no_source_registry(self) -> None:
        self.assertNotIn("sources.json", CLASSIFY)

    def test_the_classifier_is_registered_once(self) -> None:
        prep = PREP_PATH.read_text(encoding="utf-8")
        hits = [line for line in prep.splitlines() if "classifyVehicle" in line]
        self.assertEqual(hits, ["PREP(classifyVehicle);"])

    def test_the_band_table_function_is_registered_once(self) -> None:
        prep = PREP_PATH.read_text(encoding="utf-8")
        hits = [line for line in prep.splitlines() if "getVehicleBands" in line]
        self.assertEqual(hits, ["PREP(getVehicleBands);"])


class ConsumerWiringTest(unittest.TestCase):
    """The mass estimator sources its tracked flag from the classifier."""

    def test_the_wrapper_calls_the_classifier(self) -> None:
        wrapper = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertIn("call FUNC(classifyVehicle)", wrapper)

    def test_the_wrapper_passes_its_held_match(self) -> None:
        wrapper = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertIn("[_vehicle, _match] call FUNC(classifyVehicle)", wrapper)

    def test_the_wrapper_keeps_the_type_marker(self) -> None:
        # The mass-class tests locate their region by this exact line.
        wrapper = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertIn('private _vehicleType = "wheeled";', wrapper)

    def test_the_wrapper_no_longer_runs_the_ad_hoc_check(self) -> None:
        wrapper = WRAPPER_PATH.read_text(encoding="utf-8")
        self.assertNotIn(
            'if (_vehicle isKindOf "Tank" || {_vehicle isKindOf "Tracked_APC"}) then {',
            wrapper,
        )


class BandTableFunctionTest(unittest.TestCase):
    """The band table function returns the table and nothing else."""

    def test_the_function_returns_the_table(self) -> None:
        self.assertTrue(BANDS.rstrip().endswith("_table"))

    def test_the_function_holds_no_logic(self) -> None:
        # The generated file is data. It has no control flow and no engine call.
        body = BANDS.split("*/", 1)[-1]
        for token in ("if (", "forEach", "call ", "params", "isKindOf"):
            self.assertNotIn(token, body, f"the band table holds {token}")


if __name__ == "__main__":
    unittest.main()
