#!/usr/bin/env python3
"""World geographic anchor contract and kernel tests (MGRS wave 1, task 1).

Runs the REAL addons/core/functions/geo/fnc_buildGeoAnchor.sqf through
tools/tests/sqf_lite.py with fixtures that supply the raw CfgWorlds values.

The anchor schema is 9 elements:
  [latCentre, lonCentre, zone, mapSize, lonWest, latSouth, lonEast, latNorth,
   sourceToken]

mapArea[] element order is authoritative from BIS itself.  The shipped
Addons/functions_f/a3/functions_f/Map/fn_posDegtoWorld.sqf reads
  [mapArea select 0, mapArea select 1] -> bottom-left
  [mapArea select 2, mapArea select 3] -> top-right
and passes each pair to bis_fnc_posDegToUTM, whose parameter 0 is longitude
and parameter 1 is latitude.  Therefore
  mapArea = [lonWest, latSouth, lonEast, latNorth].
Re-read from the installed world configs on 2026-10-06.
"""

import json
import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
GEO = ROOT / "addons" / "core" / "functions" / "geo"
BUILD = GEO / "fnc_buildGeoAnchor.sqf"
READER = GEO / "fnc_getGeoAnchor.sqf"
PREP = ROOT / "addons" / "core" / "XEH_PREP.hpp"
INVARIANTS = ROOT / "data" / "consistency" / "position_invariants.json"
EVALUATOR = GEO / "fnc_evaluateGeoConsistency.sqf"
MONITOR = GEO / "fnc_runGeoConsistency.sqf"
POSTINIT = ROOT / "addons" / "core" / "XEH_postInit.sqf"
LATLON = GEO / "fnc_latLonToUtm.sqf"
UTM2LL = GEO / "fnc_utmToLatLon.sqf"
FORMAT = GEO / "fnc_formatMgrs.sqf"
PARSE = GEO / "fnc_parseMgrs.sqf"
WORLD2MGRS = GEO / "fnc_worldToMgrs.sqf"
MGRS2WORLD = GEO / "fnc_mgrsToWorld.sqf"
UTM2WORLD = GEO / "fnc_utmToWorld.sqf"
TABLES = ROOT / "addons" / "core" / "data" / "mgrs_tables.sqf"

# Shipped mapArea values, re-read from the installed game on 2026-10-06.
ALTIS_MAPAREA = [25.011957, 39.718452, 25.481527, 40.094578]  # [lonW,latS,lonE,latN]
TANOA_MAPAREA = [-20.267975, 174.00284, -20.135265, 174.14566]  # stored [lat,lon]


def build(map_size, zone, map_area, lat, lon):
    """Run the real pure builder with the raw CfgWorlds values."""
    return run_sqf(BUILD, [map_size, zone, map_area, lat, lon])


def geo_globals():
    """Inject the real conversion kernels and the generated MGRS table."""
    g = {"aee_core_mgrsTables": run_sqf(TABLES, [])}
    g["__FUNC__latLonToUtm"] = lambda lat, lon: run_sqf(LATLON, [lat, lon])
    g["__FUNC__utmToLatLon"] = lambda e, n, z, h: run_sqf(UTM2LL, [e, n, z, h])
    g["__FUNC__formatMgrs"] = lambda e, n, z, p, lat: run_sqf(
        FORMAT, [e, n, z, p, lat], geo_globals()
    )
    g["__FUNC__parseMgrs"] = lambda text: run_sqf(PARSE, [text], geo_globals())
    g["__FUNC__utmToWorld"] = lambda e, n, z, h, a: run_sqf(
        UTM2WORLD, [e, n, z, h, a], geo_globals()
    )
    return g


def world_to_mgrs(position, anchor, precision=10):
    return run_sqf(WORLD2MGRS, [position, anchor, precision], geo_globals())


def mgrs_to_world(text, anchor):
    return run_sqf(MGRS2WORLD, [text, anchor], geo_globals())


# The Altis anchor from the box in its shipped config (task 1).
ALTIS_ANCHOR = build(30720, 35, ALTIS_MAPAREA, -35.152, 16.661)


