#!/usr/bin/env python3
"""Device matcher and lookup tests (night vision, thermal and optic).

The device matcher and lookup are generated from the validated device
corpus by tools/validation/gen_device_data.py. Every entry with a complete
identity emits a row. A value that is not held is a labelled absent zero or
empty string, not a reason to refuse the record. These tests hold the row
contract, the family filter, the identity ladder, the fail-closed result,
the seed parity with the old hard-coded tube model and the freshness gate.

Run: python3 -m unittest tools.tests.test_device_runtime -v
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import device_catalogue as catalogue  # noqa: E402
from tools.validation import gen_device_data as gen  # noqa: E402

MATCH_PATH = REPO / "addons" / "nightvision" / "functions" / "fnc_getDeviceMatch.sqf"
DATA_PATH = REPO / "addons" / "nightvision" / "functions" / "fnc_getDeviceData.sqf"
PREP_PATH = REPO / "addons" / "nightvision" / "XEH_PREP.hpp"
TUBE_PATH = REPO / "addons" / "nightvision" / "functions" / "fnc_getNvgTubeModel.sqf"
THERMAL_PATH = (
    REPO
    / "addons"
    / "thermal"
    / "functions"
    / "sensor"
    / "fnc_getThermalDeviceProperties.sqf"
)
MATCH = MATCH_PATH.read_text(encoding="utf-8")
DATA = DATA_PATH.read_text(encoding="utf-8")
TUBE = TUBE_PATH.read_text(encoding="utf-8")
THERMAL = THERMAL_PATH.read_text(encoding="utf-8")

# The seven columns the matcher row carries.
COL_DEVICE = 0
COL_FAMILY = 1
COL_CLASSES = 2
COL_ALIASES = 3
COL_KEYWORDS = 4
COL_SOURCE = 5
COL_VALUES = 6
ROW_COLUMNS = 7

# The runtime value row of each family, for the seed-parity checks.
NVG_FIELDS = ("output_colour", "resolution_lpmm", "snr", "halo_mm")


def rows() -> list[list[object]]:
    return gen.load_rows(gen.DEFAULT_DATA)


def table_body() -> str:
    match = re.search(r"private _tableAll = \[(.*?)\n\];", MATCH, re.S)
    if match is None:
        raise AssertionError("the generated table is missing")
    return match.group(1)


def nvg_row(device_id: str) -> list[object]:
    """The value row of one night vision device, as the matcher returns it."""
    for row in rows():
        if row[COL_DEVICE] == device_id and row[COL_FAMILY] == "nvg":
            values = row[COL_VALUES]
            assert isinstance(values, list)
            return values
    raise AssertionError(f"no night vision row for {device_id}")


class TestCorpus(unittest.TestCase):
    def test_the_loader_reports_no_error(self):
        self.assertEqual(catalogue.load(gen.DEFAULT_DATA).errors, [])

    def test_all_three_families_are_held(self):
        families = {entry.family for entry in catalogue.load(gen.DEFAULT_DATA).entries}
        self.assertEqual(families, {"nvg", "thermal", "optic"})

    def test_every_held_value_is_complete(self):
        load = catalogue.load(gen.DEFAULT_DATA)
        for entry in load.entries:
            for field, raw in entry.values.items():
                with self.subTest(device=entry.device_id, field=field):
                    value = catalogue.held_value(entry.values, field)
                    if raw.get("value") in (None, ""):
                        self.assertIsNone(value)
                        continue
                    self.assertIsNotNone(value, "a held value is incomplete")
                    assert value is not None
                    for key in catalogue.VALUE_META_KEYS:
                        self.assertIn(key, value)
                    self.assertIn(value["grade"], catalogue.GRADES)

    def test_a_tier_five_value_is_claimed_only(self):
        load = catalogue.load(gen.DEFAULT_DATA)
        for entry in load.entries:
            for field in entry.values:
                value = catalogue.held_value(entry.values, field)
                if value is None:
                    continue
                source = load.sources[str(value["source"])]
                if source.tier >= 5:
                    with self.subTest(device=entry.device_id, field=field):
                        self.assertEqual(value["grade"], "claimed")

    def test_a_device_id_is_unique(self):
        ids = [entry.device_id for entry in catalogue.load(gen.DEFAULT_DATA).entries]
        self.assertEqual(len(ids), len(set(ids)))

    def test_a_class_name_is_unique_within_a_family(self):
        owned: dict[tuple[str, str], str] = {}
        for entry in catalogue.load(gen.DEFAULT_DATA).entries:
            for name in entry.class_names:
                key = (entry.family, name)
                with self.subTest(device=entry.device_id, name=name):
                    self.assertNotIn(key, owned, f"{name} is held by two devices")
                    owned[key] = entry.device_id


class TestGeneratedMatchFile(unittest.TestCase):
    def test_the_file_is_marked_generated(self):
        self.assertIn("GENERATED", MATCH)
        self.assertIn("gen_device_data.py", MATCH)
        self.assertIn("aee_nightvision_fnc_getDeviceMatch", MATCH)

    def test_the_header_states_the_row_contract(self):
        header = MATCH.split("*/", 1)[0]
        for token in (
            "device_id",
            "family",
            "class_names",
            "aliases",
            "keywords",
            "source_record_id",
            "value_row",
        ):
            self.assertIn(token, header, f"the header does not state {token}")

    def test_the_header_names_every_runtime_set(self):
        header = MATCH.split("*/", 1)[0]
        for token in (
            "output_colour",
            "resolution_lpmm",
            "snr",
            "halo_mm",
            "netd_c",
            "resolution_x",
            "resolution_y",
            "refresh_hz",
            "cooled",
            "weight_kg",
            "magnification",
            "objective_mm",
            "fov_deg",
            "exit_pupil_mm",
            "active",
        ):
            self.assertIn(token, header, f"the header does not state {token}")

    def test_the_corpus_emits_one_row_per_entry(self):
        expected = gen.load_rows(gen.DEFAULT_DATA)
        self.assertEqual(
            len(re.findall(r"^\s{4}\[", table_body(), re.M)), len(expected)
        )

    def test_the_family_filter_is_applied_before_the_ladder(self):
        self.assertIn("_tableAll select", MATCH)
        self.assertIn("(_x select 1) == _family", MATCH)

    def test_reads_no_source_registry_and_no_config_value(self):
        self.assertNotIn("sources.json", MATCH)
        for command in ("getNumber", "getMass", "enginePower", "maxSpeed"):
            self.assertNotIn(command, MATCH, f"the matcher reads {command}")

    def test_uses_class_identity_only(self):
        self.assertIn('getText (_cfg >> "displayName")', MATCH)
        self.assertIn("displayName", MATCH)


class TestMatcherLayers(unittest.TestCase):
    def test_the_exact_class_layer_runs_first_with_confidence_one(self):
        self.assertIn(', 1, "exact_class"', MATCH)
        self.assertIn('(_classes splitString "|") find _key', MATCH)

    def test_the_alias_layer_runs_second_with_confidence_two(self):
        self.assertIn(', 2, "alias"', MATCH)
        self.assertIn("_x in _tokens", MATCH)

    def test_the_keyword_layer_runs_third_with_confidence_three(self):
        self.assertIn(', 3, "keyword"', MATCH)
        self.assertIn("_query find _x", MATCH)

    def test_the_closest_layer_runs_fourth_with_confidence_four(self):
        self.assertIn(', 4, "closest"', MATCH)
        self.assertIn("_bestScore > _runnerUp", MATCH)
        self.assertIn(str(gen.SCAN_MIN), MATCH)

    def test_a_tie_at_a_layer_returns_empty(self):
        self.assertEqual(
            MATCH.count("if ((count _candidates) > 1) exitWith { [] };"), 3
        )
        self.assertIn("_tie = true", MATCH)

    def test_no_match_returns_empty(self):
        self.assertIn('if (_className == "") exitWith { [] };', MATCH)
        self.assertTrue(MATCH.rstrip().endswith("[]"))

    def test_the_result_is_the_documented_six_element_array(self):
        self.assertIn("[_row select 0, _row select 1, _confidence, _layer,", MATCH)
        self.assertIn("_row select 5, _row select 6]", MATCH)


class TestGeneratedDataFile(unittest.TestCase):
    def test_the_file_is_marked_generated(self):
        self.assertIn("GENERATED", DATA)
        self.assertIn("gen_device_data.py", DATA)
        self.assertIn("aee_nightvision_fnc_getDeviceData", DATA)

    def test_the_lookup_consumes_the_matcher(self):
        self.assertIn("FUNC(getDeviceMatch)", DATA)
        self.assertIn("_match select 5", DATA)

    def test_the_lookup_holds_no_table(self):
        self.assertNotIn("private _table", DATA)

    def test_reads_no_source_registry_and_no_config_value(self):
        self.assertNotIn("sources.json", DATA)
        for command in ("getNumber", "getMass", "enginePower", "maxSpeed"):
            self.assertNotIn(command, DATA, f"the lookup reads {command}")

    def test_a_family_selector_is_supported(self):
        self.assertIn("_family", DATA)


class TestResolutionMirror(unittest.TestCase):
    """The identity ladder resolves every class the tube model named."""

    CASES = (
        ("GPNVG-18", "gpnvg18"),
        ("GPNVG18", "gpnvg18"),
        ("PANOGoggles", "gpnvg18"),
        ("nv_wide", "gpnvg18"),
        ("NVGogglesB_grn_F", "envgb"),
        ("ENVG", "envgb"),
        ("AN/PSQ-42", "envgb"),
        ("AN/PVS-31", "pvs31"),
        ("nvg_w", "pvs31"),
        ("ANVIS", "anvis9"),
        ("AVS-9", "anvis9"),
        ("AN/PVS-15", "pvs15"),
        ("AN/PVS-14", "pvs14"),
        ("AN/PVS-7", "pvs7"),
        ("AN/PVS-5", "pvs5"),
        ("1PN138", "russian_1pn138"),
        ("1PN97", "russian_1pn138"),
        ("1PN93", "russian_1pn93"),
        ("1PN63", "russian_1pn63"),
        ("1PN58", "russian_1pn63"),
        ("NVGoggles", "vanilla_gen3"),
        ("NVGoggles_INDEP", "vanilla_gen3"),
        ("nvgen3", "vanilla_gen3"),
        ("NVGoggles_OPFOR", "vanilla_gen2"),
        ("nvgen2", "vanilla_gen2"),
    )

    def test_every_tube_trigger_resolves_to_its_device(self):
        table = rows()
        for class_name, device_id in self.CASES:
            with self.subTest(class_name=class_name):
                result = gen.match_row(table, class_name, family="nvg")
                self.assertIsNotNone(result, f"{class_name} resolved nothing")
                assert result is not None
                self.assertEqual(result[COL_DEVICE], device_id)
                self.assertEqual(result[COL_FAMILY], "nvg")

    def test_a_mod_prefix_still_resolves(self):
        table = rows()
        result = gen.match_row(table, "rhs_pvs14", family="nvg")
        assert result is not None
        self.assertEqual(result[COL_DEVICE], "pvs14")

    def test_an_unknown_class_returns_none(self):
        self.assertIsNone(gen.match_row(rows(), "zzzznotadevice", family="nvg"))

    def test_the_family_filter_separates_the_shared_class(self):
        table = rows()
        nvg = gen.match_row(table, "ENVG-B", family="nvg")
        thermal = gen.match_row(table, "ENVG-B", family="thermal")
        assert nvg is not None and thermal is not None
        self.assertEqual(nvg[COL_DEVICE], "envgb")
        self.assertEqual(thermal[COL_DEVICE], "envg_thermal")

    def test_a_thermal_trigger_resolves(self):
        result = gen.match_row(rows(), "Catherine-MP", family="thermal")
        assert result is not None
        self.assertEqual(result[COL_DEVICE], "catherine")
        self.assertEqual(result[COL_FAMILY], "thermal")

    def test_an_optic_trigger_resolves(self):
        result = gen.match_row(rows(), "ACOG", family="optic")
        assert result is not None
        self.assertEqual(result[COL_DEVICE], "prism_4x")
        self.assertEqual(result[COL_FAMILY], "optic")


class TestSeedParity(unittest.TestCase):
    """The generated night vision values match the old hard-coded table."""

    def test_gpnvg18(self):
        values = nvg_row("gpnvg18")
        self.assertEqual(values[0], "white")
        self.assertEqual(values[1], 64)
        self.assertEqual(values[3], 0.5533)

    def test_envgb(self):
        values = nvg_row("envgb")
        self.assertEqual(values[0], "white")
        self.assertEqual(values[1], 72)
        self.assertEqual(values[2], 32)
        self.assertEqual(values[3], 0.5533)

    def test_pvs31(self):
        values = nvg_row("pvs31")
        self.assertEqual(values[0], "white")
        self.assertEqual(values[1], 72)
        self.assertEqual(values[2], 33)
        self.assertEqual(values[3], 0.5533)

    def test_pvs14(self):
        values = nvg_row("pvs14")
        self.assertEqual(values[0], "")
        self.assertEqual(values[1], 64)
        self.assertEqual(values[2], 31)
        self.assertEqual(values[3], 0.5533)

    def test_pvs7(self):
        values = nvg_row("pvs7")
        self.assertEqual(values[1], 0)
        self.assertEqual(values[2], 12)
        self.assertEqual(values[3], 0.2388)

    def test_pvs5(self):
        values = nvg_row("pvs5")
        self.assertEqual(values[1], 28)
        self.assertEqual(values[3], 0.2388)

    def test_russian_1pn63(self):
        values = nvg_row("russian_1pn63")
        self.assertEqual(values[1], 30)
        self.assertEqual(values[3], 0)

    def test_an_unsourced_device_row_is_all_absent(self):
        values = nvg_row("russian_1pn138")
        self.assertEqual(values, ["", 0, 0, 0])


class TestNvgRewire(unittest.TestCase):
    def test_the_tube_model_reads_the_generated_matcher(self):
        self.assertIn("call FUNC(getDeviceMatch)", TUBE)
        self.assertIn('[_hmd, "nvg"]', TUBE)

    def test_the_generation_fallback_stays(self):
        # The unmatched contract: no device corrections, the caller keeps
        # the generation value from fnc_getNvgDeviceProperties.
        self.assertIn('["GEN1", "", -1, -1, -1, false]', TUBE)
        self.assertIn("getNvgDeviceProperties", TUBE)

    def test_the_hard_coded_device_values_are_gone(self):
        for token in ("gpnvg", "pvs14", "0.5533", "0.2388", "1pn63"):
            self.assertNotIn(token, TUBE, f"{token} is still hard-coded")

    def test_both_generated_functions_are_registered(self):
        prep = PREP_PATH.read_text(encoding="utf-8")
        self.assertIn("PREP(getDeviceMatch);", prep)
        self.assertIn("PREP(getDeviceData);", prep)


class TestGeneratorRows(unittest.TestCase):
    def test_a_ready_record_makes_a_seven_column_row(self):
        load = catalogue.load(gen.DEFAULT_DATA)
        entry = next(e for e in load.entries if e.device_id == "pvs14")
        row = gen.build_row(entry.to_mapping(), entry.class_names)
        assert row is not None
        self.assertEqual(len(row), ROW_COLUMNS)
        self.assertEqual(row[COL_DEVICE], "pvs14")
        self.assertEqual(row[COL_FAMILY], "nvg")
        self.assertIn("pvs14", str(row[COL_CLASSES]).split("|"))

    def test_a_missing_value_resolves_absent_not_a_refusal(self):
        load = catalogue.load(gen.DEFAULT_DATA)
        entry = next(e for e in load.entries if e.device_id == "russian_1pn138")
        row = gen.build_row(entry.to_mapping())
        assert row is not None
        values = row[COL_VALUES]
        assert isinstance(values, list)
        self.assertEqual(values, ["", 0, 0, 0])
        resolved = {
            field.name: field for field in gen.resolve_row(entry.to_mapping()) or []
        }
        self.assertEqual("absent", resolved["resolution_lpmm"].grade)

    def test_an_identity_incomplete_record_makes_no_row(self):
        self.assertIsNone(gen.build_row({"family": "nvg", "values": {}}))
        self.assertIsNone(gen.build_row({"device_id": "x", "family": "bad"}))


class TestFreshness(unittest.TestCase):
    def test_the_committed_outputs_are_fresh(self):
        self.assertEqual(gen.check_outputs(gen.DEFAULT_DATA), 0)

    def test_the_main_check_mode_passes(self):
        self.assertEqual(gen.main(["--check"]), 0)

    def test_a_stale_file_fails_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            match = Path(tmp) / "fnc_getDeviceMatch.sqf"
            data = Path(tmp) / "fnc_getDeviceData.sqf"
            match.write_text(gen.render_match([]) + "// stale\n", encoding="utf-8")
            data.write_text(gen.render_data(), encoding="utf-8")
            self.assertEqual(gen.check_outputs(gen.DEFAULT_DATA, match, data), 1)

    def test_check_mode_writes_nothing_on_a_stale_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            match = Path(tmp) / "fnc_getDeviceMatch.sqf"
            data = Path(tmp) / "fnc_getDeviceData.sqf"
            match.write_text("stale", encoding="utf-8")
            data.write_text("stale", encoding="utf-8")
            gen.check_outputs(gen.DEFAULT_DATA, match, data)
            self.assertEqual(match.read_text(encoding="utf-8"), "stale")
            self.assertEqual(data.read_text(encoding="utf-8"), "stale")


class TestThermalFamilyIsolation(unittest.TestCase):
    """A thermal class resolves in exactly one family (issue #215).

    The matcher filters its table by family before the ladder, so the
    ENVG-B, which is both a night vision device and a thermal device, can
    never tie. A thermal class resolves only through the thermal filter.
    """

    def test_the_shared_class_resolves_per_family(self):
        table = rows()
        for class_name in ("ENVG-B", "AN/PSQ-42"):
            with self.subTest(class_name=class_name):
                thermal = gen.match_row(table, class_name, family="thermal")
                nvg = gen.match_row(table, class_name, family="nvg")
                self.assertIsNotNone(thermal)
                self.assertIsNotNone(nvg)
                assert thermal is not None and nvg is not None
                self.assertEqual(thermal[COL_DEVICE], "envg_thermal")
                self.assertEqual(thermal[COL_FAMILY], "thermal")
                self.assertEqual(nvg[COL_DEVICE], "envgb")
                self.assertEqual(nvg[COL_FAMILY], "nvg")

    def test_every_thermal_class_resolves_in_the_thermal_family(self):
        table = rows()
        for row in table:
            if row[COL_FAMILY] != "thermal":
                continue
            classes = [key for key in str(row[COL_CLASSES]).split("|") if key]
            self.assertTrue(classes, f"{row[COL_DEVICE]} names no class")
            for class_name in classes:
                with self.subTest(device=row[COL_DEVICE], class_name=class_name):
                    found = gen.match_row(table, class_name, family="thermal")
                    self.assertIsNotNone(found)
                    assert found is not None
                    self.assertEqual(found[COL_DEVICE], row[COL_DEVICE])

    def test_a_thermal_class_never_resolves_to_a_foreign_family(self):
        # With no filter, a thermal class either resolves to its thermal row
        # or to nothing (the shared class ties). It never resolves to a
        # night vision or optic row.
        table = rows()
        for row in table:
            if row[COL_FAMILY] != "thermal":
                continue
            classes = [key for key in str(row[COL_CLASSES]).split("|") if key]
            for class_name in classes:
                with self.subTest(class_name=class_name):
                    found = gen.match_row(table, class_name)
                    if found is not None:
                        self.assertEqual(found[COL_FAMILY], "thermal")

    def test_pas13_variants_do_not_resolve_to_the_base(self):
        # The base device must not steal a variant through its old broad
        # "pas13" alias. A variant token selects the variant row, and a
        # separated variant token matches nothing here so the resolver's
        # static fallback selects the variant.
        table = rows()
        for class_name in (
            "AN/PAS-13E(V)1",
            "PAS-13 V1",
            "rhs_weap_pas13v1",
            "ACE_PAS13_V1",
            "CUP_optic_PAS13_V1",
            "PAS13_V1",
        ):
            with self.subTest(class_name=class_name):
                found = gen.match_row(table, class_name, family="thermal")
                self.assertIsNotNone(found)
                assert found is not None
                self.assertEqual(found[COL_DEVICE], "pas13_v1")
        self.assertIsNone(gen.match_row(table, "PAS-13E(V)1", family="thermal"))
        for class_name in ("AN/PAS-13", "PAS-13"):
            with self.subTest(class_name=class_name):
                base = gen.match_row(table, class_name, family="thermal")
                self.assertIsNotNone(base)
                assert base is not None
                self.assertEqual(base[COL_DEVICE], "pas13_base")


class TestUnmatchedThermalFallback(unittest.TestCase):
    """An unknown thermal class matches nothing, so the resolver falls back.

    fnc_getThermalDeviceProperties keeps its static table as the named
    fallback: a whole-row fallback when the matcher returns nothing, and a
    per-field fallback when the corpus holds no figure for one field. A
    figure is never copied from a sibling device.
    """

    def test_an_unknown_thermal_class_matches_nothing(self):
        self.assertIsNone(
            gen.match_row(rows(), "zzzznotathermaldevice", family="thermal")
        )

    def test_a_fallback_only_token_matches_nothing(self):
        # "clipon" is a static-fallback token with no corpus row.
        self.assertIsNone(gen.match_row(rows(), "clipon", family="thermal"))

    def test_the_resolver_reads_the_generated_matcher(self):
        self.assertIn("call EFUNC(nightvision,getDeviceMatch)", THERMAL)
        self.assertIn('[_optic, "thermal"]', THERMAL)

    def test_the_named_fallback_is_the_static_table(self):
        self.assertIn("private _fallback = switch (true) do {", THERMAL)
        self.assertIn("if (_match isEqualTo []) exitWith { _fallback };", THERMAL)

    def test_a_missing_field_falls_back_per_field(self):
        for field in ("_netd", "_resX", "_resY", "_refresh", "_weight"):
            self.assertIn(f"{field} = _fallback select", THERMAL)

    def test_the_cooled_enum_maps_to_the_numeric_contract(self):
        self.assertIn('if (_cooledToken == "cooled") then { _cooled = 1; };', THERMAL)
        self.assertIn('if (_cooledToken == "uncooled") then { _cooled = 0; };', THERMAL)


class TestThermalCorpusParity(unittest.TestCase):
    """The generated thermal values are the corpus values (issue #215)."""

    def thermal_values(self, device_id: str) -> list[object]:
        for row in rows():
            if row[COL_DEVICE] == device_id and row[COL_FAMILY] == "thermal":
                values = row[COL_VALUES]
                assert isinstance(values, list)
                return values
        raise AssertionError(f"no thermal row for {device_id}")

    def test_the_row_order_is_the_document_contract(self):
        # [netd_c, resolution_x, resolution_y, refresh_hz, cooled, weight_kg]
        self.assertEqual(
            self.thermal_values("catherine"),
            [0.025, 1280, 1024, 50, "cooled", 7.9],
        )
        self.assertEqual(
            self.thermal_values("flir_scout"),
            [0.05, 640, 512, 30, "uncooled", 0.34],
        )

    def test_every_thermal_value_this_release_holds_is_claimed(self):
        # Every thermal field this release holds is a claimed sourced figure.
        # The ECOTI is the one documented exception: the Safran E-COTI Data
        # Sheet prints no NETD and no refresh rate, so those two fields are
        # labelled absent rather than borrowed from a sibling device.  Every
        # other ECOTI field is claimed, and no other device has an absent
        # field.
        load = catalogue.load(gen.DEFAULT_DATA)
        for entry in load.entries:
            if entry.family != "thermal":
                continue
            published_absent = (
                {"netd_c", "refresh_hz"} if entry.device_id == "ecoti" else set()
            )
            for name, field in entry.resolved_fields().items():
                with self.subTest(device=entry.device_id, field=name):
                    if name in published_absent:
                        self.assertEqual(field.grade, "absent")
                    else:
                        self.assertEqual(field.grade, "claimed")


if __name__ == "__main__":
    unittest.main()
