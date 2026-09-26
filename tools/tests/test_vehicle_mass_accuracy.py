#!/usr/bin/env python3
"""Contract and safety tests for the vehicle mass accuracy campaign tool.

The campaign tool is read-only against the repository. These tests pin the
four strict JSON contracts, the protected-file manifest, the self-check and
the O_NOFOLLOW safe-write guard. Every write goes to a private temporary
directory.

Run: python3 -m unittest tools.tests.test_vehicle_mass_accuracy -v
"""

from __future__ import annotations

import contextlib
import errno
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import validate_vehicle_mass_accuracy as tool  # noqa: E402
from tools.validation import vehicle_catalogue as vehicle_catalogue  # noqa: E402


def _metric() -> dict[str, object]:
    return {
        "n": 46,
        "coverage": 1.0,
        "mdape": 0.1402,
        "width_ratio_median": 2.9,
        "interval_distance_median": 0.0,
        "bias_median": 0.01,
    }


def _probe() -> dict[str, object]:
    return {
        "schema": tool.PROBE_SCHEMA,
        "class": "B_MRAP_01_F",
        "type_of": "B_MRAP_01_F",
        "spawned": True,
        "failure": "",
        "bounding_box_real": [
            [-1.49355, -4.71046, -2.14563],
            [1.49355, 4.71046, 2.14563],
            8.08086,
        ],
        "extents_m": {"length": 11.0, "width": 6.0, "height": 2.0},
        "wheel_geometry": {
            "wheel_count": 4,
            "track_count": 0,
            "wheel_hit_point_names": ["wheel_1_1"],
            "track_hit_point_names": [],
        },
        "readable_material_class": "metal",
        "sourced_match_empty": True,
        "model_interval_kg": [6000.0, 9000.0],
        "method": "geometry_material",
        "confidence": 0.5,
        "assumption_mask": 1,
        "assumption_bits": ["geometry_box"],
        "get_mass": 8306.63,
        "engine_power": 276,
        "status": "estimated",
        "engine_relative_only": True,
    }


def _mapping() -> dict[str, object]:
    return {
        "schema": tool.MAPPING_SCHEMA,
        "entries": [
            {
                "catalogue_id": "fixture_entry",
                "class_key": "wheeled",
                "resolve_path": "token",
                "mapping_basis": "exact",
                "mass_field": "curb_weight_kg",
                "mass_kg": 1500.0,
                "volume_m3": 12.5,
                "evidence": "test fixture",
            }
        ],
        "in_game_classes": [
            {
                "class": "C_Hatchback_01_F",
                "catalogue_id": "fixture_entry",
                "mapping_basis": "analogue",
                "evidence": "test fixture",
            }
        ],
    }


def _holdout() -> dict[str, object]:
    metric = _metric()
    return {
        "schema": tool.HOLDOUT_SCHEMA,
        "method": "leave_one_out",
        "aggregate": dict(metric),
        "by_class_key": {"wheeled": dict(metric)},
        "by_mapping_basis": {"exact": dict(metric)},
        "in_sample": {"n": 46, "coverage": 1.0, "mdape": 0.1402},
        "overfit_gap_mdape": 0.0,
        "thresholds": {
            "n_min": 30,
            "coverage_min": 0.80,
            "mdape_max": 0.35,
            "width_max": 6.0,
        },
        "failures": [],
    }


def _ablation() -> dict[str, object]:
    return {
        "schema": tool.ABLATION_SCHEMA,
        "arm_a": {
            "name": tool.ARM_A_NAME,
            "n": 6,
            "coverage": 0.5,
            "mdape": 0.2,
            "width_ratio_median": 3.0,
        },
        "arm_b": {
            "name": tool.ARM_B_NAME,
            "n": 6,
            "coverage": 0.5,
            "mdape": 0.2,
            "width_ratio_median": 3.0,
            "evaluable": False,
        },
        "corpus_note": "the sourced corpus holds no material class field",
        "engine_probe_note": "engine-relative only, not real-world accuracy",
    }


class _TempCase(unittest.TestCase):
    """A test case with a private temporary root."""

    root: Path = Path()

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def write_json(self, name: str, payload: object) -> Path:
        path = self.root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path