class TestBuildGeoAnchor(unittest.TestCase):
    def test_schema_length_is_nine(self):
        anchor = build(30720, 35, ALTIS_MAPAREA, -35.152, 16.661)
        self.assertEqual(len(anchor), 9)

    def test_altis_uses_map_area_centre(self):
        anchor = build(30720, 35, ALTIS_MAPAREA, -35.152, 16.661)
        self.assertEqual(anchor[8], "mapArea")
        self.assertAlmostEqual(anchor[0], (39.718452 + 40.094578) / 2, places=6)
        self.assertAlmostEqual(anchor[1], (25.011957 + 25.481527) / 2, places=6)
        self.assertEqual(anchor[2], 35)
        self.assertEqual(anchor[3], 30720)
        self.assertAlmostEqual(anchor[4], 25.011957, places=6)
        self.assertAlmostEqual(anchor[5], 39.718452, places=6)
        self.assertAlmostEqual(anchor[6], 25.481527, places=6)
        self.assertAlmostEqual(anchor[7], 40.094578, places=6)

    def test_element_order_is_longitude_then_latitude(self):
        # Reading the box as [lat,lon,...] would place Altis near 25 N 40 E.
        # The centre equals the mean of the boxed lon/lat pair only when the
        # order is [lon,lat,lon,lat].
        anchor = build(30720, 35, ALTIS_MAPAREA, -35.152, 16.661)
        self.assertAlmostEqual(anchor[0], 39.906515, places=6)  # latitude
        self.assertAlmostEqual(anchor[1], 25.246742, places=6)  # longitude

    def test_absent_box_falls_back_to_cfgworlds(self):
        anchor = build(8192, 35, [], -35.097, 16.482)
        self.assertEqual(anchor[8], "cfgworlds")
        self.assertAlmostEqual(anchor[0], 35.097, places=3)  # negate BIS key
        self.assertAlmostEqual(anchor[1], 16.482, places=3)
        self.assertEqual(anchor[2], 35)
        self.assertEqual(anchor[3], 8192)
        self.assertEqual(anchor[4:8], [0, 0, 0, 0])

    def test_stale_keys_not_used_when_box_present(self):
        # Altis's latitude/longitude keys are stale (16.661 E, 35.152 N); with
        # mapArea present the anchor must use the box, not the keys.
        anchor = build(30720, 35, ALTIS_MAPAREA, -35.152, 16.661)
        self.assertEqual(anchor[8], "mapArea")
        self.assertNotAlmostEqual(anchor[0], 35.152, places=3)
        self.assertNotAlmostEqual(anchor[1], 16.661, places=3)

    def test_degenerate_box_falls_back(self):
        # A zero-area box (west == east) is not usable.
        anchor = build(30720, 35, [25.0, 39.0, 25.0, 40.0], -35.152, 16.661)
        self.assertEqual(anchor[8], "cfgworlds")

    def test_out_of_range_latitude_falls_back(self):
        # Tanoa ships mapArea as [lat,lon]; read in the authoritative
        # [lon,lat] order its latitude is ~174, which is not a latitude, so
        # Tanoa falls back to the CfgWorlds keys.
        anchor = build(15360, 60, TANOA_MAPAREA, 17.698, 178.783)
        self.assertEqual(anchor[8], "cfgworlds")
        self.assertAlmostEqual(anchor[0], -17.698, places=3)
        self.assertAlmostEqual(anchor[1], 178.783, places=3)

    def test_zero_latitude_falls_back_temperate(self):
        anchor = build(0, 0, [], 0, 0)
        self.assertEqual(anchor[8], "cfgworlds")
        self.assertEqual(anchor[0], 40)
        self.assertEqual(anchor[1], 0)
        self.assertEqual(anchor[2], 0)
        self.assertEqual(anchor[3], 0)


