#!/usr/bin/env python3
"""Vehicle corpus provenance tests (vehicle research corpus, wave 2 task 4).

The validator is the gate. It rejects a value without a unit, a source, a
locator, a state or a compliant grade. It rejects an engine source as a
value source. It rejects an incomplete runtime-ready record, a tracked
record that misses a track field, a held source whose bytes do not match
and an averaged conflict. It rejects a class map with no real-world mapping
source. It accepts a complete record.

The good records live only in this test file and in a temporary directory.
They hold no real vehicle value and they are never written to the corpus.

Run: python3 -m unittest tools.tests.test_vehicle_corpus -v
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import validate_vehicle_data as v  # noqa: E402

VALIDATOR = REPO / "tools" / "validation" / "validate_vehicle_data.py"
REAL_DATA = REPO / "data" / "vehicle"
# The invalid pilot fixture is a test artefact, held outside the production
# records path. Task 8 moved it here so the production corpus stays clean.
INVALID_FIXTURE = REAL_DATA / "fixtures" / "pilot-invalid.json"

# The held bytes of the fixture sources. The CLI tests write them under a
# temporary ``sources/`` directory so the held-source check can name a real
# digest. A documented value needs a held source, so the fixture manual and
# measurement sources are held too.
HELD_BYTES = b"fixture held standard bytes, not a real document"
HELD_SHA = hashlib.sha256(HELD_BYTES).hexdigest()
MANUAL_BYTES = b"fixture held manual bytes, not a real document"
MANUAL_SHA = hashlib.sha256(MANUAL_BYTES).hexdigest()
MEASURE_BYTES = b"fixture held measurement bytes, not a real document"
MEASURE_SHA = hashlib.sha256(MEASURE_BYTES).hexdigest()
HELD_FILES = {
    "fx_standard.bin": HELD_BYTES,
    "fx_manual.bin": MANUAL_BYTES,
    "fx_measure.bin": MEASURE_BYTES,
}


def _write_held_files(dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name, data in HELD_FILES.items():
        (dest / name).write_bytes(data)


def _source(
    source_id: str,
    tier: int,
    source_type: str,
    primary_held: bool = False,
    sha256: str = "",
) -> dict[str, object]:
    return {
        "source_id": source_id,
        "tier": tier,
        "type": source_type,
        "title": "FIXTURE source, not a held document",
        "identifier": "FIXTURE",
        "retrieved": "2026-09-24",
        "primary_held": primary_held,
        "sha256": sha256,
    }


def _sources() -> list[object]:
    return [
        _source("fx_standard", 1, "standard", True, sha256=HELD_SHA),
        _source("fx_manual", 2, "manual", True, sha256=MANUAL_SHA),
        _source("fx_measure", 3, "measurement", True, sha256=MEASURE_SHA),
        _source("fx_maker", 4, "manufacturer"),
        _source("fx_compilation", 5, "compilation"),
        _source("fx_geometry", 5, "engine_geometry"),
        _source("fx_engine_config", 5, "engine_config"),
        _source("fx_class_table", 5, "class_table"),
    ]


def _by_id() -> dict[str, dict[str, object]]:
    by_id: dict[str, dict[str, object]] = {}
    for raw in _sources():
        if isinstance(raw, dict):
            by_id[str(raw["source_id"])] = cast("dict[str, object]", raw)
    return by_id


def _value(
    value: object, unit: str, source: str, grade: str, **extra: object
) -> dict[str, object]:
    entry: dict[str, object] = {
        "value": value,
        "unit": unit,
        "source": source,
        "locator": "fixture locator",
        "state": "fixture state",
        "grade": grade,
    }
    entry.update(extra)
    return entry


def _record() -> dict[str, object]:
    return {
        "variant_id": "fixture_variant",
        "game_class": "FIXTURE_CLASS",
        "class_token": "Wheeled_APC",
        "identity_source": "fx_manual",
        "maker": "FIXTURE",
        "model": "FIXTURE",
        "variant": "FIXTURE",
        "country": "NONE",
        "era": "none",
        "vehicle_type": "wheeled",
        "runtime_ready": True,
        "values": {
            "operating_weight_kg": _value(1, "kg", "fx_manual", "documented"),
            "tyre_width_mm": _value(1, "mm", "fx_manual", "documented"),
            "tyre_diameter_mm": _value(
                1,
                "mm",
                "fx_geometry",
                "derived",
                formula="2 * dist(wheel axis, boundary)",
            ),
            "ground_clearance_mm": _value(1, "mm", "fx_manual", "documented"),
            "net_power_kw": _value(1, "kW", "fx_manual", "documented"),
            "transmission_type": _value("manual", "enum", "fx_manual", "documented"),
            "grousers_state": _value("none", "enum", "fx_manual", "documented"),
            "length_mm": _value(1, "mm", "fx_standard", "standard"),
            "wheel_count": _value(1, "count", "fx_geometry", "documented"),
        },
    }


def _tracked_record() -> dict[str, object]:
    record = _record()
    record["variant_id"] = "fixture_tracked_variant"
    record["class_token"] = "Tracked_APC"
    record["vehicle_type"] = "tracked"
    values = _values(record)
    del values["tyre_width_mm"]
    del values["tyre_diameter_mm"]
    del values["wheel_count"]
    values["track_shoe_width_mm"] = _value(1, "mm", "fx_manual", "documented")
    values["track_pitch_mm"] = _value(1, "mm", "fx_manual", "documented")
    return record


def _catalogue_entry() -> dict[str, object]:
    return {
        "catalogue_id": "fixture_cat",
        "canonical_name": "FIXTURE",
        "maker": "FIXTURE",
        "model": "FIXTURE",
        "variant": "FIXTURE",
        "variant_id": "fixture_cat_variant",
        "vehicle_type": "wheeled",
        "class_token": "Wheeled_APC",
        "country": "NONE",
        "era": "none",
        "aliases": ["fixture"],
        "keywords": ["fixture"],
        "runtime_ready": False,
        "values": {
            "curb_weight_kg": _value(1, "kg", "fx_manual", "documented"),
        },
    }


def _class_map_entry() -> dict[str, object]:
    return {
        "game_class": "FIXTURE_CLASS",
        "class_token": "Wheeled_APC",
        "catalogue_id": "fixture_cat",
        "identity_source": "fx_manual",
        "identity_evidence": "FIXTURE evidence text",
        "grade": "documented",
    }


def _field(record: dict[str, object], name: str) -> dict[str, object]:
    values = cast("dict[str, object]", record["values"])
    return cast("dict[str, object]", values[name])


def _values(record: dict[str, object]) -> dict[str, object]:
    return cast("dict[str, object]", record["values"])


def _conflict() -> dict[str, object]:
    return {
        "entity": "fixture_variant",
        "field": "operating_weight_kg",
        "value_a": 1,
        "source_a": "fx_manual",
        "value_b": 2,
        "source_b": "fx_measure",
        "resolution": "keep both values, keyed by state",
        "rule_applied": "record both, never average",
        "date": "2026-09-24",
    }


def _write_corpus(root: Path) -> None:
    (root / "records").mkdir(parents=True)
    (root / "sources").mkdir()
    _write_held_files(root / "sources")
    (root / "sources.json").write_text(
        json.dumps(_sources(), indent=2), encoding="utf-8"
    )
    capture = {
        "retrieved": "2026-09-24",
        "note": "TEMPORARY FIXTURE, not runtime data",
        "sources": [],
        "records": [_record()],
        "conflicts": [],
    }
    (root / "records" / "temp.json").write_text(
        json.dumps(capture, indent=2), encoding="utf-8"
    )


def _write_catalogue_corpus(root: Path) -> None:
    (root / "sources").mkdir(parents=True)
    _write_held_files(root / "sources")
    (root / "sources.json").write_text(
        json.dumps(_sources(), indent=2), encoding="utf-8"
    )
    (root / "catalogue").mkdir()
    capture = {
        "retrieved": "2026-09-24",
        "note": "TEMPORARY FIXTURE, not runtime data",
        "sources": [],
        "entries": [_catalogue_entry()],
    }
    (root / "catalogue" / "fx_manual.json").write_text(
        json.dumps(capture, indent=2), encoding="utf-8"
    )
    (root / "class_map.json").write_text(
        json.dumps([_class_map_entry()], indent=2), encoding="utf-8"
    )


class ValidatorContractTest(unittest.TestCase):
    def errors(
        self,
        record: dict[str, object],
        sources: list[object] | None = None,
        conflicts: list[object] | None = None,
    ) -> list[str]:
        return v.validate_corpus(
            _sources() if sources is None else sources,
            [record],
            [] if conflicts is None else conflicts,
        )

    def assert_rejects(
        self,
        record: dict[str, object],
        needle: str,
        sources: list[object] | None = None,
        conflicts: list[object] | None = None,
    ) -> None:
        errors = self.errors(record, sources, conflicts)
        self.assertTrue(
            any(needle in error for error in errors),
            f"no error naming {needle!r} in {errors}",
        )

    def test_good_corpus_passes(self) -> None:
        self.assertEqual([], self.errors(_record()))

    def test_missing_source_is_rejected(self) -> None:
        record = _record()
        del _field(record, "operating_weight_kg")["source"]
        self.assert_rejects(record, "operating_weight_kg: source is required")

    def test_unknown_source_is_rejected(self) -> None:
        record = _record()
        _field(record, "operating_weight_kg")["source"] = "ghost"
        self.assert_rejects(record, "unknown source ghost")

    def test_invalid_grade_is_rejected(self) -> None:
        record = _record()
        _field(record, "length_mm")["grade"] = "guessed"
        self.assert_rejects(record, "grade must be one of")

    def test_missing_unit_is_rejected(self) -> None:
        record = _record()
        del _field(record, "operating_weight_kg")["unit"]
        self.assert_rejects(record, "unit is required")

    def test_unit_must_match_the_field(self) -> None:
        record = _record()
        _field(record, "operating_weight_kg")["unit"] = "mm"
        self.assert_rejects(record, "does not match the field unit kg")

    def test_unknown_unit_token_is_rejected(self) -> None:
        record = _record()
        _field(record, "operating_weight_kg")["unit"] = "lb"
        self.assert_rejects(record, "not in the vocabulary")

    def test_missing_state_is_rejected(self) -> None:
        record = _record()
        del _field(record, "operating_weight_kg")["state"]
        self.assert_rejects(record, "state is required")

    def test_missing_locator_is_rejected(self) -> None:
        record = _record()
        del _field(record, "operating_weight_kg")["locator"]
        self.assert_rejects(record, "locator is required")

    def test_missing_value_is_rejected(self) -> None:
        record = _record()
        del _field(record, "operating_weight_kg")["value"]
        self.assert_rejects(record, "value is required")

    def test_engine_config_source_is_forbidden_for_a_value(self) -> None:
        record = _record()
        _field(record, "net_power_kw")["source"] = "fx_engine_config"
        self.assert_rejects(record, "engine_config is forbidden for a value")

    def test_class_table_source_is_forbidden_for_a_value(self) -> None:
        record = _record()
        _field(record, "tyre_width_mm")["source"] = "fx_class_table"
        self.assert_rejects(record, "class_table is forbidden for a value")

    def test_engine_config_source_is_allowed_for_identity(self) -> None:
        record = _record()
        record["identity_source"] = "fx_engine_config"
        self.assertEqual([], self.errors(record))

    def test_incomplete_runtime_ready_record_is_rejected(self) -> None:
        record = _record()
        del _values(record)["net_power_kw"]
        self.assert_rejects(record, "misses required field net_power_kw")

    def test_non_runtime_record_may_omit_a_required_field(self) -> None:
        record = _record()
        record["runtime_ready"] = False
        values = _values(record)
        for name in (
            "tyre_width_mm",
            "tyre_diameter_mm",
            "ground_clearance_mm",
            "net_power_kw",
            "transmission_type",
            "grousers_state",
        ):
            del values[name]
        self.assertEqual([], self.errors(record))

    def test_valid_tracked_record_is_accepted(self) -> None:
        self.assertEqual([], self.errors(_tracked_record()))

    def test_tracked_record_missing_track_width_is_rejected(self) -> None:
        record = _tracked_record()
        del _values(record)["track_shoe_width_mm"]
        self.assert_rejects(record, "misses required field track_shoe_width_mm")

    def test_tracked_record_with_tyres_instead_of_tracks_is_rejected(self) -> None:
        # A tracked record that holds the two tyre fields still misses the
        # two track fields. The tracked set never requires a tyre field.
        record = _tracked_record()
        values = _values(record)
        values["tyre_width_mm"] = _value(1, "mm", "fx_manual", "documented")
        values["tyre_diameter_mm"] = _value(1, "mm", "fx_manual", "documented")
        del values["track_shoe_width_mm"]
        del values["track_pitch_mm"]
        self.assert_rejects(record, "misses required field track_shoe_width_mm")
        self.assert_rejects(record, "misses required field track_pitch_mm")

    def test_published_power_hp_is_accepted(self) -> None:
        record = _record()
        _values(record)["published_power_hp"] = _value(
            370, "hp", "fx_manual", "documented"
        )
        self.assertEqual([], self.errors(record))

    def test_published_power_hp_needs_the_hp_unit(self) -> None:
        record = _record()
        _values(record)["published_power_hp"] = _value(
            276, "kW", "fx_manual", "documented"
        )
        self.assert_rejects(record, "does not match the field unit hp")

    def test_tyre_size_text_is_accepted(self) -> None:
        record = _record()
        _values(record)["tyre_size_text"] = _value(
            "395/85R20", "text", "fx_manual", "documented"
        )
        self.assertEqual([], self.errors(record))

    def test_tyre_size_text_rejects_a_number(self) -> None:
        record = _record()
        _values(record)["tyre_size_text"] = _value(
            395, "text", "fx_manual", "documented"
        )
        self.assert_rejects(record, "value must be a word for unit text")

    def test_track_shoe_count_is_accepted(self) -> None:
        record = _tracked_record()
        _values(record)["track_shoe_count"] = _value(
            63, "count", "fx_manual", "documented"
        )
        self.assertEqual([], self.errors(record))

    def test_standard_grade_needs_a_held_tier1_standard(self) -> None:
        record = _record()
        _field(record, "length_mm")["source"] = "fx_manual"
        _field(record, "length_mm")["grade"] = "standard"
        self.assert_rejects(record, "grade standard needs a held tier 1 standard")

    def test_documented_grade_needs_a_held_source(self) -> None:
        record = _record()
        sources = _sources()
        for raw in sources:
            if isinstance(raw, dict) and raw.get("source_id") == "fx_manual":
                cast("dict[str, object]", raw)["primary_held"] = False
        self.assert_rejects(record, "needs a held tier 2 or 3 manual", sources=sources)

    def test_tier5_source_needs_grade_claimed(self) -> None:
        record = _record()
        _field(record, "length_mm")["source"] = "fx_compilation"
        _field(record, "length_mm")["grade"] = "documented"
        self.assert_rejects(record, "tier 5 source needs grade claimed")

    def test_tier5_compilation_at_claimed_is_accepted(self) -> None:
        record = _record()
        _field(record, "length_mm")["source"] = "fx_compilation"
        _field(record, "length_mm")["grade"] = "claimed"
        self.assertEqual([], self.errors(record))

    def test_engine_geometry_is_limited_to_documented_geometry(self) -> None:
        record = _record()
        _field(record, "operating_weight_kg")["source"] = "fx_geometry"
        self.assert_rejects(record, "engine_geometry is allowed for")

    def test_derived_grade_needs_a_formula(self) -> None:
        record = _record()
        del _field(record, "tyre_diameter_mm")["formula"]
        self.assert_rejects(record, "grade derived")

    def test_unknown_value_field_is_rejected(self) -> None:
        record = _record()
        _values(record)["mass_kg"] = _value(1, "kg", "fx_manual", "documented")
        self.assert_rejects(record, "unknown value field")

    def test_duplicate_variant_is_rejected(self) -> None:
        errors = v.validate_corpus(_sources(), [_record(), _record()], [])
        self.assertTrue(any("duplicate variant_id" in e for e in errors), errors)

    def test_unknown_identity_source_is_rejected(self) -> None:
        record = _record()
        record["identity_source"] = "ghost"
        self.assert_rejects(record, "unknown identity_source ghost")

    def test_invalid_vehicle_type_is_rejected(self) -> None:
        record = _record()
        record["vehicle_type"] = "boat"
        self.assert_rejects(record, "vehicle_type must be one of")

    def test_duplicate_source_is_rejected(self) -> None:
        sources = _sources() + [_source("fx_manual", 2, "manual")]
        errors = v.validate_corpus(sources, [_record()], [])
        self.assertTrue(any("duplicate source_id" in e for e in errors), errors)

    def test_source_tier_out_of_range_is_rejected(self) -> None:
        sources = _sources() + [_source("fx_bad", 9, "manual")]
        errors = v.validate_corpus(sources, [_record()], [])
        self.assertTrue(any("tier must be 1 to 5" in e for e in errors), errors)

    def test_averaged_conflict_is_rejected(self) -> None:
        conflict = _conflict()
        conflict["resolution"] = "averaged to one value"
        self.assert_rejects(
            _record(), "averaged conflict is forbidden", conflicts=[conflict]
        )

    def test_conflict_must_keep_both_values(self) -> None:
        conflict = _conflict()
        del conflict["value_b"]
        self.assert_rejects(_record(), "value_b is required", conflicts=[conflict])

    def test_conflict_source_must_be_known(self) -> None:
        conflict = _conflict()
        conflict["source_b"] = "ghost"
        self.assert_rejects(_record(), "unknown source ghost", conflicts=[conflict])

    def test_a_clean_conflict_is_accepted(self) -> None:
        self.assertEqual([], self.errors(_record(), conflicts=[_conflict()]))


class HeldSourceTest(unittest.TestCase):
    """The held-source digest check. Every held source names its id."""

    def test_held_source_with_matching_bytes_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            _write_held_files(dest)
            errors = v.validate_held_sources(_sources(), dest)
        self.assertEqual([], errors)

    def test_held_source_missing_file_is_rejected_naming_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            _write_held_files(dest)
            (dest / "fx_standard.bin").unlink()
            errors = v.validate_held_sources(_sources(), dest)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("fx_standard", errors[0])
        self.assertIn("missing", errors[0])

    def test_held_source_digest_mismatch_is_rejected_naming_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            _write_held_files(dest)
            (dest / "fx_standard.bin").write_bytes(b"truncated bytes")
            errors = v.validate_held_sources(_sources(), dest)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("fx_standard", errors[0])
        self.assertIn("mismatch", errors[0])

    def test_non_held_source_is_not_checked(self) -> None:
        sources = [_source("fx_manual", 2, "manual")]
        with tempfile.TemporaryDirectory() as tmp:
            errors = v.validate_held_sources(sources, Path(tmp))
        self.assertEqual([], errors)

    def test_blank_digest_on_held_source_is_rejected(self) -> None:
        sources = [_source("fx_standard", 1, "standard", True, sha256="")]
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "fx_standard.bin").write_bytes(HELD_BYTES)
            errors = v.validate_held_sources(sources, dest)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("fx_standard", errors[0])


class CatalogueTest(unittest.TestCase):
    def test_valid_catalogue_entry_is_accepted(self) -> None:
        self.assertEqual([], v.validate_catalogue([_catalogue_entry()], _by_id()))

    def test_duplicate_catalogue_id_is_rejected(self) -> None:
        errors = v.validate_catalogue(
            [_catalogue_entry(), _catalogue_entry()], _by_id()
        )
        self.assertTrue(any("duplicate catalogue_id" in e for e in errors), errors)

    def test_uppercase_alias_is_rejected(self) -> None:
        entry = _catalogue_entry()
        entry["aliases"] = ["Fixture"]
        errors = v.validate_catalogue([entry], _by_id())
        self.assertTrue(any("must be lowercase" in e for e in errors), errors)

    def test_non_string_alias_is_rejected(self) -> None:
        entry = _catalogue_entry()
        entry["aliases"] = [1]
        errors = v.validate_catalogue([entry], _by_id())
        self.assertTrue(any("non-string entry" in e for e in errors), errors)

    def test_keywords_must_be_an_array(self) -> None:
        entry = _catalogue_entry()
        entry["keywords"] = "fixture"
        errors = v.validate_catalogue([entry], _by_id())
        self.assertTrue(any("keywords must be an array" in e for e in errors), errors)

    def test_catalogue_value_needs_a_known_source(self) -> None:
        entry = _catalogue_entry()
        entry["runtime_ready"] = False
        entry["values"] = {
            "operating_weight_kg": _value(1, "kg", "ghost", "documented")
        }
        errors = v.validate_catalogue([entry], _by_id())
        self.assertTrue(any("unknown source ghost" in e for e in errors), errors)

    def test_catalogue_entry_with_an_absent_field_is_accepted(self) -> None:
        # A missing runtime field is a labelled zero, not a refusal. A tracked
        # entry that holds only operating weight still passes the gate.
        entry = _catalogue_entry()
        entry["vehicle_type"] = "tracked"
        entry["values"] = {
            "operating_weight_kg": _value(1, "kg", "fx_manual", "documented"),
        }
        self.assertEqual([], v.validate_catalogue([entry], _by_id()))

    def test_catalogue_entry_with_no_resolvable_field_is_rejected(self) -> None:
        entry = _catalogue_entry()
        entry["values"] = {}
        errors = v.validate_catalogue([entry], _by_id())
        self.assertTrue(any("no runtime field resolves" in e for e in errors), errors)


class ClassMapTest(unittest.TestCase):
    def test_valid_class_map_is_accepted(self) -> None:
        errors = v.validate_class_map([_class_map_entry()], {"fixture_cat"}, _by_id())
        self.assertEqual([], errors)

    def test_token_only_guess_is_rejected(self) -> None:
        entry = {
            "class_token": "Wheeled_APC",
            "catalogue_id": "fixture_cat",
            "grade": "documented",
        }
        errors = v.validate_class_map([entry], {"fixture_cat"}, _by_id())
        self.assertTrue(any("game_class is required" in e for e in errors), errors)
        self.assertTrue(
            any("category guess cannot create a class map" in e for e in errors),
            errors,
        )

    def test_engine_identity_source_is_rejected(self) -> None:
        entry = _class_map_entry()
        entry["identity_source"] = "fx_engine_config"
        errors = v.validate_class_map([entry], {"fixture_cat"}, _by_id())
        self.assertTrue(
            any("category guess cannot create a class map" in e for e in errors),
            errors,
        )

    def test_missing_identity_evidence_is_rejected(self) -> None:
        entry = _class_map_entry()
        del entry["identity_evidence"]
        errors = v.validate_class_map([entry], {"fixture_cat"}, _by_id())
        self.assertTrue(
            any("identity_evidence is required" in e for e in errors), errors
        )

    def test_missing_identity_source_is_rejected(self) -> None:
        entry = _class_map_entry()
        del entry["identity_source"]
        errors = v.validate_class_map([entry], {"fixture_cat"}, _by_id())
        self.assertTrue(any("identity_source is required" in e for e in errors), errors)

    def test_unknown_catalogue_is_rejected(self) -> None:
        errors = v.validate_class_map([_class_map_entry()], {"other_cat"}, _by_id())
        self.assertTrue(any("unknown catalogue_id fixture_cat" in e for e in errors))

    def test_duplicate_game_class_is_rejected(self) -> None:
        errors = v.validate_class_map(
            [_class_map_entry(), _class_map_entry()], {"fixture_cat"}, _by_id()
        )
        self.assertTrue(any("duplicate game_class" in e for e in errors), errors)

    def test_documented_needs_a_tier2_source(self) -> None:
        entry = _class_map_entry()
        entry["identity_source"] = "fx_compilation"
        errors = v.validate_class_map([entry], {"fixture_cat"}, _by_id())
        self.assertTrue(
            any("grade documented needs a tier 2 or tier 3" in e for e in errors),
            errors,
        )

    def test_claimed_accepts_a_compilation(self) -> None:
        entry = _class_map_entry()
        entry["identity_source"] = "fx_compilation"
        entry["grade"] = "claimed"
        errors = v.validate_class_map([entry], {"fixture_cat"}, _by_id())
        self.assertEqual([], errors)


class ValidatorCliTest(unittest.TestCase):
    def test_self_check_returns_no_failures(self) -> None:
        self.assertEqual([], v.self_check())

    def test_self_check_cli_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--self-check"],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("vehicle data gate: PASS", result.stdout)

    def test_red_fixture_is_rejected_with_a_named_error(self) -> None:
        # The invalid pilot fixture lives outside the production records path
        # (task 8 moved it to data/vehicle/fixtures/). The production corpus is
        # clean, so the negative test feeds the fixture through a temp corpus
        # and still proves the validator rejects it with a named error.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vehicle"
            (root / "records").mkdir(parents=True)
            (root / "sources.json").write_text("[]", encoding="utf-8")
            (root / "records" / "pilot-invalid.json").write_bytes(
                INVALID_FIXTURE.read_bytes()
            )
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--data-dir", str(root)],
                capture_output=True,
                text=True,
                cwd=str(REPO),
                check=False,
            )
        self.assertEqual(1, result.returncode)
        self.assertIn("vehicle data gate: FAIL", result.stdout)
        self.assertTrue(
            "source is required" in result.stdout
            or "forbidden for a value" in result.stdout,
            result.stdout,
        )

    def test_the_production_corpus_holds_no_invalid_record(self) -> None:
        # The default validator must pass: the production corpus is empty of
        # invalid records, and the invalid fixture is held outside records/.
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--data-dir", str(REAL_DATA)],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("vehicle data gate: PASS", result.stdout)
        self.assertTrue(INVALID_FIXTURE.is_file(), INVALID_FIXTURE)
        self.assertFalse(
            any(
                (REAL_DATA / "records").glob("*.json"),
            ),
            "the production records path must hold no capture file",
        )

    def test_a_temporary_good_corpus_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vehicle"
            _write_corpus(root)
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--data-dir", str(root)],
                capture_output=True,
                text=True,
                cwd=str(REPO),
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("vehicle data gate: PASS", result.stdout)

    def test_cli_rejects_a_missing_held_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vehicle"
            _write_corpus(root)
            shutil.rmtree(root / "sources")
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--data-dir", str(root)],
                capture_output=True,
                text=True,
                cwd=str(REPO),
                check=False,
            )
        self.assertEqual(1, result.returncode)
        self.assertIn("vehicle data gate: FAIL", result.stdout)
        self.assertIn("fx_standard", result.stdout)
        self.assertIn("missing", result.stdout)

    def test_cli_accepts_a_catalogue_and_class_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vehicle"
            _write_catalogue_corpus(root)
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--data-dir", str(root)],
                capture_output=True,
                text=True,
                cwd=str(REPO),
                check=False,
            )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("vehicle data gate: PASS", result.stdout)

    def test_capture_level_sources_must_stay_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vehicle"
            _write_catalogue_corpus(root)
            path = root / "catalogue" / "fx_manual.json"
            capture = cast(
                "dict[str, object]", json.loads(path.read_text(encoding="utf-8"))
            )
            capture["sources"] = [
                _source("fx_extra", 2, "manual", True, sha256=MANUAL_SHA)
            ]
            path.write_text(json.dumps(capture, indent=2), encoding="utf-8")
            errors = v.run(root)
        self.assertTrue(any("must stay empty" in error for error in errors), errors)

    def test_cli_rejects_a_token_only_class_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "vehicle"
            _write_catalogue_corpus(root)
            (root / "class_map.json").write_text(
                json.dumps(
                    [
                        {
                            "class_token": "Wheeled_APC",
                            "catalogue_id": "fixture_cat",
                            "grade": "documented",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--data-dir", str(root)],
                capture_output=True,
                text=True,
                cwd=str(REPO),
                check=False,
            )
        self.assertEqual(1, result.returncode)
        self.assertIn("vehicle data gate: FAIL", result.stdout)
        self.assertIn("category guess cannot create a class map", result.stdout)


if __name__ == "__main__":
    unittest.main()
