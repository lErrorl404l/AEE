#!/usr/bin/env python3
"""Aircraft corpus provenance tests (aircraft corpus, wave 4 task 15).

The validator is the gate. It rejects a value without a unit, a source, a
locator, a state or a compliant grade. It rejects an engine source as a
value source. It rejects a runtime-required field that resolves from an
unheld source. It rejects a `primary_held: false` value with no UNSOURCED
marker. It accepts a complete entry.

The real corpus is the oracle for the first slice. The negative fixture at
``data/aircraft/fixtures/`` is the oracle for rejection. The good records
live only in this test file and in a temporary directory. They hold no real
aircraft value and they are never written to the corpus.

Run: python3 -m unittest tools.tests.test_aircraft_corpus -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import validate_aircraft_data as v  # noqa: E402
from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

VALIDATOR = REPO / "tools" / "validation" / "validate_aircraft_data.py"
REAL_DATA = REPO / "data" / "aircraft"
FIXTURES = REAL_DATA / "fixtures"
FIXTURE_CAPTURE = FIXTURES / "pilot-invalid.json"
FIXTURE_SOURCES = FIXTURES / "sources.json"
SYSTEMS_FIXTURE = FIXTURES / "systems-invalid.json"

# A robust subset of the first-slice catalogue ids. The corpus may grow, so
# the tests assert presence, never an exact count.
FIRST_SLICE = (
    "a10a_thunderbolt_ii",
    "su25_frogfoot",
    "l159_alca",
    "cessna_172_skyhawk",
    "jas39c_gripen",
    "fa18e_super_hornet",
    "su57_felon",
    "md500",
    "md530_defender",
    "rah66_comanche",
    "uh60a_black_hawk",
    "light_utility_rotary",
    "mi28_havoc",
    "mi26_halo",
    "aw159_wildcat",
    "ch47_chinook",
    "md500_civil",
)

JsonObject = dict[str, object]


def _source(
    source_id: str,
    tier: int,
    source_type: str,
    primary_held: bool = True,
) -> JsonObject:
    return {
        "source_id": source_id,
        "tier": tier,
        "type": source_type,
        "title": "FIXTURE source, not a held document",
        "identifier": "FIXTURE",
        "retrieved": "2026-10-05",
        "primary_held": primary_held,
        "sha256": "",
    }


def _value(
    value: object, unit: str, source: str, grade: str = "documented", **extra: object
) -> JsonObject:
    entry: JsonObject = {
        "value": value,
        "unit": unit,
        "source": source,
        "locator": "fixture locator",
        "state": "fixture state",
        "grade": grade,
    }
    entry.update(extra)
    return entry


def _record() -> JsonObject:
    """A complete fixed-wing entry. Fixture only, no real aircraft."""
    return {
        "catalogue_id": "fixture_aircraft",
        "variant_id": "fixture_variant",
        "game_class": "FIXTURE_PLANE_F",
        "class_token": "Plane",
        "identity_source": "fx_manual",
        "maker": "FIXTURE",
        "model": "FIXTURE",
        "variant": "FIXTURE",
        "country": "NONE",
        "era": "none",
        "vehicle_type": "fixed_wing",
        "runtime_ready": True,
        "values": {
            "operating_weight_kg": _value(1, "kg", "fx_manual"),
            "thrust_kn": _value(1.0, "kN", "fx_manual"),
            "reference_speed_ms": _value(1.0, "m/s", "fx_manual"),
        },
    }


def _field(record: JsonObject, name: str) -> JsonObject:
    values = cast("dict[str, object]", record["values"])
    return cast("JsonObject", values[name])


def _values(record: JsonObject) -> dict[str, object]:
    return cast("dict[str, object]", record["values"])


def _sources() -> list[object]:
    return [
        _source("fx_manual", 2, "manual", True),
        _source("fx_compilation", 5, "compilation", False),
        _source("fx_engine_config", 5, "engine_config", False),
    ]


def _by_id() -> dict[str, JsonObject]:
    return {
        str(raw["source_id"]): cast("JsonObject", raw)
        for raw in _sources()
        if isinstance(raw, dict)
    }


def _load_real() -> catalogue.CatalogueLoad:
    return catalogue.load(REAL_DATA, profile=catalogue.AIRCRAFT_PROFILE)


def _real_sources() -> list[JsonObject]:
    raw = json.loads((REAL_DATA / "sources.json").read_text(encoding="utf-8"))
    return [cast("JsonObject", item) for item in raw]


def _real_by_id() -> dict[str, JsonObject]:
    return {str(item["source_id"]): item for item in _real_sources()}


class ValidatorContractTest(unittest.TestCase):
    """The value and record rules, on temp fixtures only."""

    def errors(self, record: JsonObject) -> list[str]:
        return v.validate_corpus(_sources(), [record], [])

    def assert_rejects(self, record: JsonObject, needle: str) -> None:
        errors = self.errors(record)
        self.assertTrue(
            any(needle in error for error in errors),
            f"no error naming {needle!r} in {errors}",
        )

    def test_a_good_record_passes(self) -> None:
        self.assertEqual([], self.errors(_record()))

    def test_a_missing_source_is_rejected(self) -> None:
        record = _record()
        del _field(record, "operating_weight_kg")["source"]
        self.assert_rejects(record, "source is required")

    def test_a_missing_unit_is_rejected(self) -> None:
        record = _record()
        del _field(record, "operating_weight_kg")["unit"]
        self.assert_rejects(record, "unit is required")

    def test_an_engine_config_source_is_forbidden_for_a_value(self) -> None:
        record = _record()
        _field(record, "operating_weight_kg")["source"] = "fx_engine_config"
        self.assert_rejects(record, "forbidden for a value")

    def test_a_tier5_source_needs_grade_claimed(self) -> None:
        record = _record()
        _field(record, "operating_weight_kg")["source"] = "fx_compilation"
        self.assert_rejects(record, "tier 5 source needs grade claimed")

    def test_a_runtime_field_never_resolves_from_an_unheld_source(self) -> None:
        record = _record()
        _field(record, "operating_weight_kg")["source"] = "fx_compilation"
        _field(record, "operating_weight_kg")["grade"] = "claimed"
        _field(record, "operating_weight_kg")["state"] = "UNSOURCED fixture lead"
        self.assert_rejects(record, "resolves from the unheld source")

    def test_an_unheld_value_needs_the_unsourced_marker(self) -> None:
        record = _record()
        _field(record, "operating_weight_kg")["source"] = "fx_compilation"
        _field(record, "operating_weight_kg")["grade"] = "claimed"
        _field(record, "operating_weight_kg")["state"] = "fixture state"
        self.assert_rejects(record, f"state to start with {v.UNSOURCED_MARKER}")

    def test_a_runtime_ready_record_needs_every_runtime_field(self) -> None:
        record = _record()
        del _values(record)["thrust_kn"]
        del _values(record)["reference_speed_ms"]
        self.assert_rejects(record, "misses required field rated_power_w")


class RealCorpusTest(unittest.TestCase):
    """The real corpus is the first-slice oracle."""

    def test_the_real_corpus_passes_the_validator_in_process(self) -> None:
        self.assertEqual([], v.run(REAL_DATA))

    def test_the_loader_reports_no_errors(self) -> None:
        self.assertEqual([], _load_real().errors)

    def test_the_first_slice_sentinels_are_present(self) -> None:
        ids = {entry.catalogue_id for entry in _load_real().entries}
        for sentinel in FIRST_SLICE:
            self.assertIn(sentinel, ids)

    def test_the_catalogue_ids_and_variant_ids_are_unique(self) -> None:
        load = _load_real()
        catalogue_ids = [entry.catalogue_id for entry in load.entries]
        variant_ids = [entry.variant_id for entry in load.entries]
        self.assertEqual(len(catalogue_ids), len(set(catalogue_ids)))
        self.assertEqual(len(variant_ids), len(set(variant_ids)))

    def test_every_binding_names_a_known_catalogue_id(self) -> None:
        load = _load_real()
        known = {entry.catalogue_id for entry in load.entries}
        for binding in load.bindings:
            self.assertIn(binding.catalogue_id, known, binding.game_class)

    def test_no_catalogue_value_names_an_engine_source(self) -> None:
        by_id = _real_by_id()
        for entry in _load_real().entries:
            for name, raw in entry.values.items():
                if not isinstance(raw, dict):
                    continue
                source_id = raw.get("source")
                if not isinstance(source_id, str) or not source_id:
                    continue
                source = by_id.get(source_id)
                self.assertIsNotNone(source, f"{entry.catalogue_id}.{name}")
                assert source is not None
                self.assertNotIn(
                    source.get("type"),
                    v.ENGINE_SOURCE_TYPES,
                    f"{entry.catalogue_id}.{name} names {source_id}",
                )

    def test_every_unheld_value_carries_the_unsourced_state(self) -> None:
        by_id = _real_by_id()
        for entry in _load_real().entries:
            for name, raw in entry.values.items():
                if not isinstance(raw, dict):
                    continue
                source_id = raw.get("source")
                source = by_id.get(source_id) if isinstance(source_id, str) else None
                if source is None or source.get("primary_held") is not False:
                    continue
                state = raw.get("state")
                self.assertIsInstance(state, str, f"{entry.catalogue_id}.{name}")
                assert isinstance(state, str)
                self.assertTrue(
                    state.startswith(v.UNSOURCED_MARKER),
                    f"{entry.catalogue_id}.{name} state {state!r}",
                )

    def test_a_runtime_field_never_resolves_from_an_unheld_source(self) -> None:
        by_id = _real_by_id()
        for entry in _load_real().entries:
            runtime = v.REQUIRED_RUNTIME_BY_TYPE.get(entry.vehicle_type, ())
            resolved = catalogue.resolve_fields(
                entry.vehicle_type, entry.values, catalogue.AIRCRAFT_PROFILE
            )
            for field in runtime:
                resolved_field = resolved.get(field)
                if resolved_field is None or resolved_field.grade == "absent":
                    continue
                source = by_id.get(resolved_field.source)
                if source is None:
                    continue
                self.assertIsNot(
                    source.get("primary_held"),
                    False,
                    f"{entry.catalogue_id}.{field} resolves from {resolved_field.source}",
                )

    def test_every_non_lead_resolves_its_runtime_fields(self) -> None:
        for entry in _load_real().entries:
            if entry.runtime_ready is not True:
                continue
            runtime = v.REQUIRED_RUNTIME_BY_TYPE.get(entry.vehicle_type, ())
            resolved = entry.resolved_fields()
            for field in runtime:
                self.assertIn(field, resolved, entry.catalogue_id)
                self.assertNotEqual(
                    "absent", resolved[field].grade, f"{entry.catalogue_id}.{field}"
                )

    def test_the_registry_holds_at_least_the_first_slice_sources(self) -> None:
        self.assertGreaterEqual(len(_real_sources()), 6)

    def test_the_registry_names_every_value_source(self) -> None:
        by_id = _real_by_id()
        for entry in _load_real().entries:
            for name, raw in entry.values.items():
                if not isinstance(raw, dict):
                    continue
                source_id = raw.get("source")
                if isinstance(source_id, str) and source_id:
                    self.assertIn(source_id, by_id, f"{entry.catalogue_id}.{name}")


class FixtureRejectionTest(unittest.TestCase):
    """The negative fixture is the rejection oracle."""

    def test_the_fixtures_path_is_never_treated_as_production(self) -> None:
        self.assertTrue(v.run(FIXTURES))

    def test_the_fixture_entry_is_rejected_with_a_named_error(self) -> None:
        capture = cast(
            "JsonObject",
            json.loads(FIXTURE_CAPTURE.read_text(encoding="utf-8")),
        )
        sources = json.loads(FIXTURE_SOURCES.read_text(encoding="utf-8"))
        entries = capture.get("entries")
        self.assertIsInstance(entries, list)
        errors = v.validate_corpus(sources, entries, capture.get("conflicts", []))
        self.assertTrue(any("source is required" in error for error in errors), errors)
        self.assertTrue(any("unit is required" in error for error in errors), errors)
        self.assertTrue(
            any("forbidden for a value" in error for error in errors), errors
        )


class SystemsGateTest(unittest.TestCase):
    """The systems registry, the record path and the mutation audit (task 7)."""

    def _valid_document(self) -> JsonObject:
        """A valid systems record document. Fixture only, no real aircraft."""
        return {
            "retrieved": "2026-10-09",
            "sources": [_source("fx_manual", 2, "manual", True)],
            "record": {
                "catalogue_id": "fixture_systems_ok",
                "canonical_name": "FIXTURE",
                "maker": "FIXTURE",
                "model": "FIXTURE",
                "variant": "FIXTURE",
                "variant_id": "fixture_systems_ok_variant",
                "game_class": "FIXTURE_SYSTEMS_OK_F",
                "class_token": "Plane",
                "identity_source": "fx_manual",
                "country": "NONE",
                "era": "none",
                "vehicle_type": "fixed_wing",
                "runtime_ready": False,
                "values": {
                    "fuel_capacity": _value(1000, "L", "fx_manual"),
                    "fuel_type": _value("sentinel", "enum", "fx_manual"),
                    "fuel_consumption_rate": _value(1.5, "kg/s", "fx_manual"),
                    "sfc_kg_kwh": _value(0.3, "kg/kWh", "fx_manual"),
                    "fuel_lhv_mj_kg": _value(43.0, "MJ/kg", "fx_manual"),
                    "engine_design_rpm": _value(6000, "rpm", "fx_manual"),
                    "engine_max_tgt_c": _value(800, "deg C", "fx_manual"),
                    "inertia_xx_kgm2": _value(1000, "kg m^2", "fx_manual"),
                    "bus_voltage_v": _value(28, "V", "fx_manual"),
                    "battery_capacity_ah": _value(25, "Ah", "fx_manual"),
                },
            },
        }

    def test_the_record_path_accepts_a_valid_systems_record(self) -> None:
        errors: list[str] = []
        v.validate_record_document(self._valid_document(), errors)
        self.assertEqual([], errors)

    def test_the_record_path_rejects_the_systems_fixture(self) -> None:
        document = json.loads(SYSTEMS_FIXTURE.read_text(encoding="utf-8"))
        errors: list[str] = []
        v.validate_record_document(document, errors)
        self.assertTrue(
            any("unit gal is not in the vocabulary" in e for e in errors), errors
        )
        self.assertTrue(any("name its formula" in e for e in errors), errors)

    def test_the_fixture_record_cli_fails(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "--record",
                str(SYSTEMS_FIXTURE),
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            check=False,
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("aircraft data gate: FAIL", result.stdout)
        self.assertIn("unit gal is not in the vocabulary", result.stdout)

    def test_a_mutation_to_an_unlisted_unit_is_caught(self) -> None:
        document = self._valid_document()
        errors: list[str] = []
        v.validate_record_document(document, errors)
        self.assertEqual([], errors, "the base record must be clean")

        record = cast("JsonObject", document["record"])
        values = cast("dict[str, object]", record["values"])
        cast("JsonObject", values["fuel_capacity"])["unit"] = "gal"
        mutated: list[str] = []
        v.validate_record_document(document, mutated)
        self.assertTrue(
            any("unit gal is not in the vocabulary" in e for e in mutated), mutated
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutated.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            errors: list[str] = []
            v.validate_record_document(
                json.loads(path.read_text(encoding="utf-8")), errors
            )
        self.assertTrue(errors)

    def test_an_unknown_systems_field_is_an_error(self) -> None:
        document = self._valid_document()
        record = cast("JsonObject", document["record"])
        values = cast("dict[str, object]", record["values"])
        values["fuel_capacity_typo"] = _value(1, "L", "fx_manual")
        errors: list[str] = []
        v.validate_record_document(document, errors)
        self.assertTrue(any("unknown value field" in e for e in errors), errors)

    def test_a_wrong_but_listed_systems_unit_is_an_error(self) -> None:
        document = self._valid_document()
        record = cast("JsonObject", document["record"])
        values = cast("dict[str, object]", record["values"])
        cast("JsonObject", values["fuel_capacity"])["unit"] = "kg"
        errors: list[str] = []
        v.validate_record_document(document, errors)
        self.assertTrue(
            any("does not match the field unit L" in e for e in errors), errors
        )

    def test_the_systems_markers_are_disjoint_from_the_runtime_fields(self) -> None:
        self.assertEqual([], v.systems_marker_errors())


class ValidatorCliTest(unittest.TestCase):
    """The command line proves the same two oracles."""

    def _run(self, data_dir: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--data-dir", str(data_dir)],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            check=False,
        )

    def test_the_real_corpus_cli_passes(self) -> None:
        result = self._run(REAL_DATA)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("aircraft data gate: PASS", result.stdout)

    def test_the_fixtures_cli_fails(self) -> None:
        result = self._run(FIXTURES)
        self.assertEqual(1, result.returncode)
        self.assertIn("aircraft data gate: FAIL", result.stdout)


if __name__ == "__main__":
    unittest.main()