class TestGeoAnchorSourceContract(unittest.TestCase):
    def test_preps_registration(self):
        prep = PREP.read_text(encoding="utf-8")
        self.assertIn("PREPS(geo,buildGeoAnchor)", prep)
        self.assertIn("PREPS(geo,getGeoAnchor)", prep)

    def test_builder_records_authoritative_order(self):
        src = BUILD.read_text(encoding="utf-8")
        self.assertIn("[lonWest, latSouth, lonEast, latNorth]", src)
        self.assertIn("fn_posDegtoWorld", src)

    def test_reader_publishes_anchor_and_calls_builder(self):
        src = READER.read_text(encoding="utf-8")
        # Assert the CALL FORM, not the bare name, which also sits in comments.
        self.assertIn("call FUNC(buildGeoAnchor)", src)
        # Assert the PUBLISH FORM, not the bare name, which also sits in the
        # header comment ("published as aee_core_geoAnchor").
        self.assertIn('setVariable ["aee_core_geoAnchor"', src)
        # The anchor is cached under QGVAR(geoAnchor) so the reads happen once.
        self.assertIn("QGVAR(geoAnchor)", src)
        self.assertIn('configFile >> "CfgWorlds" >> worldName', src)


class TestWorldToMgrs(unittest.TestCase):
    def test_anchor_centre_maps_to_anchor_lat_lon(self):
        # The world centre is the box centre; the projected latitude and
        # longitude must be exactly the anchor centre.
        anchor = ALTIS_ANCHOR
        result = world_to_mgrs([anchor[3] / 2, anchor[3] / 2, 0], anchor)
        self.assertAlmostEqual(result[1], anchor[0], places=6)
        self.assertAlmostEqual(result[2], anchor[1], places=6)

    def test_returns_mgrs_and_intermediates(self):
        result = world_to_mgrs([10000, 20000, 0], ALTIS_ANCHOR)
        self.assertEqual(len(result), 6)
        self.assertIsInstance(result[0], str)
        self.assertEqual(result[0][:3], "35S")
        self.assertEqual(result[5], 35)
        # The intermediates lead the reported easting and northing.
        self.assertGreater(result[3], 100000)
        self.assertGreater(result[4], 1000000)

    def test_world_to_mgrs_to_world_within_one_metre(self):
        anchor = ALTIS_ANCHOR
        for x, y in [
            (15360, 15360),
            (10000, 20000),
            (0, 0),
            (30720, 30720),
            (20000, 5000),
            (7840, 22000),
        ]:
            written = world_to_mgrs([x, y, 0], anchor)
            back = mgrs_to_world(written[0], anchor)
            self.assertLess(
                math.dist((x, y), (back[0], back[1])),
                1.0,
                f"round trip {x},{y} drifted to {back[0]},{back[1]}",
            )

    def test_no_box_anchor_maps_world_centre_to_anchor_centre(self):
        # A usable box is absent, so the tangent plane at the centre applies.
        # The fallback uses the SAME convention as the box branch: the world
        # centre (mapSize/2, mapSize/2) maps to the anchor centre.  The old
        # origin convention put every fallback world out by mapSize/2 metres.
        anchor = build(8192, 35, [], -35.097, 16.482)
        result = world_to_mgrs([anchor[3] / 2, anchor[3] / 2, 0], anchor)
        self.assertEqual(len(result), 6)
        self.assertIsInstance(result[0], str)
        self.assertAlmostEqual(result[1], anchor[0], places=6)
        self.assertAlmostEqual(result[2], anchor[1], places=6)

    def test_no_box_anchor_round_trips_the_world_centre(self):
        # The forward and inverse tangent planes apply the same offset, so the
        # world centre round-trips inside the MGRS square diagonal.
        anchor = build(8192, 35, [], -35.097, 16.482)
        centre = [anchor[3] / 2, anchor[3] / 2, 0]
        written = world_to_mgrs(centre, anchor)
        back = mgrs_to_world(written[0], anchor)
        self.assertLess(math.dist((centre[0], centre[1]), (back[0], back[1])), 1.5)


