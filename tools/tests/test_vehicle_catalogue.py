#!/usr/bin/env python3
"""Vehicle catalogue and class-map loader tests.

The loader is the shared read path for the vehicle corpus. It reads
``data/vehicle/catalogue/*.json`` and ``data/vehicle/class_map.json`` and
returns typed records. It enforces unique catalogue and variant ids, normalises
aliases and keywords, drops a shared alias with a warning, and rejects a class
map with no real-world mapping source.

The fixtures live in a temporary directory. They hold no real vehicle value
and they are never written to the corpus.

Run: python3 -m unittest tools.tests.test_vehicle_catalogue -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import vehicle_catalogue as vc  # noqa: E402

DATA = REPO / "data" / "vehicle"
CATALOGUE = DATA / "catalogue"
CLASS_MAP = DATA / "class_map.json"

JsonObject = dict[str, object]


def _entry(catalogue_id: str, **overrides: object) -> JsonObject:
    entry: JsonObject = {
        "catalogue_id": catalogue_id,
        "canonical_name": catalogue_id.upper(),
        "maker": "FIXTURE",
        "model": "FIXTURE",
        "variant": "FIXTURE",
        "variant_id": f"{catalogue_id}_variant",
        "vehicle_type": "wheeled",
        "class_token": "",
        "country": "NONE",
        "era": "none",
        "aliases": [],
        "keywords": [],
        "runtime_ready": False,
        "values": {},
    }
    entry.update(overrides)
    return entry


def _capture(entries: list[JsonObject]) -> JsonObject:
    return {
        "retrieved": "2026-09-24",
        "note": "FIXTURE capture, no real vehicle value",
        "sources": [],
        "entries": entries,
    }


def _mapping(game_class: str = "FIXTURE_CLASS", **overrides: object) -> JsonObject:
    record: JsonObject = {
        "game_class": game_class,
        "class_token": "Wheeled_APC",
        "catalogue_id": "fixture_cat",
        "identity_source": "fx_manual",
        "identity_evidence": "FIXTURE evidence text",
        "grade": "documented",
    }
    record.update(overrides)
    return record


def _source(source_id: str, source_type: str) -> JsonObject:
    return {
        "source_id": source_id,
        "tier": 2,
        "type": source_type,
        "title": "FIXTURE source, not a held document",
        "identifier": "FIXTURE",
        "retrieved": "2026-09-24",
    }


def _write(
    root: Path,
    captures: dict[str, JsonObject] | None = None,
    class_map: object | None = None,
    sources: list[JsonObject] | None = None,
) -> Path:
    """Write a temporary corpus. Return its ``vehicle`` directory."""
    (root / "catalogue").mkdir(parents=True, exist_ok=True)
    for name, capture in (captures or {}).items():
        (root / "catalogue" / f"{name}.json").write_text(
            json.dumps(capture), encoding="utf-8"
        )
    if class_map is not None:
        (root / "class_map.json").write_text(json.dumps(class_map), encoding="utf-8")
    if sources is not None:
        (root / "sources.json").write_text(json.dumps(sources), encoding="utf-8")
    return root


class ValidLoadingTest(unittest.TestCase):
    def test_single_entry_loads_with_typed_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(
                Path(tmp),
                captures={"fixture": _capture([_entry("fixture_cat")])},
                class_map=[],
            )
            loaded = vc.load(root, real_source_ids=set())
        self.assertEqual([], loaded.errors)
        self.assertEqual(1, len(loaded.entries))
        entry = loaded.entries[0]
        self.assertEqual("fixture_cat", entry.catalogue_id)
        self.assertEqual("wheeled", entry.vehicle_type)
        self.assertIs(False, entry.runtime_ready)
        self.assertIn("fixturecatvariant", entry.identity_aliases())

    def test_missing_catalogue_dir_and_class_map_load_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            loaded = vc.load(Path(tmp), real_source_ids=set())
        self.assertEqual([], loaded.errors)
        self.assertEqual([], loaded.entries)
        self.assertEqual([], loaded.mappings)
        self.assertEqual({}, loaded.alias_index)

    def test_aliases_and_keywords_are_normalised_and_deduplicated(self) -> None:
        entry = _entry(
            "fixture_cat",
            aliases=["M-ATV", "  matv  ", "M1240"],
            keywords=["Armored Personnel Carrier", "MRAP"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), captures={"fixture": _capture([entry])})
            loaded = vc.load(root, real_source_ids=set())
        self.assertEqual([], loaded.errors)
        record = loaded.entries[0]
        self.assertEqual(("matv", "m1240"), record.aliases)
        self.assertEqual(("armoredpersonnelcarrier", "mrap"), record.keywords)

    def test_non_string_alias_is_reported(self) -> None:
        entry = _entry("fixture_cat", aliases=[1])
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), captures={"fixture": _capture([entry])})
            loaded = vc.load(root, real_source_ids=set())
        self.assertTrue(
            any("aliases holds a non-string entry" in e for e in loaded.errors),
            loaded.errors,
        )


class DuplicateIdTest(unittest.TestCase):
    def test_duplicate_catalogue_id_is_rejected(self) -> None:
        entries = [_entry("fixture_cat"), _entry("fixture_cat")]
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), captures={"fixture": _capture(entries)})
            loaded = vc.load(root, real_source_ids=set())
        self.assertEqual(1, len(loaded.entries))
        self.assertTrue(
            any("duplicate catalogue_id" in e for e in loaded.errors),
            loaded.errors,
        )

    def test_duplicate_variant_id_is_rejected(self) -> None:
        entries = [
            _entry("fixture_one", variant_id="shared_variant"),
            _entry("fixture_two", variant_id="shared_variant"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), captures={"fixture": _capture(entries)})
            loaded = vc.load(root, real_source_ids=set())
        self.assertEqual(1, len(loaded.entries))
        self.assertTrue(
            any("duplicate variant_id shared_variant" in e for e in loaded.errors),
            loaded.errors,
        )


class AliasCollisionTest(unittest.TestCase):
    def test_shared_alias_is_dropped_with_a_warning(self) -> None:
        entries = [
            _entry("fixture_one", aliases=["shared", "alpha"]),
            _entry("fixture_two", aliases=["shared", "beta"]),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), captures={"fixture": _capture(entries)})
            loaded = vc.load(root, real_source_ids=set())
        self.assertNotIn("shared", loaded.alias_index)
        self.assertEqual("fixture_one", loaded.alias_index["alpha"])
        self.assertEqual("fixture_two", loaded.alias_index["beta"])
        self.assertTrue(
            any("alias shared" in w and "dropped" in w for w in loaded.warnings),
            loaded.warnings,
        )

    def test_unique_alias_is_indexed(self) -> None:
        entries = [_entry("fixture_cat", aliases=["only"])]
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(Path(tmp), captures={"fixture": _capture(entries)})
            loaded = vc.load(root, real_source_ids=set())
        self.assertEqual("fixture_cat", loaded.alias_index["only"])


class ClassMapTest(unittest.TestCase):
    def test_empty_class_map_loads_without_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(
                Path(tmp),
                captures={"fixture": _capture([_entry("fixture_cat")])},
                class_map=[],
            )
            loaded = vc.load(root, real_source_ids=set())
        self.assertEqual([], loaded.errors)
        self.assertEqual([], loaded.mappings)

    def test_token_only_mapping_is_rejected(self) -> None:
        record: JsonObject = {
            "class_token": "Wheeled_APC",
            "catalogue_id": "fixture_cat",
            "grade": "documented",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(
                Path(tmp),
                captures={"fixture": _capture([_entry("fixture_cat")])},
                class_map=[record],
            )
            loaded = vc.load(root, real_source_ids={"fx_manual"})
        self.assertEqual([], loaded.mappings)
        self.assertTrue(
            any("game_class is required" in e for e in loaded.errors), loaded.errors
        )
        self.assertTrue(
            any("identity_source is required" in e for e in loaded.errors),
            loaded.errors,
        )

    def test_engine_source_is_rejected(self) -> None:
        record = _mapping(identity_source="fx_engine_config")
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(
                Path(tmp),
                captures={"fixture": _capture([_entry("fixture_cat")])},
                class_map=[record],
            )
            loaded = vc.load(root, real_source_ids={"fx_manual"})
        self.assertEqual([], loaded.mappings)
        self.assertTrue(
            any("is not a real-world mapping source" in e for e in loaded.errors),
            loaded.errors,
        )

    def test_missing_catalogue_is_rejected(self) -> None:
        record = _mapping(catalogue_id="ghost")
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(
                Path(tmp),
                captures={"fixture": _capture([_entry("fixture_cat")])},
                class_map=[record],
            )
            loaded = vc.load(root, real_source_ids={"fx_manual"})
        self.assertEqual([], loaded.mappings)
        self.assertTrue(
            any("unknown catalogue_id ghost" in e for e in loaded.errors),
            loaded.errors,
        )

    def test_real_mapping_source_is_accepted_from_the_registry(self) -> None:
        record = _mapping()
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(
                Path(tmp),
                captures={"fixture": _capture([_entry("fixture_cat")])},
                class_map=[record],
                sources=[_source("fx_manual", "manual")],
            )
            loaded = vc.load(root)
        self.assertEqual([], loaded.errors)
        self.assertEqual(1, len(loaded.mappings))
        mapping = loaded.mappings[0]
        self.assertEqual("FIXTURE_CLASS", mapping.game_class)
        self.assertEqual("fixture_cat", mapping.catalogue_id)
        self.assertEqual("fx_manual", mapping.identity_source)

    def test_engine_registry_source_is_not_a_mapping_source(self) -> None:
        record = _mapping(identity_source="fx_engine_config")
        with tempfile.TemporaryDirectory() as tmp:
            root = _write(
                Path(tmp),
                captures={"fixture": _capture([_entry("fixture_cat")])},
                class_map=[record],
                sources=[_source("fx_engine_config", "engine_config")],
            )
            loaded = vc.load(root)
        self.assertEqual([], loaded.mappings)
        self.assertTrue(
            any("is not a real-world mapping source" in e for e in loaded.errors),
            loaded.errors,
        )


class RealCorpusTest(unittest.TestCase):
    def test_held_entries_and_mappings_load_clean(self) -> None:
        loaded = vc.load(DATA)
        self.assertEqual([], loaded.errors, loaded.errors)
        ids = {entry.catalogue_id for entry in loaded.entries}
        for sentinel in (
            "m_atv_m1240",
            "m113a2",
            "m923a2",
            "honda_civic_6gen_sedan",
            "kawasaki_ninja_250r_ex250f",
            "m1_abrams",
            "m2_m3_bradley",
            "cougar_4x4",
        ):
            self.assertIn(sentinel, ids)
        self.assertGreaterEqual(len(ids), 47)
        # Six records in the committed class map, each an engine class-table
        # binding at grade claimed.
        self.assertEqual(6, len(loaded.mappings))
        for mapping in loaded.mappings:
            self.assertEqual("claimed", mapping.grade)

    def test_leads_are_loaded_but_not_runtime_ready(self) -> None:
        loaded = vc.load(DATA)
        # The corpus holds one complete entry: the Kawasaki service manual
        # motorcycle resolves every runtime field. Every other entry is a
        # sourced lead, a partial record that is not runtime-ready.
        ready = [entry.catalogue_id for entry in loaded.entries if entry.runtime_ready]
        self.assertEqual(["kawasaki_ninja_250r_ex250f"], ready)
        for entry in loaded.entries:
            with self.subTest(entry=entry.catalogue_id):
                if entry.runtime_ready:
                    continue
                self.assertIs(False, entry.runtime_ready)
                self.assertEqual("", entry.class_token)

    def test_real_alias_index_holds_the_lead_aliases(self) -> None:
        loaded = vc.load(DATA)
        self.assertEqual("m_atv_m1240", loaded.alias_index["m1240"])
        self.assertEqual("m113a2", loaded.alias_index["m113"])

    def test_real_class_map_holds_one_claimed_binding_per_entry(self) -> None:
        records: object = json.loads(CLASS_MAP.read_text(encoding="utf-8"))
        self.assertIsInstance(records, list)
        assert isinstance(records, list)
        # Six ground tokens now carry one class-map binding each.
        self.assertEqual(6, len(records))
        for record in records:
            self.assertIsInstance(record, dict)
            entry = cast("dict[str, object]", record)
            self.assertEqual("claimed", entry["grade"])
            self.assertEqual("aee_class_table", entry["identity_source"])
        self.assertTrue(CATALOGUE.is_dir())

    def test_catalogue_values_are_preserved_verbatim(self) -> None:
        loaded = vc.load(DATA)
        matv = next(e for e in loaded.entries if e.catalogue_id == "m_atv_m1240")
        values = cast("dict[str, object]", matv.values)
        curb = cast("dict[str, object]", values["curb_weight_kg"])
        self.assertEqual(11123, curb["value"])
        self.assertEqual("documented", curb["grade"])
        self.assertIn("gross_weight_kg", values)
        self.assertNotIn("operating_weight_kg", values)


class TyreSizeParserTest(unittest.TestCase):
    """The named size-code derivation. Geometry only, never a real-world claim."""

    def test_metric_radial_width_is_the_first_figure(self) -> None:
        width, diameter = vc.parse_tyre_size("395/85R20")
        self.assertEqual(395.0, width)
        self.assertAlmostEqual(20 * vc.INCH_TO_MM + 2 * 395 * 0.85, diameter)

    def test_metric_cross_ply_width_is_the_first_figure(self) -> None:
        width, diameter = vc.parse_tyre_size("130/80-16")
        self.assertEqual(130.0, width)
        self.assertAlmostEqual(16 * vc.INCH_TO_MM + 2 * 130 * 0.80, diameter)

    def test_metric_dash_before_a_radial_mark_is_accepted(self) -> None:
        width, diameter = vc.parse_tyre_size("110/80-R19")
        self.assertEqual(110.0, width)
        self.assertAlmostEqual(19 * vc.INCH_TO_MM + 2 * 110 * 0.80, diameter)

    def test_metric_with_a_space_before_the_radial_mark(self) -> None:
        width, diameter = vc.parse_tyre_size("395/85 R20")
        self.assertEqual(395.0, width)
        self.assertAlmostEqual(20 * vc.INCH_TO_MM + 2 * 395 * 0.85, diameter)

    def test_inch_colon_form_keeps_the_aspect_100_conversion(self) -> None:
        width, diameter = vc.parse_tyre_size("14:00 x R20")
        self.assertAlmostEqual(14.0 * vc.INCH_TO_MM, width, places=4)
        self.assertAlmostEqual((20 + 2 * 14.0) * vc.INCH_TO_MM, diameter)

    def test_inch_dash_and_x_forms_keep_the_conversion(self) -> None:
        for code in ("14.00-20", "14x20"):
            with self.subTest(code=code):
                width, diameter = vc.parse_tyre_size(code)
                self.assertAlmostEqual(14.0 * vc.INCH_TO_MM, width, places=4)
                self.assertAlmostEqual((20 + 2 * 14.0) * vc.INCH_TO_MM, diameter)

    def test_malformed_and_empty_forms_are_rejected(self) -> None:
        for code in (
            "",
            "   ",
            "unknown",
            "130/80",
            "130/80-",
            "/80-16",
            "130//80-16",
            "395/8520",
        ):
            with self.subTest(code=code):
                self.assertIsNone(vc.parse_tyre_size(code))

    def test_derivation_keeps_source_and_state_for_a_cross_ply_code(self) -> None:
        values: JsonObject = {
            "tyre_size_text": {
                "value": "130/80-16",
                "unit": "text",
                "source": "fx_manual",
                "locator": "section 2",
                "state": "staged",
                "grade": "documented",
            }
        }
        field = vc.resolve_field(values, "tyre_width_mm")
        self.assertEqual("derived", field.grade)
        self.assertEqual("fx_manual", field.source)
        self.assertEqual("section 2", field.locator)
        self.assertIn("derived from the size code 130/80-16", field.state)


if __name__ == "__main__":
    unittest.main()