class ProbeContractTest(_TempCase):
    def test_valid_record_has_no_errors(self) -> None:
        self.assertEqual(tool.probe_errors(_probe()), [])

    def test_round_trip_through_loader(self) -> None:
        path = self.write_json("probe.json", _probe())
        loaded = tool.load_probe_record(path)
        self.assertEqual(loaded["schema"], tool.PROBE_SCHEMA)

    def test_schema_mismatch_rejected(self) -> None:
        record = _probe()
        record["schema"] = "aee.vehicle.mass_accuracy.probe/2"
        self.assertTrue(tool.probe_errors(record))

    def test_missing_key_rejected(self) -> None:
        record = _probe()
        del record["status"]
        self.assertTrue(tool.probe_errors(record))

    def test_unexpected_key_rejected(self) -> None:
        record = _probe()
        record["unexpected_field"] = 1
        errors = tool.probe_errors(record)
        self.assertTrue(any("unexpected key" in error for error in errors))

    def test_wrong_type_rejected(self) -> None:
        record = _probe()
        record["get_mass"] = "8306.63"
        self.assertTrue(tool.probe_errors(record))

    def test_engine_relative_flag_required(self) -> None:
        record = _probe()
        record["engine_relative_only"] = False
        self.assertTrue(tool.probe_errors(record))

    def test_failed_spawn_requires_failure_text(self) -> None:
        record = _probe()
        record["spawned"] = False
        record["failure"] = ""
        self.assertTrue(tool.probe_errors(record))

    def test_non_object_rejected(self) -> None:
        self.assertTrue(tool.probe_errors([1, 2, 3]))


class MappingContractTest(_TempCase):
    def test_valid_document_has_no_errors(self) -> None:
        self.assertEqual(tool.mapping_errors(_mapping()), [])

    def test_round_trip_through_loader(self) -> None:
        path = self.write_json("mapping.json", _mapping())
        loaded = tool.load_mapping(path)
        self.assertEqual(loaded["schema"], tool.MAPPING_SCHEMA)

    def test_invalid_resolve_path_rejected(self) -> None:
        document = _mapping()
        entries = document["entries"]
        if isinstance(entries, list) and entries and isinstance(entries[0], dict):
            entries[0]["resolve_path"] = "guess"
        errors = tool.mapping_errors(document)
        self.assertTrue(any("resolve_path" in error for error in errors))

    def test_invalid_mapping_basis_rejected(self) -> None:
        document = _mapping()
        entries = document["entries"]
        if isinstance(entries, list) and entries and isinstance(entries[0], dict):
            entries[0]["mapping_basis"] = "analyse"
        errors = tool.mapping_errors(document)
        self.assertTrue(any("mapping_basis" in error for error in errors))

    def test_missing_entry_key_rejected(self) -> None:
        document = _mapping()
        entries = document["entries"]
        if isinstance(entries, list) and entries and isinstance(entries[0], dict):
            del entries[0]["evidence"]
        self.assertTrue(tool.mapping_errors(document))

    def test_non_object_entry_rejected(self) -> None:
        document = _mapping()
        document["entries"] = [1, 2]
        self.assertTrue(tool.mapping_errors(document))


class HoldoutContractTest(_TempCase):
    def test_valid_document_has_no_errors(self) -> None:
        self.assertEqual(tool.holdout_errors(_holdout()), [])

    def test_round_trip_through_loader(self) -> None:
        path = self.write_json("holdout.json", _holdout())
        loaded = tool.load_holdout(path)
        self.assertEqual(loaded["schema"], tool.HOLDOUT_SCHEMA)

    def test_schema_mismatch_rejected(self) -> None:
        document = _holdout()
        document["schema"] = "aee.vehicle.mass_accuracy.holdout/2"
        self.assertTrue(tool.holdout_errors(document))

    def test_invalid_method_rejected(self) -> None:
        document = _holdout()
        document["method"] = "in_sample"
        errors = tool.holdout_errors(document)
        self.assertTrue(any("method" in error for error in errors))

    def test_missing_key_rejected(self) -> None:
        document = _holdout()
        del document["failures"]
        self.assertTrue(tool.holdout_errors(document))

    def test_unexpected_key_rejected(self) -> None:
        document = _holdout()
        document["extra"] = 1
        errors = tool.holdout_errors(document)
        self.assertTrue(any("unexpected key" in error for error in errors))

    def test_non_integer_n_min_rejected(self) -> None:
        document = _holdout()
        thresholds = document["thresholds"]
        self.assertIsInstance(thresholds, dict)
        if isinstance(thresholds, dict):
            thresholds["n_min"] = 30.5
        errors = tool.holdout_errors(document)
        self.assertTrue(any("n_min" in error for error in errors))
        self.assertTrue(any("integer" in error for error in errors))

    def test_integer_n_min_accepted(self) -> None:
        document = _holdout()
        thresholds = document["thresholds"]
        self.assertIsInstance(thresholds, dict)
        if isinstance(thresholds, dict):
            thresholds["n_min"] = 30
        self.assertEqual(tool.holdout_errors(document), [])

    def test_aggregate_wrong_type_rejected(self) -> None:
        document = _holdout()
        aggregate = document["aggregate"]
        self.assertIsInstance(aggregate, dict)
        if isinstance(aggregate, dict):
            aggregate["coverage"] = "high"
        self.assertTrue(tool.holdout_errors(document))