class TestUtmToWorld(unittest.TestCase):
    """fnc_utmToWorld, executed: a UTM coordinate to world through the box."""

    def test_world_to_utm_to_world_round_trips(self):
        anchor = ALTIS_ANCHOR
        hemisphere = "north" if anchor[0] >= 0 else "south"
        for x, y in [
            (15360, 15360),
            (10000, 20000),
            (20000, 5000),
            (7840, 22000),
        ]:
            written = world_to_mgrs([x, y, 0], anchor)
            back = run_sqf(
                UTM2WORLD,
                [written[3], written[4], written[5], hemisphere, anchor],
                geo_globals(),
            )
            self.assertLess(
                math.dist((x, y), (back[0], back[1])),
                0.001,
                f"utm round trip {x},{y} drifted",
            )

    def test_a_bad_anchor_returns_the_origin(self):
        back = run_sqf(UTM2WORLD, [350134.0, 4418852.0, 35, "north", []], geo_globals())
        self.assertEqual(back, [0, 0, 0])


class TestWorldToMgrsSourceContract(unittest.TestCase):
    def test_preps_registration(self):
        prep = PREP.read_text(encoding="utf-8")
        self.assertIn("PREPS(geo,worldToMgrs)", prep)
        self.assertIn("PREPS(geo,mgrsToWorld)", prep)
        self.assertIn("PREPS(geo,utmToWorld)", prep)

    def test_mgrs_to_world_reuses_the_utm_kernel(self):
        src = MGRS2WORLD.read_text(encoding="utf-8")
        # The box inverse is shared, so the two conversions cannot drift.
        self.assertIn("call FUNC(utmToWorld)", src)

    def test_world_to_mgrs_chains_the_kernels(self):
        src = WORLD2MGRS.read_text(encoding="utf-8")
        # Assert the CALL FORM; the bare names also sit in the comments.
        self.assertIn("call FUNC(latLonToUtm)", src)
        self.assertIn("call FUNC(formatMgrs)", src)

    def test_mgrs_to_world_reverses_the_chain(self):
        src = MGRS2WORLD.read_text(encoding="utf-8")
        self.assertIn("call FUNC(parseMgrs)", src)
        self.assertIn("call FUNC(utmToWorld)", src)


# ── Position consistency table and evaluator (task 14) ─────────────────────

ALLOWED_PREDICATES = {"pairs_equal", "agree_within"}


def load_invariants_json():
    return json.loads(INVARIANTS.read_text(encoding="utf-8"))


def table_for_sqf(data):
    """The JSON rows in the SQF row order the evaluator reads."""
    rows = []
    for row in data["rows"]:
        rows.append(
            [
                row["id"],
                row["name"],
                row["predicate"],
                row["inputs"],
                row["pairs"],
                row["tolerance"] if row["tolerance"] is not None else 0,
                row["severity"],
                row["grade"],
                row["note"],
            ]
        )
    return rows


def evaluate(values, table=None):
    """Run the REAL pure evaluator through the harness."""
    if table is None:
        table = table_for_sqf(load_invariants_json())
    return run_sqf(EVALUATOR, [table, values])


def monitor_supplied_keys():
    """The value-map keys the monitor supplies (keys bound to a variable)."""
    src = MONITOR.read_text(encoding="utf-8")
    block = src.split("private _values = [", 1)[1].split("\n];", 1)[0]
    return set(re.findall(r'\["([A-Za-z0-9_]+)",\s*_', block))


def monitor_row_tolerance(row_id):
    """The tolerance literal of one monitor table row, read from the SQF."""
    src = MONITOR.read_text(encoding="utf-8")
    after = src.split(f'"{row_id}"', 1)[1]
    match = re.search(r"\n\s*([0-9]+\.[0-9]+),", after)
    return float(match.group(1))


def strip_sqf_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


