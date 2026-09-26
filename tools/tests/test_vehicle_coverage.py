#!/usr/bin/env python3
"""Vehicle coverage guard tests (vehicle research corpus, wave 3 task 7).

The coverage logic lives in the production generator
``tools/validation/gen_vehicle_coverage.py``. This module imports it. The
tests cover the build, the guard and the generated artefacts.

The coverage guard gives every token in ``data/vehicle/classes.json`` one
state. The states are ``recorded``, ``lead``, ``no_source`` and
``excluded_non_ground``. A non-ground token is ``excluded_non_ground``. A
ground token is ``recorded`` only when a runtime-ready catalogue entry holds
it. No token leaves the inventory in silence.

The committed ``coverage.json`` must match a fresh build, so the rows are
derived, not hand-maintained.

Run: python3 -m unittest tools.tests.test_vehicle_coverage -v
     python3 tools/tests/test_vehicle_coverage.py --report
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from typing import cast

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_vehicle_coverage as g  # noqa: E402
from tools.validation import validate_vehicle_data as v  # noqa: E402
from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

DATA = REPO / "data" / "vehicle"

JsonObject = dict[str, object]


def _as_sequence(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"expected an array, got {type(value).__name__}")
    return list(cast("list[object]", value))


def _entries(payload: JsonObject) -> list[JsonObject]:
    return g.entries(payload)


def _live_rows(payload: JsonObject) -> list[JsonObject]:
    """Return the token rows without copying them, for in-place edits."""
    rows: list[JsonObject] = []
    for item in _as_sequence(payload.get("tokens")):
        if not isinstance(item, dict):
            raise TypeError("coverage row must be an object")
        rows.append(cast("JsonObject", item))
    return rows


def _row(coverage: JsonObject, token: str) -> JsonObject:
    for row in _live_rows(coverage):
        if row.get("token") == token:
            return row
    raise AssertionError(f"no coverage row for {token}")


def _token(
    token: str,
    is_ground: bool,
    exclusion_reason: str | None = None,
    kind: str = "engine_base",
) -> JsonObject:
    return {
        "token": token,
        "kind": kind,
        "is_ground": is_ground,
        "exclusion_reason": exclusion_reason,
        "provenance": ["addons/probe.sqf:1"],
    }


def _classes(*tokens: JsonObject) -> JsonObject:
    return {"schema": "aee.vehicle.class_inventory/1", "tokens": list(tokens)}


def _ready_record(token: str, variant_id: str) -> JsonObject:
    values: JsonObject = {}
    for field in v.REQUIRED_RUNTIME:
        values[field] = {
            "value": 1,
            "unit": v.FIELD_UNITS[field],
            "source": "fx_manual",
            "locator": "probe locator",
            "state": "probe state",
            "grade": "documented",
        }
    return {
        "variant_id": variant_id,
        "class_token": token,
        "vehicle_type": "wheeled",
        "runtime_ready": True,
        "values": values,
    }


def _recorded(*records: JsonObject) -> dict[str, set[str]]:
    """Build a token-to-variants map from fixture records."""
    out: dict[str, set[str]] = {}
    for record in records:
        out.setdefault(str(record["class_token"]), set()).add(str(record["variant_id"]))
    return out


class CoverageBuildTest(unittest.TestCase):
    def test_non_ground_token_is_excluded(self) -> None:
        payload = g.build_coverage(
            _classes(_token("Air", False, "no positive ground class-table row")),
            {},
        )
        row = _row(payload, "Air")
        self.assertEqual(row["state"], g.NON_GROUND_STATE)
        self.assertEqual(row["reason"], "no positive ground class-table row")

    def test_ground_token_without_a_record_is_no_source(self) -> None:
        payload = g.build_coverage(_classes(_token("Tank", True)), {})
        row = _row(payload, "Tank")
        self.assertEqual(row["state"], g.GROUND_ABSENT_STATE)
        self.assertIsNone(row["variant"])

    def test_ground_token_with_one_record_is_recorded(self) -> None:
        payload = g.build_coverage(
            _classes(_token("Tank", True)), {"Tank": {"tank_v1"}}
        )
        row = _row(payload, "Tank")
        self.assertEqual(row["state"], "recorded")
        self.assertEqual(row["variant"], "tank_v1")

    def test_ground_token_with_two_records_is_lead(self) -> None:
        payload = g.build_coverage(_classes(_token("Tank", True)), {"Tank": {"a", "b"}})
        row = _row(payload, "Tank")
        self.assertEqual(row["state"], "lead")
        self.assertIsNone(row["variant"])

    def test_a_researched_token_without_a_record_is_lead(self) -> None:
        payload = g.build_coverage(
            _classes(_token("Tank", True)), {}, {"Tank": "researched lead"}
        )
        row = _row(payload, "Tank")
        self.assertEqual(row["state"], "lead")
        self.assertEqual(row["reason"], "researched lead")
        self.assertIsNone(row["variant"])

    def test_a_runtime_ready_record_overrides_a_researched_lead(self) -> None:
        payload = g.build_coverage(
            _classes(_token("Tank", True)),
            {"Tank": {"tank_v1"}},
            {"Tank": "researched lead"},
        )
        row = _row(payload, "Tank")
        self.assertEqual(row["state"], "recorded")
        self.assertEqual(row["variant"], "tank_v1")

    def test_a_recorded_token_makes_the_token_recorded(self) -> None:
        ready = _recorded(_ready_record("Tank", "tank_v1"))
        payload = g.build_coverage(_classes(_token("Tank", True)), ready)
        row = _row(payload, "Tank")
        self.assertEqual("recorded", row["state"])
        self.assertEqual("tank_v1", row["variant"])

    def test_a_tracked_binding_records_through_its_token(self) -> None:
        ready = _recorded(_ready_record("Tracked_APC", "m113a2"))
        payload = g.build_coverage(_classes(_token("Tracked_APC", True)), ready)
        row = _row(payload, "Tracked_APC")
        self.assertEqual("recorded", row["state"])
        self.assertEqual("m113a2", row["variant"])

    def test_a_token_with_no_recorded_variant_is_no_source(self) -> None:
        payload = g.build_coverage(_classes(_token("Car", True)), {})
        row = _row(payload, "Car")
        self.assertEqual(g.GROUND_ABSENT_STATE, row["state"])

    def test_build_keeps_every_token(self) -> None:
        classes = _classes(_token("Tank", True), _token("Air", False, "x"))
        self.assertEqual(len(_entries(g.build_coverage(classes, {}))), 2)


class CoverageGuardTest(unittest.TestCase):
    def _classes_and_coverage(self) -> tuple[JsonObject, JsonObject]:
        classes = _classes(_token("Tank", True), _token("Air", False, "air row"))
        return classes, g.build_coverage(classes, {})

    def test_a_clean_table_has_no_errors(self) -> None:
        classes, coverage = self._classes_and_coverage()
        self.assertEqual([], g.coverage_errors(classes, coverage, {}))

    def test_a_dropped_token_is_reported_by_name(self) -> None:
        classes, coverage = self._classes_and_coverage()
        coverage["tokens"] = [
            row for row in _entries(coverage) if row.get("token") != "Tank"
        ]
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any("coverage token Tank: no entry" in error for error in errors),
            errors,
        )

    def test_an_extra_token_is_reported(self) -> None:
        classes, coverage = self._classes_and_coverage()
        rows = _entries(coverage)
        rows.append(
            g._coverage_row(
                "Ghost", "engine_base", True, g.GROUND_ABSENT_STATE, None, "x"
            )
        )
        coverage["tokens"] = rows
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any(
                "coverage token Ghost: not in the class inventory" in e for e in errors
            ),
            errors,
        )

    def test_a_duplicate_token_is_reported(self) -> None:
        classes, coverage = self._classes_and_coverage()
        rows = _entries(coverage)
        rows.append(dict(rows[0]))
        coverage["tokens"] = rows
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any("coverage token Tank: duplicate entry" in error for error in errors),
            errors,
        )

    def test_a_lead_token_needs_a_reason(self) -> None:
        classes, coverage = self._classes_and_coverage()
        _row(coverage, "Tank")["state"] = "lead"
        _row(coverage, "Tank")["reason"] = None
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any("coverage token Tank: lead token needs a reason" in e for e in errors),
            errors,
        )

    def test_a_lead_token_hiding_a_record_is_reported(self) -> None:
        classes, coverage = self._classes_and_coverage()
        _row(coverage, "Tank")["state"] = "lead"
        _row(coverage, "Tank")["reason"] = "researched lead"
        errors = g.coverage_errors(classes, coverage, {"Tank": {"tank_v1"}})
        self.assertTrue(
            any(
                "coverage token Tank: state lead hides a recorded row" in e
                for e in errors
            ),
            errors,
        )

    def test_a_recorded_ground_token_needs_a_record(self) -> None:
        classes, coverage = self._classes_and_coverage()
        _row(coverage, "Tank")["state"] = "recorded"
        _row(coverage, "Tank")["variant"] = "tank_v1"
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any(
                "coverage token Tank: recorded without an emitted row and binding"
                in error
                for error in errors
            ),
            errors,
        )

    def test_a_recorded_token_needs_the_matching_variant(self) -> None:
        classes, coverage = self._classes_and_coverage()
        _row(coverage, "Tank")["state"] = "recorded"
        _row(coverage, "Tank")["variant"] = "other"
        errors = g.coverage_errors(classes, coverage, {"Tank": {"tank_v1"}})
        self.assertTrue(
            any("coverage token Tank: recorded variant" in error for error in errors),
            errors,
        )

    def test_a_non_ground_token_must_be_excluded(self) -> None:
        classes, coverage = self._classes_and_coverage()
        _row(coverage, "Air")["state"] = g.GROUND_ABSENT_STATE
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any("coverage token Air: non-ground token must be" in e for e in errors),
            errors,
        )

    def test_a_ground_token_cannot_be_excluded(self) -> None:
        classes, coverage = self._classes_and_coverage()
        _row(coverage, "Tank")["state"] = g.NON_GROUND_STATE
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any("coverage token Tank: ground token cannot be" in e for e in errors),
            errors,
        )

    def test_an_unknown_state_is_reported(self) -> None:
        classes, coverage = self._classes_and_coverage()
        _row(coverage, "Tank")["state"] = "maybe"
        errors = g.coverage_errors(classes, coverage, {})
        self.assertTrue(
            any("coverage token Tank: state 'maybe'" in e for e in errors),
            errors,
        )


class RealCorpusCoverageTest(unittest.TestCase):
    classes: JsonObject = {}
    recorded: dict[str, set[str]] = {}
    coverage: JsonObject = {}

    def setUp(self) -> None:
        self.classes = g.load_classes(DATA)
        self.recorded = g.recorded_variants(g.load_catalogue(DATA))
        self.coverage = g.load_coverage(DATA)

    def test_the_committed_table_holds_every_token(self) -> None:
        inventory = [str(entry.get("token")) for entry in _entries(self.classes)]
        rows = [str(row.get("token")) for row in _entries(self.coverage)]
        self.assertEqual(
            len(rows), len(set(rows)), "coverage.json has a duplicate token"
        )
        missing = [token for token in inventory if token not in rows]
        self.assertEqual([], missing, f"coverage.json drops {missing}")

    def test_the_committed_table_matches_a_fresh_build(self) -> None:
        self.assertEqual(
            g.build_coverage(self.classes, self.recorded, g.LEAD_CANDIDATES),
            self.coverage,
        )

    def test_the_guard_reports_no_errors(self) -> None:
        errors = g.coverage_errors(self.classes, self.coverage, self.recorded)
        self.assertEqual([], errors, "\n".join(errors))

    def test_the_recorded_tokens_are_the_mapped_entries(self) -> None:
        # Six emitted rows and six class-map bindings -> six recorded
        # tokens, each carrying its one variant.
        self.assertEqual(
            {
                "Car": {"honda_civic_6gen_sedan"},
                "Truck": {"m923a2"},
                "Tracked_APC": {"m113a2"},
                "MRAP": {"m_atv_m1240"},
                "Tank": {"m1_abrams"},
                "Wheeled_APC": {"btr_80"},
            },
            self.recorded,
        )

    def test_the_researched_lead_candidates_are_now_recorded(self) -> None:
        # The researched lead candidates (MRAP, Tracked_APC, Wheeled_APC) now
        # hold an emitted row and a class-map binding, so the committed table
        # records them and carries no bare lead. The lead render path stays
        # covered by CoverageBuildTest.
        rows = {row.get("token"): row for row in _entries(self.coverage)}
        for token in g.LEAD_CANDIDATES:
            self.assertEqual("recorded", rows[token]["state"], token)
        leads = [token for token, row in rows.items() if row["state"] == "lead"]
        self.assertEqual([], leads)

    def test_every_ground_token_is_recorded_lead_or_no_source(self) -> None:
        rows = {row.get("token"): row for row in _entries(self.coverage)}
        for entry in _entries(self.classes):
            if entry.get("is_ground") is not True:
                continue
            row = rows[str(entry.get("token"))]
            self.assertIn(row["state"], ("recorded", "lead", g.GROUND_ABSENT_STATE))

    def test_the_ground_set_matches_the_inventory(self) -> None:
        ground = [
            entry.get("token")
            for entry in _entries(self.classes)
            if entry.get("is_ground") is True
        ]
        self.assertEqual(7, len(ground), ground)

    def test_every_token_is_covered(self) -> None:
        self.assertEqual(len(_entries(self.classes)), len(_entries(self.coverage)))


class GeneratedArtefactTest(unittest.TestCase):
    """The three reports carry the exact gaps the corpus holds."""

    classes: JsonObject = {}
    load: catalogue.CatalogueLoad = catalogue.CatalogueLoad([], [], {}, [], [])
    coverage: JsonObject = {}
    audit: str = ""
    gaps: str = ""
    mapping: str = ""

    def setUp(self) -> None:
        self.classes = g.load_classes(DATA)
        self.load = g.load_catalogue(DATA)
        self.coverage = g.load_coverage(DATA)
        self.audit = (DATA / g.COVERAGE_REPORT).read_text(encoding="utf-8")
        self.gaps = (DATA / g.SOURCE_GAPS_REPORT).read_text(encoding="utf-8")
        self.mapping = (DATA / g.CLASS_MAPPING_REPORT).read_text(encoding="utf-8")

    def test_the_audit_has_a_row_for_every_token(self) -> None:
        for row in _entries(self.coverage):
            self.assertIn(f"`{row.get('token')}`", self.audit)

    def test_the_audit_counts_the_recorded_rows(self) -> None:
        # Six class-map bindings each have an emitted runtime row.
        self.assertIn("recorded: 6", self.audit)
        self.assertIn("Runtime rows: 6", self.audit)

    def test_source_gaps_lists_every_catalogue_entry(self) -> None:
        for entry in self.load.entries:
            self.assertIn(entry.catalogue_id, self.gaps)

    def test_source_gaps_names_the_next_source_class_per_absent_field(self) -> None:
        # The report lists a source class for each absent runtime field. The
        # derived fields are not absent, so they are not gap targets.
        for field in (
            "ground_clearance_mm",
            "track_shoe_width_mm",
            "track_pitch_mm",
            "tyre_width_mm",
            "tyre_diameter_mm",
            "grousers_state",
        ):
            self.assertIn(g.NEXT_SOURCE_CLASS[field], self.gaps)

    def test_source_gaps_holds_every_held_locator(self) -> None:
        # Each held runtime field keeps its source and locator, so the report
        # carries the exact provenance, not just the gap targets.
        for entry in self.load.entries:
            required = v.REQUIRED_RUNTIME_BY_TYPE.get(entry.vehicle_type, ())
            for field in required:
                value = entry.values.get(field)
                if isinstance(value, dict):
                    self.assertIn(str(value.get("locator")), self.gaps)

    def test_source_gaps_lists_the_expected_absent_fields(self) -> None:
        self.assertIn("| `track_shoe_width_mm` |", self.gaps)
        self.assertIn("| `track_pitch_mm` |", self.gaps)
        self.assertIn("| `tyre_width_mm` |", self.gaps)
        self.assertIn("| `ground_clearance_mm` |", self.gaps)
        # The derived operating weight and net power are listed with their
        # grade, not as absent gap targets.
        self.assertIn("| `operating_weight_kg` | derived |", self.gaps)
        self.assertIn("| `net_power_kw` | derived |", self.gaps)

    def test_class_mapping_gaps_lists_every_ground_token(self) -> None:
        for entry in _entries(self.classes):
            if entry.get("is_ground") is not True:
                continue
            self.assertIn(f"| `{entry.get('token')}` |", self.mapping)

    def test_class_mapping_gaps_names_the_mapping_source_class(self) -> None:
        self.assertIn(g.CLASS_MAP_SOURCE_CLASS, self.mapping)

    def test_the_committed_reports_match_a_fresh_build(self) -> None:
        self.assertEqual(0, g.check_all(DATA))


class CoverageCheckModeTest(unittest.TestCase):
    """`--check` proves freshness and writes nothing."""

    def _copy_corpus(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        data = tmp / "vehicle"
        data.mkdir()
        for name in ("classes.json", "class_map.json", "sources.json"):
            shutil.copy(DATA / name, data / name)
        shutil.copytree(DATA / "catalogue", data / "catalogue")
        return data

    def test_a_fresh_write_passes_the_check(self) -> None:
        data = self._copy_corpus()
        g.write_all(data)
        self.assertEqual(0, g.check_all(data))

    def test_check_writes_nothing(self) -> None:
        data = self._copy_corpus()
        self.assertEqual(1, g.check_all(data))
        for name in g.ARTEFACTS:
            self.assertFalse((data / name).exists(), name)

    def test_a_missing_output_is_reported(self) -> None:
        data = self._copy_corpus()
        g.write_all(data)
        (data / g.SOURCE_GAPS_REPORT).unlink()
        self.assertEqual(1, g.check_all(data))

    def test_a_stale_output_is_reported(self) -> None:
        data = self._copy_corpus()
        g.write_all(data)
        path = data / g.COVERAGE_OUT
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assertEqual(1, g.check_all(data))

    def test_a_written_table_matches_the_committed_table(self) -> None:
        data = self._copy_corpus()
        g.write_all(data)
        self.assertEqual(
            (DATA / g.COVERAGE_OUT).read_text(encoding="utf-8"),
            (data / g.COVERAGE_OUT).read_text(encoding="utf-8"),
        )


def report(data_dir: Path = DATA) -> int:
    """Print the coverage counts and the guard result."""
    classes = g.load_classes(data_dir)
    coverage = g.load_coverage(data_dir)
    ready = g.catalogue_ready_variants(g.load_catalogue(data_dir))
    errors = g.coverage_errors(classes, coverage, ready)

    rows = _entries(coverage)
    counts: Counter[str] = Counter()
    for row in rows:
        state = row.get("state")
        if isinstance(state, str):
            counts[state] += 1
    print(f"coverage: {len(rows)} tokens")
    for state in g.COVERAGE_STATES:
        print(f"  {state}: {counts.get(state, 0)}")
    if errors:
        print("coverage guard: FAIL")
        for error in errors:
            print(f"  {error}")
        return 1
    print("coverage guard: PASS")
    return 0


if __name__ == "__main__":
    if "--report" in sys.argv:
        sys.exit(report())
    _ = unittest.main()