class AblationContractTest(_TempCase):
    def test_valid_document_has_no_errors(self) -> None:
        self.assertEqual(tool.ablation_errors(_ablation()), [])

    def test_round_trip_through_loader(self) -> None:
        path = self.write_json("ablation.json", _ablation())
        loaded = tool.load_ablation(path)
        self.assertEqual(loaded["schema"], tool.ABLATION_SCHEMA)

    def test_schema_mismatch_rejected(self) -> None:
        document = _ablation()
        document["schema"] = "aee.vehicle.mass_accuracy.ablation/2"
        self.assertTrue(tool.ablation_errors(document))

    def test_wrong_arm_name_rejected(self) -> None:
        document = _ablation()
        arm_a = document["arm_a"]
        if isinstance(arm_a, dict):
            arm_a["name"] = "other_arm"
        errors = tool.ablation_errors(document)
        self.assertTrue(any("arm_a.name" in error for error in errors))

    def test_missing_evaluable_rejected(self) -> None:
        document = _ablation()
        arm_b = document["arm_b"]
        if isinstance(arm_b, dict):
            del arm_b["evaluable"]
        self.assertTrue(tool.ablation_errors(document))

    def test_empty_note_rejected(self) -> None:
        document = _ablation()
        document["corpus_note"] = ""
        self.assertTrue(tool.ablation_errors(document))


class MalformedInputTest(_TempCase):
    def test_malformed_json_raises(self) -> None:
        path = self.root / "bad.json"
        path.write_text("{ not json", encoding="utf-8")
        with self.assertRaises(tool.ContractError) as context:
            tool.load_probe_record(path)
        self.assertIn("malformed JSON", str(context.exception))

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(tool.ContractError) as context:
            tool.load_holdout(self.root / "absent.json")
        self.assertIn("cannot read", str(context.exception))

    def test_non_object_document_raises(self) -> None:
        path = self.write_json("list.json", [1, 2, 3])
        with self.assertRaises(tool.ContractError):
            tool.load_ablation(path)

    def test_unexpected_key_raises_on_load(self) -> None:
        record = _probe()
        record["extra"] = 1
        path = self.write_json("extra.json", record)
        with self.assertRaises(tool.ContractError) as context:
            tool.load_probe_record(path)
        self.assertIn("unexpected key", str(context.exception))


class ManifestTest(_TempCase):
    def _fake_root(self, missing: str | None = None) -> Path:
        fake = self.root / "fake-root"
        for relative in tool.PROTECTED_FILES:
            if relative == missing:
                continue
            path = fake / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(relative, encoding="utf-8")
        catalogue = fake / tool.CATALOGUE_DIR
        catalogue.mkdir(parents=True, exist_ok=True)
        for name in ("b.json", "a.json"):
            (catalogue / name).write_text(name, encoding="utf-8")
        return fake

    def test_manifest_hashes_every_protected_file(self) -> None:
        fake = self._fake_root()
        manifest = tool.build_manifest(fake)
        expected = set(tool.PROTECTED_FILES) | {
            f"{tool.CATALOGUE_DIR}/a.json",
            f"{tool.CATALOGUE_DIR}/b.json",
        }
        self.assertEqual(set(manifest), expected)
        for relative, digest in manifest.items():
            self.assertEqual(digest, tool.sha256_file(fake / relative))

    def test_missing_protected_file_raises(self) -> None:
        fake = self._fake_root(missing="Makefile")
        with self.assertRaises(OSError):
            tool.build_manifest(fake)

    def test_protected_path_detection(self) -> None:
        self.assertTrue(
            tool._is_protected_path(  # noqa: SLF001
                self.root / "data/vehicle/mass_model.json", self.root
            )
        )
        self.assertTrue(
            tool._is_protected_path(  # noqa: SLF001
                self.root / f"{tool.CATALOGUE_DIR}/new.json", self.root
            )
        )
        self.assertFalse(
            tool._is_protected_path(  # noqa: SLF001
                self.root / "data/vehicle/other.json", self.root
            )
        )

    def test_write_manifest_round_trips(self) -> None:
        fake = self._fake_root()
        out = self.root / "manifest.json"
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            tool.write_manifest(out, root=fake)
        loaded = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(loaded, tool.build_manifest(fake))

    def test_write_manifest_refuses_protected_target(self) -> None:
        fake = self._fake_root()
        target = fake / "data/vehicle/mass_model.json"
        with self.assertRaises(OSError) as context:
            tool.write_manifest(target, root=fake)
        self.assertEqual(context.exception.errno, errno.EPERM)


