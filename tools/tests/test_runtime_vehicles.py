#!/usr/bin/env python3
"""Runtime vehicle matcher and lookup tests (vehicle corpus, wave 3 task 9).

The matcher and the lookup are generated from the validated vehicle
catalogue by tools/validation/gen_vehicle_data.py. Every catalogue entry
with a complete identity emits a row. A value that is not held is a
labelled absent zero, not a reason to refuse the record. These tests hold
the nine-column row contract, the graded resolution, the named
derivations, the five-layer ladder, the fail-closed result and the
freshness gate.

The complete records live only in this test file. They hold sentinel values,
name no real vehicle and are never written to the corpus.

Run: python3 -m unittest tools.tests.test_runtime_vehicles -v
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_vehicle_data as gen  # noqa: E402
from tools.validation import validate_vehicle_data as v  # noqa: E402
from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

MATCH_PATH = REPO / "addons" / "mobility" / "functions" / "fnc_getVehicleMatch.sqf"
DATA_PATH = REPO / "addons" / "mobility" / "functions" / "fnc_getVehicleData.sqf"
PREP_PATH = REPO / "addons" / "mobility" / "XEH_PREP.hpp"
MATCH = MATCH_PATH.read_text(encoding="utf-8")
DATA = DATA_PATH.read_text(encoding="utf-8")

# The nine columns the matcher row carries.
COL_CATALOGUE = 0
COL_VARIANT = 1
COL_TYPE = 2
COL_CLASS_TOKEN = 3
COL_CLASSES = 4
COL_ALIASES = 5
COL_KEYWORDS = 6
COL_SOURCE = 7
COL_VALUES = 8
ROW_COLUMNS = 9
VALUE_COLUMNS = 7

# Distinct sentinels so the column order is provable. No real value.
NUMERIC = {
    "operating_weight_kg": 11,
    "tyre_width_mm": 22,
    "tyre_diameter_mm": 33,
    "track_shoe_width_mm": 22,
    "track_pitch_mm": 33,
    "ground_clearance_mm": 44,
    "net_power_kw": 55,
}


def value(unit: str, raw: object, source: str = "fixture_source") -> dict[str, object]:
    """A complete value object. The source is a test fixture, not a document."""
    return {
        "value": raw,
        "unit": unit,
        "source": source,
        "locator": "fixture locator",
        "state": "fixture state",
        "grade": "documented",
    }


def ready_record(
    vehicle_type: str = "wheeled",
    catalogue_id: str = "fixture_catalogue",
    variant_id: str = "fixture_variant",
    aliases: tuple[str, ...] = ("fixture", "fx"),
    keywords: tuple[str, ...] = ("probe",),
    class_token: str = "Fixture_Token",
) -> dict[str, object]:
    """A runtime-ready catalogue entry. Fixture only, one sentinel per field."""
    values: dict[str, object] = {}
    for field in v.REQUIRED_RUNTIME_BY_TYPE[vehicle_type]:
        if field in v.ENUM_VALUES:
            raw: object = sorted(v.ENUM_VALUES[field])[-1]
        else:
            raw = NUMERIC[field]
        values[field] = value(v.FIELD_UNITS[field], raw)
    return {
        "catalogue_id": catalogue_id,
        "variant_id": variant_id,
        "vehicle_type": vehicle_type,
        "class_token": class_token,
        "aliases": list(aliases),
        "keywords": list(keywords),
        "runtime_ready": True,
        "values": values,
    }


def value_row(row: list[object]) -> list[object]:
    """Return the value_row column, narrowed for the type checker."""
    values = row[COL_VALUES]
    assert isinstance(values, list)
    return values


def table_body(text: str = MATCH) -> str:
    match = re.search(r"private _table = \[(.*?)\n\];", text, re.S)
    if match is None:
        raise AssertionError("the generated table is missing")
    return match.group(1)


class TestGeneratedMatchFile(unittest.TestCase):
    def test_the_file_is_marked_generated(self):
        self.assertIn("GENERATED", MATCH)
        self.assertIn("gen_vehicle_data.py", MATCH)
        self.assertIn("aee_mobility_fnc_getVehicleMatch", MATCH)

    def test_the_header_states_the_row_contract(self):
        header = MATCH.split("*/", 1)[0]
        for token in (
            "catalogue_id",
            "variant_id",
            "vehicle_type",
            "class_token",
            "mapped_classes",
            "aliases",
            "keywords",
            "source_record_id",
            "value_row",
        ):
            self.assertIn(token, header, f"the header does not state {token}")

    def test_the_header_states_the_result_contract(self):
        header = MATCH.split("*/", 1)[0]
        for token in (
            "confidence",
            "matched_by",
            "exact_class",
            "alias",
            "keyword",
            "inheritance",
            "closest",
        ):
            self.assertIn(token, header, f"the header does not state {token}")

    def test_the_header_names_both_runtime_sets(self):
        header = MATCH.split("*/", 1)[0]
        for token in (
            "tyre_width_mm",
            "tyre_diameter_mm",
            "track_shoe_width_mm",
            "track_pitch_mm",
        ):
            self.assertIn(token, header, f"the header does not state {token}")

    def test_the_corpus_emits_one_row_per_entry(self):
        # One emitted table row per runtime-ready catalogue entry.
        rows = gen.load_rows(gen.DEFAULT_DATA)
        self.assertEqual(len(re.findall(r"^\s{4}\[", table_body(), re.M)), len(rows))
        self.assertGreaterEqual(len(rows), 5)

    def test_reads_no_source_registry_and_no_config_value(self):
        self.assertNotIn("sources.json", MATCH)
        for command in ("getNumber", "getMass", "enginePower", "maxSpeed"):
            self.assertNotIn(command, MATCH, f"the matcher reads {command}")

    def test_uses_class_identity_only(self):
        self.assertIn("isKindOf", MATCH)
        self.assertIn("displayName", MATCH)
        self.assertIn("getText (configFile", MATCH)


class TestMatcherLayers(unittest.TestCase):
    """The five layers, ordered, each with a strict tie rule."""

    def test_the_exact_class_layer_runs_first_with_confidence_one(self):
        self.assertIn('"exact_class"', MATCH)
        self.assertIn(', 1, "exact_class"', MATCH)
        self.assertIn('(_classes splitString "|") find _key', MATCH)

    def test_the_alias_layer_runs_second_with_confidence_two(self):
        self.assertIn(', 2, "alias"', MATCH)
        self.assertIn("_x in _tokens", MATCH)

    def test_the_keyword_layer_runs_third_with_confidence_three(self):
        self.assertIn(', 3, "keyword"', MATCH)
        self.assertIn("_query find _x", MATCH)

    def test_the_inheritance_layer_runs_fourth_with_confidence_four(self):
        self.assertIn(', 4, "inheritance"', MATCH)
        self.assertIn("_className isKindOf _token", MATCH)

    def test_the_closest_layer_runs_fifth_with_confidence_five(self):
        self.assertIn(', 5, "closest"', MATCH)
        self.assertIn("_bestScore > _runnerUp", MATCH)
        self.assertIn(str(gen.SCAN_MIN), MATCH)

    def test_a_tie_at_a_layer_returns_empty(self):
        # Every layer that finds more than one candidate returns [].
        self.assertEqual(
            MATCH.count("if ((count _candidates) > 1) exitWith { [] };"), 4
        )
        self.assertIn("_tie = true", MATCH)

    def test_no_match_returns_empty(self):
        self.assertIn('if (_className == "") exitWith { [] };', MATCH)
        # The script ends on an empty array after the closest layer.
        self.assertTrue(MATCH.rstrip().endswith("[]"))

    def test_the_result_is_the_documented_seven_element_array(self):
        self.assertIn(
            "[_row select 0, _row select 1, _row select 2, _confidence, _layer,",
            MATCH,
        )
        self.assertIn("_row select 7, _row select 8]", MATCH)


class TestGeneratedDataFile(unittest.TestCase):
    def test_the_file_is_marked_generated(self):
        self.assertIn("GENERATED", DATA)
        self.assertIn("gen_vehicle_data.py", DATA)
        self.assertIn("aee_mobility_fnc_getVehicleData", DATA)

    def test_the_lookup_consumes_the_matcher(self):
        self.assertIn("FUNC(getVehicleMatch)", DATA)
        self.assertIn("_match select 6", DATA)

    def test_the_lookup_holds_no_table(self):
        self.assertNotIn("private _table", DATA)

    def test_reads_no_source_registry_and_no_config_value(self):
        self.assertNotIn("sources.json", DATA)
        for command in ("getNumber", "getMass", "enginePower", "maxSpeed"):
            self.assertNotIn(command, DATA, f"the lookup reads {command}")

    def test_a_variant_selector_is_supported(self):
        self.assertIn("_variantId", DATA)
        self.assertIn("_variantKey", DATA)


class TestWiring(unittest.TestCase):
    def test_both_functions_are_registered(self):
        prep = PREP_PATH.read_text(encoding="utf-8")
        self.assertIn("PREP(getVehicleMatch);", prep)
        self.assertIn("PREP(getVehicleData);", prep)

    def test_get_vehicle_match_is_registered_once(self):
        prep = PREP_PATH.read_text(encoding="utf-8")
        hits = [line for line in prep.splitlines() if "getVehicleMatch" in line]
        self.assertEqual(len(hits), 1, hits)


class TestGeneratorRows(unittest.TestCase):
    def test_a_ready_record_makes_a_nine_column_row(self):
        row = gen.build_row(ready_record(), ("FIXTURE_CLASS",))
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(len(row), ROW_COLUMNS)
        self.assertEqual(len(value_row(row)), VALUE_COLUMNS)

    def test_the_wheeled_value_row_is_type_aware(self):
        row = gen.build_row(ready_record("wheeled"), ("FIXTURE_CLASS",))
        assert row is not None
        self.assertEqual(row[COL_TYPE], "wheeled")
        self.assertEqual(value_row(row), [11, 22, 33, 44, 55, "manual", "none"])

    def test_the_tracked_value_row_is_type_aware(self):
        row = gen.build_row(ready_record("tracked"), ("FIXTURE_CLASS",))
        assert row is not None
        self.assertEqual(row[COL_TYPE], "tracked")
        self.assertEqual(value_row(row), [11, 22, 33, 44, 55, "manual", "none"])

    def test_a_tracked_record_emits_absent_track_fields(self):
        # A record retyped tracked without the track fields still emits. The
        # two track fields resolve to labelled absent zeros.
        record = ready_record("wheeled")
        record["vehicle_type"] = "tracked"
        row = gen.build_row(record)
        assert row is not None
        self.assertEqual(value_row(row), [11, 0, 0, 44, 55, "manual", "none"])

    def test_the_identity_columns_follow_the_contract(self):
        row = gen.build_row(ready_record(), ("FIXTURE_CLASS",))
        assert row is not None
        self.assertEqual(row[COL_CATALOGUE], "fixture_catalogue")
        self.assertEqual(row[COL_VARIANT], "fixture_variant")
        self.assertEqual(row[COL_TYPE], "wheeled")
        self.assertEqual(row[COL_CLASS_TOKEN], "Fixture_Token")

    def test_the_mapped_class_blob_is_normalised(self):
        row = gen.build_row(ready_record(), ("B_MRAP_01_F", "MRAP"))
        assert row is not None
        self.assertEqual(row[COL_CLASSES], "bmrap01f|mrap")

    def test_the_alias_and_keyword_blobs_are_normalised(self):
        record = ready_record(
            aliases=("M-ATV", "matv", "M1240"), keywords=("MRAP", "Oshkosh")
        )
        row = gen.build_row(record, ())
        assert row is not None
        self.assertEqual(row[COL_ALIASES], "matv|m1240")
        self.assertEqual(row[COL_KEYWORDS], "mrap|oshkosh")

    def test_the_source_record_id_is_the_operating_weight_source(self):
        record = ready_record()
        fields = record["values"]
        assert isinstance(fields, dict)
        entry = fields["operating_weight_kg"]
        assert isinstance(entry, dict)
        entry["source"] = "tm_fixture_source"
        row = gen.build_row(record, ())
        assert row is not None
        self.assertEqual(row[COL_SOURCE], "tm_fixture_source")

    def test_an_entry_without_the_runtime_ready_flag_still_emits(self):
        record = ready_record()
        record["runtime_ready"] = False
        self.assertIsNotNone(gen.build_row(record))
        self.assertEqual(len(gen.build_rows([record])), 1)

    def test_a_missing_required_field_resolves_absent(self):
        record = ready_record()
        fields = record["values"]
        assert isinstance(fields, dict)
        del fields["net_power_kw"]
        row = gen.build_row(record)
        assert row is not None
        self.assertEqual(value_row(row)[4], 0)
        resolved = {field.name: field for field in gen.resolve_row(record) or []}
        self.assertEqual("absent", resolved["net_power_kw"].grade)

    def test_an_incomplete_value_object_is_absent_not_a_refusal(self):
        for field, key in (
            ("operating_weight_kg", "source"),
            ("operating_weight_kg", "unit"),
            ("ground_clearance_mm", "locator"),
            ("net_power_kw", "state"),
            ("transmission_type", "grade"),
        ):
            with self.subTest(field=field, key=key):
                record = ready_record()
                fields = record["values"]
                assert isinstance(fields, dict)
                entry = fields[field]
                assert isinstance(entry, dict)
                del entry[key]
                row = gen.build_row(record)
                self.assertIsNotNone(row)
                resolved = {item.name: item for item in gen.resolve_row(record) or []}
                self.assertEqual("absent", resolved[field].grade)

    def test_a_value_with_no_value_resolves_absent(self):
        record = ready_record()
        fields = record["values"]
        assert isinstance(fields, dict)
        entry = fields["operating_weight_kg"]
        assert isinstance(entry, dict)
        entry["value"] = ""
        row = gen.build_row(record)
        assert row is not None
        self.assertEqual(value_row(row)[0], 0)

    def test_an_identity_incomplete_record_makes_no_row(self):
        record = ready_record()
        record["catalogue_id"] = ""
        self.assertIsNone(gen.build_row(record))

    def test_rows_are_stable_and_sorted(self):
        first = ready_record(catalogue_id="b_catalogue")
        second = ready_record(catalogue_id="a_catalogue")
        rows = gen.build_rows([first, second])
        self.assertEqual(
            [row[COL_CATALOGUE] for row in rows],
            ["a_catalogue", "b_catalogue"],
        )

    def test_the_real_corpus_emits_a_row_per_ready_entry(self):
        rows = gen.load_rows(gen.DEFAULT_DATA)
        ids = {row[COL_CATALOGUE] for row in rows}
        # One row per entry, no duplicate row.
        self.assertEqual(len(ids), len(rows))
        for sentinel in (
            "honda_civic_6gen_sedan",
            "kawasaki_ninja_250r_ex250f",
            "m113a2",
            "m923a2",
            "m_atv_m1240",
            "m1_abrams",
            "m2_m3_bradley",
            "m925a2",
            "m577a2",
            "cougar_4x4",
            "hmmwv_m998",
            "toyota_t100",
        ):
            self.assertIn(sentinel, ids)

    def test_a_synthetic_row_renders_into_the_match_file(self):
        row = gen.build_row(ready_record(), ("B_MRAP_01_F",))
        assert row is not None
        text = gen.render_match([row])
        self.assertIn('"fixture_catalogue", "fixture_variant", "wheeled"', text)
        self.assertIn('"bmrap01f"', text)


class TestGradedResolution(unittest.TestCase):
    """The named derivations, graded, against the real corpus."""

    def _fields(self, catalogue_id: str) -> dict[str, object]:
        load = catalogue.load(gen.DEFAULT_DATA)
        entry = next(e for e in load.entries if e.catalogue_id == catalogue_id)
        return entry.resolved_fields()

    def test_net_power_from_brake_horsepower_is_derived(self) -> None:
        power = self._fields("m923a2")["net_power_kw"]
        self.assertEqual("derived", power.grade)
        self.assertAlmostEqual(240 * 0.745699872, power.value, places=6)
        self.assertIn("1 hp = 745.699872 W", power.state)

    def test_metric_tyre_size_derives_width_and_diameter(self) -> None:
        fields = self._fields("m_atv_m1240")
        self.assertEqual("derived", fields["tyre_width_mm"].grade)
        self.assertAlmostEqual(395, fields["tyre_width_mm"].value)
        self.assertAlmostEqual(
            20 * 25.4 + 2 * 395 * 0.85, fields["tyre_diameter_mm"].value
        )

    def test_inch_tyre_size_derives_width_and_diameter(self) -> None:
        fields = self._fields("m923a2")
        self.assertAlmostEqual(14.0 * 25.4, fields["tyre_width_mm"].value)
        self.assertAlmostEqual((20 + 2 * 14.0) * 25.4, fields["tyre_diameter_mm"].value)

    def test_operating_weight_falls_back_to_curb_then_gross(self) -> None:
        matv = self._fields("m_atv_m1240")["operating_weight_kg"]
        self.assertEqual("derived", matv.grade)
        self.assertEqual(11123, matv.value)
        self.assertIn("curb weight", matv.state)
        civic = self._fields("honda_civic_6gen_sedan")["operating_weight_kg"]
        self.assertEqual(1540, civic.value)
        self.assertIn("gross vehicle weight rating", civic.state)

    def test_absent_fields_are_labelled_zeros(self) -> None:
        fields = self._fields("honda_civic_6gen_sedan")
        for name in ("tyre_width_mm", "tyre_diameter_mm", "net_power_kw"):
            self.assertEqual("absent", fields[name].grade)
        self.assertEqual(0, fields["tyre_width_mm"].value)
        self.assertEqual("", fields["grousers_state"].value)


class TestReferenceMatcher(unittest.TestCase):
    """The Python mirror of the ladder resolves a real identity per entry."""

    rows = gen.load_rows(gen.DEFAULT_DATA)

    def test_each_entry_resolves_through_the_alias_layer(self) -> None:
        for query, catalogue_id in (
            ("m113a2", "m113a2"),
            ("m939a2", "m923a2"),
            ("civic", "honda_civic_6gen_sedan"),
            ("m1240", "m_atv_m1240"),
        ):
            with self.subTest(query=query):
                result = gen.match_row(self.rows, query)
                self.assertIsNotNone(result)
                assert result is not None
                self.assertEqual(result[0], catalogue_id)
                self.assertEqual(result[4], "alias")
                value_row = result[6]
                assert isinstance(value_row, list)
                self.assertEqual(len(value_row), 7)

    def test_a_keyword_resolves_when_no_alias_matches(self) -> None:
        # "motorcycle" is a keyword of one entry (min four characters) and
        # an alias of none, so the keyword layer resolves it unambiguously.
        result = gen.match_row(self.rows, "motorcycle")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result[4], "keyword")

    def test_an_unknown_class_returns_none(self) -> None:
        self.assertIsNone(gen.match_row(self.rows, "zzzznotavehicle"))


class TestProjectionFreshness(unittest.TestCase):
    """Both files must match a fresh render. --check writes nothing."""

    def test_the_committed_outputs_are_fresh(self):
        self.assertEqual(gen.check_outputs(gen.DEFAULT_DATA), 0)

    def test_a_fresh_pair_passes_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            match = Path(tmp) / "fnc_getVehicleMatch.sqf"
            data = Path(tmp) / "fnc_getVehicleData.sqf"
            rows = gen.load_rows(gen.DEFAULT_DATA)
            match.write_text(gen.render_match(rows), encoding="utf-8")
            data.write_text(gen.render_data(), encoding="utf-8")
            self.assertEqual(gen.check_outputs(gen.DEFAULT_DATA, match, data), 0)

    def test_a_missing_match_file_fails_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "fnc_getVehicleData.sqf"
            data.write_text(gen.render_data(), encoding="utf-8")
            self.assertEqual(
                gen.check_outputs(gen.DEFAULT_DATA, Path(tmp) / "absent.sqf", data), 1
            )

    def test_a_stale_match_file_fails_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            match = Path(tmp) / "fnc_getVehicleMatch.sqf"
            data = Path(tmp) / "fnc_getVehicleData.sqf"
            match.write_text(gen.render_match([]) + "// stale\n", encoding="utf-8")
            data.write_text(gen.render_data(), encoding="utf-8")
            self.assertEqual(gen.check_outputs(gen.DEFAULT_DATA, match, data), 1)

    def test_check_mode_writes_nothing_on_a_stale_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            match = Path(tmp) / "fnc_getVehicleMatch.sqf"
            data = Path(tmp) / "fnc_getVehicleData.sqf"
            match.write_text("stale", encoding="utf-8")
            data.write_text("stale", encoding="utf-8")
            gen.check_outputs(gen.DEFAULT_DATA, match, data)
            self.assertEqual(match.read_text(encoding="utf-8"), "stale")
            self.assertEqual(data.read_text(encoding="utf-8"), "stale")


if __name__ == "__main__":
    unittest.main()