CONSISTENT_VALUES = [
    ["engineGridCentre", "024577"],
    ["engineGridFromMgrs", "024577"],
    ["anchorLat", 39.906515],
    ["anchorLon", 25.246742],
    ["projectedLat", 39.906515],
    ["projectedLon", 25.246742],
    ["worldLocationLat", 39.906515],
    ["worldLocationLon", 25.246742],
    ["centreX", 15360.0],
    ["centreY", 15360.0],
    ["roundtripX", 15360.0],
    ["roundtripY", 15360.0],
    ["easting", 501341.0],
    ["northing", 4418852.0],
    ["parsedEasting", 501341.0],
    ["parsedNorthing", 4418852.0],
]


def divergent_values():
    values = [list(pair) for pair in CONSISTENT_VALUES]
    for pair in values:
        if pair[0] == "roundtripX":
            pair[1] = 99999.0
        elif pair[0] == "engineGridFromMgrs":
            pair[1] = "099999"
        elif pair[0] == "worldLocationLat":
            pair[1] = 40.5
    return values


class TestPositionInvariantTable(unittest.TestCase):
    """Every row and every referenced variable (task 14 acceptance)."""

    def test_four_invariants_declared(self):
        data = load_invariants_json()
        ids = [row["id"] for row in data["rows"]]
        self.assertEqual(
            ids, ["GRID-AGREE", "ANCHOR-CENTRE", "WORLDLOC-ANCHOR", "MGRS-ROUNDTRIP"]
        )

    def test_every_row_has_all_fields(self):
        for row in load_invariants_json()["rows"]:
            for field in (
                "id",
                "name",
                "predicate",
                "inputs",
                "pairs",
                "tolerance",
                "severity",
                "grade",
                "note",
            ):
                self.assertIn(field, row, f"{row.get('id')} missing {field}")

    def test_every_predicate_is_allowed(self):
        for row in load_invariants_json()["rows"]:
            self.assertIn(row["predicate"], ALLOWED_PREDICATES, row["id"])

    def test_every_input_key_is_wellformed_and_pairs_reference_inputs(self):
        for row in load_invariants_json()["rows"]:
            for key in row["inputs"]:
                self.assertRegex(key, r"^[A-Za-z][A-Za-z0-9_]*$", row["id"])
            for key_a, key_b in row["pairs"]:
                self.assertIn(key_a, row["inputs"], row["id"])
                self.assertIn(key_b, row["inputs"], row["id"])

    def test_ids_are_unique(self):
        ids = [row["id"] for row in load_invariants_json()["rows"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_tolerance_is_number_or_null(self):
        for row in load_invariants_json()["rows"]:
            self.assertTrue(
                row["tolerance"] is None or isinstance(row["tolerance"], (int, float)),
                row["id"],
            )

    def test_anchor_centre_tolerance_covers_the_32_bit_float_error(self):
        # The builder computes (latSouth+latNorth)/2 and the projector computes
        # latSouth + 0.5*(latNorth-latSouth).  Algebraically equal, but the
        # engine's 32-bit floats leave them about one ULP apart, ~2e-6 deg at
        # latitude 40.  A 1e-6 tolerance is falsely RED on a correctly mapped
        # world (Altis too), so the row carries the demonstrated 1e-4 margin.
        data = load_invariants_json()
        row = next(r for r in data["rows"] if r["id"] == "ANCHOR-CENTRE")
        self.assertGreaterEqual(row["tolerance"], 1e-4)
        self.assertEqual(monitor_row_tolerance("ANCHOR-CENTRE"), row["tolerance"])

    def test_world_location_tolerance_stays_at_the_anchor_resolution(self):
        # WORLDLOC-ANCHOR compares two values written from the same anchor, so
        # it is bit-identical and keeps the 1e-6 resolution.
        data = load_invariants_json()
        row = next(r for r in data["rows"] if r["id"] == "WORLDLOC-ANCHOR")
        self.assertEqual(row["tolerance"], 1e-6)

    def test_every_referenced_variable_is_supplied_by_monitor(self):
        declared = set()
        for row in load_invariants_json()["rows"]:
            declared.update(row["inputs"])
        self.assertEqual(declared, monitor_supplied_keys())

    def test_monitor_carries_every_row_id_and_predicate(self):
        src = MONITOR.read_text(encoding="utf-8")
        for row in load_invariants_json()["rows"]:
            self.assertIn(f'"{row["id"]}"', src)
            self.assertIn(f'"{row["predicate"]}"', src)


class TestGeoConsistencyEvaluatorContract(unittest.TestCase):
    """The evaluator is pure; the monitor publishes and is wired."""

    def test_evaluator_reads_no_mission_state(self):
        src = strip_sqf_comments(EVALUATOR.read_text(encoding="utf-8"))
        # The call form, not a bare name in a comment.
        self.assertNotIn("missionNamespace", src)
        self.assertNotIn("getVariable", src)

    def test_evaluator_takes_table_and_values(self):
        src = EVALUATOR.read_text(encoding="utf-8")
        self.assertIn('["_table", [], [[]]]', src)
        self.assertIn('["_values", [], [[]]]', src)

    def test_preps_registration(self):
        prep = PREP.read_text(encoding="utf-8")
        self.assertIn("PREPS(geo,evaluateGeoConsistency)", prep)
        self.assertIn("PREPS(geo,runGeoConsistency)", prep)

    def test_monitor_calls_the_evaluator(self):
        src = MONITOR.read_text(encoding="utf-8")
        self.assertIn("call FUNC(evaluateGeoConsistency)", src)

    def test_monitor_publishes_the_flag(self):
        src = MONITOR.read_text(encoding="utf-8")
        self.assertIn('"aee_core_positionDivergence"', src)

    def test_monitor_is_wired_into_postinit(self):
        src = POSTINIT.read_text(encoding="utf-8")
        self.assertIn("call FUNC(runGeoConsistency)", src)


class TestGeoConsistencyEvaluatorBehaviour(unittest.TestCase):
    """Per-row verdicts from the real evaluator."""

    def test_consistent_map_passes_with_no_divergence(self):
        divergence, verdicts = evaluate(CONSISTENT_VALUES)
        self.assertFalse(divergence)
        self.assertEqual(len(verdicts), 4)
        for verdict in verdicts:
            self.assertTrue(verdict[1], f"{verdict[0]} should pass: {verdict[2]}")

    def test_divergent_map_flags_and_names_the_failing_rows(self):
        divergence, verdicts = evaluate(divergent_values())
        self.assertTrue(divergence)
        failed = {v[0] for v in verdicts if not v[1]}
        self.assertEqual(failed, {"GRID-AGREE", "WORLDLOC-ANCHOR", "MGRS-ROUNDTRIP"})
        # The agreeing row stays green.
        for verdict in verdicts:
            if verdict[0] == "ANCHOR-CENTRE":
                self.assertTrue(verdict[1])

    def test_single_divergent_pair_fails_exactly_one_row(self):
        values = [list(pair) for pair in CONSISTENT_VALUES]
        for pair in values:
            if pair[0] == "roundtripY":
                pair[1] = 20000.0
        divergence, verdicts = evaluate(values)
        self.assertTrue(divergence)
        failed = [v[0] for v in verdicts if not v[1]]
        self.assertEqual(failed, ["MGRS-ROUNDTRIP"])

    def test_anchor_centre_passes_at_the_32_bit_float_offset(self):
        # Simulate the engine's 32-bit centre difference of about 2e-6 degrees.
        # The old 1e-6 tolerance made this correctly mapped row falsely RED.
        values = [list(pair) for pair in CONSISTENT_VALUES]
        for pair in values:
            if pair[0] == "projectedLat":
                pair[1] = pair[1] - 0.000002
        divergence, verdicts = evaluate(values)
        row = next(v for v in verdicts if v[0] == "ANCHOR-CENTRE")
        self.assertTrue(row[1], row[2])

    def test_missing_value_is_a_divergence(self):
        values = [pair for pair in CONSISTENT_VALUES if pair[0] != "northing"]
        divergence, verdicts = evaluate(values)
        self.assertTrue(divergence)
        failed = {v[0] for v in verdicts if not v[1]}
        self.assertIn("MGRS-ROUNDTRIP", failed)


if __name__ == "__main__":
    unittest.main()