class SafeWriteTest(_TempCase):
    def test_writes_a_real_file(self) -> None:
        path = self.root / "out.txt"
        tool._safe_write(path, "original", root=self.root)  # noqa: SLF001
        self.assertEqual(path.read_text(encoding="utf-8"), "original")

    def test_refuses_symlink_target(self) -> None:
        target = self.root / "target.txt"
        tool._safe_write(target, "original", root=self.root)  # noqa: SLF001
        link = self.root / "link.txt"
        link.symlink_to(target)
        with self.assertRaises(OSError) as context:
            tool._safe_write(link, "hacked", root=self.root)  # noqa: SLF001
        self.assertEqual(context.exception.errno, errno.ELOOP)
        self.assertEqual(target.read_bytes(), b"original")

    def test_refuses_symlink_parent(self) -> None:
        real_dir = self.root / "real-dir"
        real_dir.mkdir()
        link_dir = self.root / "link-dir"
        link_dir.symlink_to(real_dir)
        with self.assertRaises(OSError) as context:
            tool._safe_write(  # noqa: SLF001
                link_dir / "child.txt", "hacked", root=self.root
            )
        self.assertEqual(context.exception.errno, errno.ELOOP)
        self.assertFalse((real_dir / "child.txt").exists())

    def test_refuses_symlink_grandparent(self) -> None:
        real_grandparent = self.root / "real-grandparent"
        (real_grandparent / "child").mkdir(parents=True)
        link_grandparent = self.root / "link-grandparent"
        link_grandparent.symlink_to(real_grandparent)
        with self.assertRaises(OSError) as context:
            tool._safe_write(  # noqa: SLF001
                link_grandparent / "child" / "grandchild.txt",
                "hacked",
                root=self.root,
            )
        self.assertEqual(context.exception.errno, errno.ELOOP)
        self.assertFalse((real_grandparent / "child" / "grandchild.txt").exists())

    def test_refuses_protected_path(self) -> None:
        protected = self.root / "data/vehicle/mass_model.json"
        with self.assertRaises(OSError) as context:
            tool._safe_write(protected, "hacked", root=self.root)  # noqa: SLF001
        self.assertEqual(context.exception.errno, errno.EPERM)
        self.assertFalse(protected.exists())

    def test_refuses_catalogue_path(self) -> None:
        catalogue = self.root / tool.CATALOGUE_DIR / "new.json"
        with self.assertRaises(OSError) as context:
            tool._safe_write(catalogue, "hacked", root=self.root)  # noqa: SLF001
        self.assertEqual(context.exception.errno, errno.EPERM)


class SelfCheckTest(unittest.TestCase):
    def test_self_check_passes(self) -> None:
        self.assertEqual(tool.self_check(), [])


class CommandLineTest(unittest.TestCase):
    def test_self_check_mode_exits_zero(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = tool.main(["--self-check"])
        self.assertEqual(code, 0)
        self.assertIn("PASS", buffer.getvalue())

    def test_manifest_mode_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "manifest.json"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = tool.main(["--manifest", str(out)])
            self.assertEqual(code, 0)
            self.assertTrue(out.is_file())

    def test_unknown_argument_exits(self) -> None:
        with self.assertRaises(SystemExit):
            _ = tool.main(["--nope"])

    def test_no_mode_exits(self) -> None:
        with self.assertRaises(SystemExit):
            _ = tool.main([])


def _held(value: float, unit: str) -> dict[str, object]:
    return {
        "value": value,
        "unit": unit,
        "source": "test fixture",
        "locator": "test fixture",
        "state": "test fixture",
        "grade": "documented",
    }


def _entry(
    catalogue_id: str,
    *,
    mass_kg: float = 2000.0,
    length_mm: float = 4000.0,
    width_mm: float = 2000.0,
    height_mm: float = 1500.0,
    vehicle_type: str = "wheeled",
    class_token: str = "",
    model: str = "",
    variant_id: str = "",
) -> vehicle_catalogue.CatalogueEntry:
    values: dict[str, object] = {
        "length_mm": _held(length_mm, "mm"),
        "width_mm": _held(width_mm, "mm"),
        "height_mm": _held(height_mm, "mm"),
        "curb_weight_kg": _held(mass_kg, "kg"),
    }
    return vehicle_catalogue.CatalogueEntry(
        catalogue_id=catalogue_id,
        canonical_name=catalogue_id,
        maker="",
        model=model,
        variant="",
        variant_id=variant_id or catalogue_id,
        vehicle_type=vehicle_type,
        class_token=class_token,
        country="",
        era="",
        aliases=(),
        keywords=(),
        runtime_ready=True,
        values=values,
        source_file="test fixture",
    )


def _synthetic_model() -> dict[str, object]:
    return {
        "schema": "aee.vehicle.mass_model/1",
        "material_density": {
            "metal": {"low": 7100, "high": 7850, "source": "x", "locator": "y"},
            "wood": {"low": 350, "high": 1100, "source": "x", "locator": "y"},
            "ground": {"low": 860, "high": 1450, "source": "x", "locator": "y"},
        },
        "mass_classes": [
            {
                "key": "wheeled",
                "match": "vehicle_type",
                "vehicle_type": "wheeled",
                "density_class": "metal",
                "fill_low": 0.01,
                "fill_high": 0.05,
                "n": 0,
            },
            {
                "key": "default",
                "match": "default",
                "vehicle_type": "",
                "density_class": "metal",
                "fill_low": 0.0,
                "fill_high": 0.0,
                "n": 0,
            },
        ],
        "geometry_bands": {
            "min_extent_m": 0.5,
            "max_extent_m": 20.0,
            "max_width_ratio": 6.0,
        },
        "calibration": {
            "approved": False,
            "n_entries": 0,
            "mdape": 0.0,
            "fraction_in_band": 0.0,
        },
    }


def _probe_record(
    *, class_name: str = "B_MRAP_01_F", **overrides: object
) -> dict[str, object]:
    record: dict[str, object] = {
        "schema": tool.PROBE_SCHEMA,
        "class": class_name,
        "type_of": class_name,
        "spawned": True,
        "failure": "",
        "bounding_box_real": [[-1.0, -2.0, -1.0], [1.0, 2.0, 1.0], 4.0],
        "extents_m": {"length": 4.0, "width": 2.0, "height": 1.5},
        "wheel_geometry": {
            "wheel_count": 4,
            "track_count": 0,
            "wheel_hit_point_names": ["wheel_1_1"],
            "track_hit_point_names": [],
        },
        "readable_material_class": "metal",
        "sourced_match_empty": True,
        "model_interval_kg": [1000.0, 2000.0],
        "method": "geometry_material",
        "confidence": 0.5,
        "assumption_mask": 1,
        "assumption_bits": ["geometry_box"],
        "get_mass": 1500.0,
        "engine_power": 276.0,
        "status": "estimated",
        "engine_relative_only": True,
    }
    record.update(overrides)
    return record


def _log_line(record: dict[str, object], *, quoted: bool = True) -> str:
    payload = json.dumps(record, sort_keys=True)
    if quoted:
        return '12:00:00 "' + tool.PROBE_MARKER + " " + payload + '"'
    return "12:00:00 " + tool.PROBE_MARKER + " " + payload


def _mapping_value(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AssertionError(f"expected an object, got {type(value).__name__}")
    return {str(key): item for key, item in value.items()}


def _num(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AssertionError(f"expected a number, got {type(value).__name__}")
    return float(value)


class HoldoutEngineTest(_TempCase):
    def test_all_three_methods_are_produced(self) -> None:
        model = _synthetic_model()
        entries = [_entry(f"v{index}") for index in range(6)]
        for method in tool.HOLDOUT_METHODS:
            document = tool.holdout_document(model, entries, None, method)
            self.assertEqual(document["method"], method)
            self.assertEqual(document["schema"], tool.HOLDOUT_SCHEMA)
            self.assertEqual(tool.holdout_errors(document), [])

    def test_leave_one_out_is_leak_free_on_an_outlier(self) -> None:
        model = _synthetic_model()
        entries = [_entry(f"v{index}") for index in range(5)]
        entries.append(_entry("outlier", mass_kg=200000.0))
        rows = tool.leave_one_out(model, entries, {})
        by_id = {str(row["catalogue_id"]): row for row in rows}
        self.assertFalse(by_id["outlier"]["covers"])
        for index in range(5):
            self.assertTrue(by_id[f"v{index}"]["covers"])
        document = tool.holdout_document(model, entries, None, "leave_one_out")
        self.assertLess(_num(_mapping_value(document["aggregate"])["coverage"]), 1.0)

    def test_impossible_holdout_mass_has_no_coverage(self) -> None:
        model = _synthetic_model()
        entries = [_entry("solo", mass_kg=100000.0)]
        document = tool.holdout_document(model, entries, None, "leave_one_out")
        self.assertEqual(_mapping_value(document["aggregate"])["n"], 1)
        self.assertEqual(_mapping_value(document["aggregate"])["coverage"], 0.0)
        self.assertTrue(document["failures"])

    def test_repeated_output_is_deterministic(self) -> None:
        model = _synthetic_model()
        entries = [_entry(f"v{index}") for index in range(7)]
        first = tool.holdout_document(model, entries, None, "grouped_leave_one_out")
        second = tool.holdout_document(model, entries, None, "grouped_leave_one_out")
        self.assertEqual(first, second)

    def test_mapping_ledger_labels_the_split(self) -> None:
        model = _synthetic_model()
        entries = [_entry(f"v{index}") for index in range(5)]
        mapping = {
            "schema": tool.MAPPING_SCHEMA,
            "entries": [
                {
                    "catalogue_id": entry.catalogue_id,
                    "class_key": "wheeled",
                    "resolve_path": "vehicle_type",
                    "mapping_basis": "analogue",
                    "mass_field": "curb_weight_kg",
                    "mass_kg": 2000.0,
                    "volume_m3": 12.0,
                    "evidence": "test fixture",
                }
                for entry in entries
            ],
            "in_game_classes": [],
        }
        document = tool.holdout_document(model, entries, mapping, "leave_one_out")
        self.assertEqual(
            set(_mapping_value(document["by_mapping_basis"])), {"analogue"}
        )

    def test_default_basis_is_class_only_without_a_ledger(self) -> None:
        model = _synthetic_model()
        entries = [_entry(f"v{index}") for index in range(5)]
        document = tool.holdout_document(model, entries, None, "leave_one_out")
        self.assertEqual(
            set(_mapping_value(document["by_mapping_basis"])), {"class_only"}
        )

    def test_family_key_strips_variant_tokens(self) -> None:
        first = _entry("a", model="", variant_id="honda_civic_6gen_coupe")
        second = _entry("b", model="", variant_id="honda_civic_6gen_sedan")
        self.assertEqual(tool.family_key(first), tool.family_key(second))

    def test_family_key_prefers_the_model(self) -> None:
        first = _entry("a", model="Civic", variant_id="civic_boost")
        same = _entry("b", model="Civic", variant_id="civic_si")
        other = _entry("c", model="Accord", variant_id="accord_lx")
        self.assertEqual(tool.family_key(first), tool.family_key(same))
        self.assertNotEqual(tool.family_key(first), tool.family_key(other))


class AblationEngineTest(_TempCase):
    def test_empty_probe_marks_arm_b_not_evaluable(self) -> None:
        document = tool.ablation_document(_synthetic_model(), [], [])
        self.assertFalse(_mapping_value(document["arm_b"])["evaluable"])
        self.assertEqual(tool.ablation_errors(document), [])

    def test_material_probe_widens_arm_b(self) -> None:
        records = [
            _probe_record(readable_material_class="metal"),
            _probe_record(
                class_name="B_Truck_01_transport_F", readable_material_class="wood"
            ),
        ]
        document = tool.ablation_document(_synthetic_model(), [], records)
        self.assertTrue(_mapping_value(document["arm_b"])["evaluable"])
        self.assertGreater(
            _num(_mapping_value(document["arm_b"])["width_ratio_median"]),
            _num(_mapping_value(document["arm_a"])["width_ratio_median"]),
        )
        self.assertEqual(tool.ablation_errors(document), [])

    def test_ground_material_is_not_evaluable(self) -> None:
        records = [_probe_record(readable_material_class="ground")]
        document = tool.ablation_document(_synthetic_model(), [], records)
        self.assertFalse(_mapping_value(document["arm_b"])["evaluable"])
        self.assertEqual(_mapping_value(document["arm_b"])["n"], 0)

    def test_engine_probe_note_labels_engine_relative(self) -> None:
        records = [_probe_record(readable_material_class="wood")]
        document = tool.ablation_document(_synthetic_model(), [], records)
        note = str(document["engine_probe_note"])
        self.assertIn("engine_relative_only", note)
        self.assertIn("not real-world accuracy", note)

    def test_corpus_arms_record_the_material_gap(self) -> None:
        model = _synthetic_model()
        entries = [_entry(f"v{index}") for index in range(6)]
        document = tool.ablation_document(model, entries, None)
        self.assertEqual(_mapping_value(document["arm_a"])["n"], 6)
        self.assertFalse(_mapping_value(document["arm_b"])["evaluable"])
        self.assertIn("corpus", str(document["corpus_note"]))
        self.assertEqual(tool.ablation_errors(document), [])

    def test_zero_mass_spawned_record_is_not_scored(self) -> None:
        record = _probe_record(get_mass=0)
        document = tool.ablation_document(_synthetic_model(), [], [record])
        self.assertEqual(_mapping_value(document["arm_a"])["n"], 0)
        self.assertFalse(_mapping_value(document["arm_b"])["evaluable"])
        self.assertEqual(tool.ablation_errors(document), [])

    def test_failed_spawn_record_is_ignored_by_the_arms(self) -> None:
        failed = _probe_record(
            class_name=tool.MOTORCYCLE_CLASS,
            spawned=False,
            failure="cannot create",
        )
        document = tool.ablation_document(_synthetic_model(), [], [failed])
        self.assertEqual(_mapping_value(document["arm_a"])["n"], 0)
        self.assertFalse(_mapping_value(document["arm_b"])["evaluable"])


class IngestEngineTest(_TempCase):
    def _power_probe(self, record: dict[str, object]) -> Path:
        samples = [
            {
                "class": record["class"],
                "engine_power": record["engine_power"],
                "bounding_box_real": record["bounding_box_real"],
            }
        ]
        path = self.root / "power-probe.json"
        path.write_text(
            json.dumps({"schema": "aee.vehicle.power_probe/1", "samples": samples}),
            encoding="utf-8",
        )
        return path

    def _valid_log(self) -> tuple[str, dict[str, object], dict[str, object]]:
        good = _probe_record()
        failed = _probe_record(
            class_name=tool.MOTORCYCLE_CLASS,
            type_of=tool.MOTORCYCLE_CLASS,
            spawned=False,
            failure="Cannot create non-ai vehicle",
            bounding_box_real=[[0, 0, 0], [0, 0, 0], 0],
            engine_power=0,
            get_mass=0,
            readable_material_class="none",
            status="unavailable",
        )
        text = "\n".join([_log_line(good), _log_line(failed)]) + "\n"
        return text, good, failed

    def test_valid_log_ingests_every_record(self) -> None:
        text, good, _ = self._valid_log()
        records, spawned, failed, failures = tool.ingest_log(
            text, self._power_probe(good)
        )
        self.assertEqual(failures, [])
        self.assertEqual(len(records), 2)
        self.assertEqual(spawned, 1)
        self.assertEqual(failed, 1)

    def test_failed_spawn_record_is_retained(self) -> None:
        text, _, failed_record = self._valid_log()
        records, _, _, failures = tool.ingest_log(
            text, self._power_probe(_probe_record())
        )
        self.assertEqual(failures, [])
        self.assertIn(failed_record, records)

    def test_malformed_json_is_a_failure(self) -> None:
        text = "12:00:00 " + tool.PROBE_MARKER + " { not json\n"
        records, _, _, failures = tool.ingest_log(
            text, self._power_probe(_probe_record())
        )
        self.assertEqual(records, [])
        self.assertTrue(any("malformed JSON" in failure for failure in failures))

    def test_missing_engine_relative_flag_is_a_failure(self) -> None:
        bad = _probe_record()
        del bad["engine_relative_only"]
        _, _, _, failures = tool.ingest_log(
            _log_line(bad) + "\n", self._power_probe(_probe_record())
        )
        self.assertTrue(any("engine_relative_only" in failure for failure in failures))

    def test_non_number_engine_power_is_a_failure(self) -> None:
        bad = _probe_record(engine_power="276")
        _, _, _, failures = tool.ingest_log(
            _log_line(bad) + "\n", self._power_probe(_probe_record())
        )
        self.assertTrue(any("engine_power" in failure for failure in failures))

    def test_missing_failed_record_is_a_failure(self) -> None:
        good = _probe_record()
        _, _, _, failures = tool.ingest_log(
            _log_line(good) + "\n", self._power_probe(good)
        )
        self.assertTrue(any("failed" in failure for failure in failures))

    def test_engine_power_mismatch_is_a_failure(self) -> None:
        good = _probe_record()
        path = self._power_probe(good)
        reference = json.loads(path.read_text(encoding="utf-8"))
        reference["samples"][0]["engine_power"] = 999.0
        path.write_text(json.dumps(reference), encoding="utf-8")
        _, _, _, failures = tool.ingest_log(_log_line(good) + "\n", path)
        self.assertTrue(any("engine_power" in failure for failure in failures))

    def test_bounding_box_mismatch_is_a_failure(self) -> None:
        good = _probe_record()
        path = self._power_probe(good)
        reference = json.loads(path.read_text(encoding="utf-8"))
        reference["samples"][0]["bounding_box_real"] = [[9, 9, 9], [9, 9, 9], 9]
        path.write_text(json.dumps(reference), encoding="utf-8")
        _, _, _, failures = tool.ingest_log(_log_line(good) + "\n", path)
        self.assertTrue(any("bounding_box_real" in failure for failure in failures))

    def test_non_marker_lines_are_ignored(self) -> None:
        good = _probe_record()
        failed = _probe_record(
            class_name=tool.MOTORCYCLE_CLASS, spawned=False, failure="x"
        )
        text = "\n".join(
            ["unrelated line", _log_line(good), "another line", _log_line(failed)]
        )
        records, _, _, failures = tool.ingest_log(text + "\n", self._power_probe(good))
        self.assertEqual(failures, [])
        self.assertEqual(len(records), 2)

    def test_unquoted_payload_is_parsed(self) -> None:
        good = _probe_record()
        text = _log_line(good, quoted=False) + "\n"
        records, _, _, _ = tool.ingest_log(text, self._power_probe(good))
        self.assertEqual(len(records), 1)

    def test_write_goes_only_to_the_named_path(self) -> None:
        text, good, _ = self._valid_log()
        log = self.root / "probe.log"
        log.write_text(text, encoding="utf-8")
        out = self.root / "engine-probe.json"
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code, failures = tool.write_ingest(log, out, self._power_probe(good))
        self.assertEqual(code, 0)
        self.assertEqual(failures, [])
        self.assertEqual(len(tool.load_probe_array(out)), 2)

    def test_write_refuses_to_follow_a_symlink_target(self) -> None:
        text, good, _ = self._valid_log()
        log = self.root / "probe.log"
        log.write_text(text, encoding="utf-8")
        target = self.root / "real.txt"
        target.write_text("original", encoding="utf-8")
        link = self.root / "engine-probe.json"
        link.symlink_to(target)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code, _ = tool.write_ingest(log, link, self._power_probe(good))
        self.assertEqual(code, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), "original")
        self.assertFalse(link.is_symlink())


class CampaignCommandLineTest(unittest.TestCase):
    def test_holdout_mode_exits_zero_on_the_repository_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "holdout.json"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = tool.main(["--holdout", "--out", str(out)])
            self.assertEqual(code, 0)
            document = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(document["schema"], tool.HOLDOUT_SCHEMA)

    def test_ablation_mode_exits_zero_on_the_repository_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "ablation.json"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = tool.main(["--ablation", "--out", str(out)])
            self.assertEqual(code, 0)
            document = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(tool.ablation_errors(document), [])

    def test_unknown_method_exits(self) -> None:
        with self.assertRaises(SystemExit):
            _ = tool.holdout_document(_synthetic_model(), [], None, "in_sample")


if __name__ == "__main__":
    _ = unittest.main()
