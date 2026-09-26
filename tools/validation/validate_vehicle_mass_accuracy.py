#!/usr/bin/env python3
"""Read-only accuracy campaign for the modelled vehicle mass estimator.

This tool measures the committed vehicle mass estimator out of sample and
against the engine. It changes no model, threshold, catalogue or runtime
file. It is read-only against the repository. The only write it makes is a
campaign artifact under an output path the caller names, and the manifest
guard refuses to write any protected file.

The four JSON contracts are pinned here. Every loader is strict: it rejects
a missing key, an unexpected key, a wrong type, an invalid enum value, a
non-object record and malformed JSON. The process exits non-zero on a
violation.

Contract ``aee.vehicle.mass_accuracy.probe/1`` (one object per probe
record)::

    {
      "schema": "aee.vehicle.mass_accuracy.probe/1",
      "class": str, "type_of": str, "spawned": bool, "failure": str,
      "bounding_box_real": [number or [number, ...], ...],
      "extents_m": {"length": number, "width": number, "height": number},
      "wheel_geometry": {
        "wheel_count": int, "track_count": int,
        "wheel_hit_point_names": [str, ...],
        "track_hit_point_names": [str, ...]
      },
      "readable_material_class": str,
      "sourced_match_empty": bool,
      "model_interval_kg": [number, number],
      "method": str, "confidence": number,
      "assumption_mask": int, "assumption_bits": [str, ...],
      "get_mass": number, "engine_power": number,
      "status": str, "engine_relative_only": true
    }

A record with ``spawned`` false must hold the failure text. The flag
``engine_relative_only`` must be exactly true: no probe value is a
real-world mass or power.

Contract ``aee.vehicle.mass_accuracy.mapping/1``::

    {
      "schema": "aee.vehicle.mass_accuracy.mapping/1",
      "entries": [{
        "catalogue_id": str, "class_key": str,
        "resolve_path": "token" | "vehicle_type" | "default",
        "mapping_basis": "exact" | "analogue" | "class_only",
        "mass_field": str, "mass_kg": number, "volume_m3": number,
        "evidence": str
      }],
      "in_game_classes": [{
        "class": str, "catalogue_id": str,
        "mapping_basis": "exact" | "analogue" | "class_only",
        "evidence": str
      }]
    }

Contract ``aee.vehicle.mass_accuracy.holdout/1``::

    {
      "schema": "aee.vehicle.mass_accuracy.holdout/1",
      "method": "leave_one_out" | "grouped_leave_one_out" | "stratified_split",
      "aggregate": {metric object},
      "by_class_key": {str: metric object},
      "by_mapping_basis": {str: metric object},
      "in_sample": {"n": int, "coverage": number, "mdape": number},
      "overfit_gap_mdape": number,
      "thresholds": {"n_min": int, "coverage_min": number,
                     "mdape_max": number, "width_max": number},
      "failures": [str, ...]
    }

A metric object holds ``n``, ``coverage``, ``mdape``,
``width_ratio_median``, ``interval_distance_median`` and ``bias_median``.

Contract ``aee.vehicle.mass_accuracy.ablation/1``::

    {
      "schema": "aee.vehicle.mass_accuracy.ablation/1",
      "arm_a": {"name": "geometry_class_fill_only", "n": int,
                "coverage": number, "mdape": number,
                "width_ratio_median": number},
      "arm_b": {"name": "readable_material_class", "n": int,
                "coverage": number, "mdape": number,
                "width_ratio_median": number, "evaluable": bool},
      "corpus_note": str, "engine_probe_note": str
    }

Run:  python3 tools/validation/validate_vehicle_mass_accuracy.py --self-check
      python3 tools/validation/validate_vehicle_mass_accuracy.py --manifest PATH
      python3 tools/validation/validate_vehicle_mass_accuracy.py --holdout [--mapping PATH] [--method NAME] [--out PATH]
      python3 tools/validation/validate_vehicle_mass_accuracy.py --ablation [--probe PATH] [--out PATH]
      python3 tools/validation/validate_vehicle_mass_accuracy.py --ingest LOG [--out PATH]
Exit: 0 on success, 1 on a contract violation, a manifest error, a failed
      self-check, a failed holdout, a failed ingest or a cross-check mismatch.
"""

from __future__ import annotations

import copy
import errno
import hashlib
import json
import math
import os
import statistics
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TypeGuard, cast

_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import vehicle_catalogue as catalogue  # noqa: E402
from tools.validation.validate_vehicle_mass_model import (  # noqa: E402
    CALIBRATION_NAME,
    DEFAULT_MAX_WIDTH_RATIO,
    MAX_MDAPE,
    MIN_ENTRIES,
    MIN_FRACTION_IN_BAND,
    ClassMetric,
    Metrics,
    approval_failures,
    calibrate,
    documented_mass,
    entry_volume_m3,
    evaluate,
    load_calibration,
    load_model,
    resolve_mass_class,
    skip_reason,
)

ROOT = _REPO
CATALOGUE_DIR = "data/vehicle/catalogue"
DATA_DIR = ROOT / "data" / "vehicle"
MODEL_PATH = DATA_DIR / "mass_model.json"

PROBE_SCHEMA = "aee.vehicle.mass_accuracy.probe/1"
MAPPING_SCHEMA = "aee.vehicle.mass_accuracy.mapping/1"
HOLDOUT_SCHEMA = "aee.vehicle.mass_accuracy.holdout/1"
ABLATION_SCHEMA = "aee.vehicle.mass_accuracy.ablation/1"

# The protected files named by the campaign plan. The catalogue entry
# expands through PROTECTED_GLOBS at run time, so the manifest records one
# hash per concrete file.
PROTECTED_FILES: tuple[str, ...] = (
    "data/vehicle/mass_model.json",
    "data/vehicle/class_map.json",
    "data/vehicle/classes.json",
    "data/vehicle/coverage.json",
    "data/vehicle/sources.json",
    "addons/mobility/functions/fnc_estimateVehicleMass.sqf",
    "addons/mobility/functions/fnc_estimateVehicleMassCore.sqf",
    "addons/mobility/functions/fnc_getVehicleMassModel.sqf",
    "addons/mobility/functions/fnc_calculateSoilStrength.sqf",
    "tools/run_tests.py",
    "Makefile",
    ".github/workflows/ci.yml",
)
PROTECTED_GLOBS: tuple[str, ...] = ("data/vehicle/catalogue/*.json",)

RESOLVE_PATHS: tuple[str, ...] = ("token", "vehicle_type", "default")
MAPPING_BASES: tuple[str, ...] = ("exact", "analogue", "class_only")
HOLDOUT_METHODS: tuple[str, ...] = (
    "leave_one_out",
    "grouped_leave_one_out",
    "stratified_split",
)
ARM_A_NAME = "geometry_class_fill_only"
ARM_B_NAME = "readable_material_class"

PROBE_KEYS: tuple[str, ...] = (
    "schema",
    "class",
    "type_of",
    "spawned",
    "failure",
    "bounding_box_real",
    "extents_m",
    "wheel_geometry",
    "readable_material_class",
    "sourced_match_empty",
    "model_interval_kg",
    "method",
    "confidence",
    "assumption_mask",
    "assumption_bits",
    "get_mass",
    "engine_power",
    "status",
    "engine_relative_only",
)
MAPPING_KEYS: tuple[str, ...] = ("schema", "entries", "in_game_classes")
MAPPING_ENTRY_KEYS: tuple[str, ...] = (
    "catalogue_id",
    "class_key",
    "resolve_path",
    "mapping_basis",
    "mass_field",
    "mass_kg",
    "volume_m3",
    "evidence",
)
IN_GAME_KEYS: tuple[str, ...] = (
    "class",
    "catalogue_id",
    "mapping_basis",
    "evidence",
)
HOLDOUT_KEYS: tuple[str, ...] = (
    "schema",
    "method",
    "aggregate",
    "by_class_key",
    "by_mapping_basis",
    "in_sample",
    "overfit_gap_mdape",
    "thresholds",
    "failures",
)
METRIC_KEYS: tuple[str, ...] = (
    "n",
    "coverage",
    "mdape",
    "width_ratio_median",
    "interval_distance_median",
    "bias_median",
)
IN_SAMPLE_KEYS: tuple[str, ...] = ("n", "coverage", "mdape")
THRESHOLD_KEYS: tuple[str, ...] = (
    "n_min",
    "coverage_min",
    "mdape_max",
    "width_max",
)
ABLATION_KEYS: tuple[str, ...] = (
    "schema",
    "arm_a",
    "arm_b",
    "corpus_note",
    "engine_probe_note",
)
ARM_KEYS: tuple[str, ...] = ("name", "n", "coverage", "mdape", "width_ratio_median")

USAGE = (
    "usage: validate_vehicle_mass_accuracy.py "
    "[--self-check | --manifest PATH | --holdout | --ablation | --ingest LOG] "
    "[--out PATH] [--mapping PATH] [--probe PATH] [--method NAME]"
)


class ContractError(ValueError):
    """A strict contract violation. The message holds every fault."""

    path: Path
    errors: list[str]

    def __init__(self, path: Path, errors: Sequence[str]) -> None:
        self.path = path
        self.errors = list(errors)
        super().__init__(f"{path}: " + "; ".join(errors))


# --------------------------------------------------------------------------
# Type guards and small checks.
# --------------------------------------------------------------------------


def _is_number(value: object) -> TypeGuard[float | int]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_str(value: object) -> TypeGuard[str]:
    return isinstance(value, str)


def _is_bool(value: object) -> TypeGuard[bool]:
    return isinstance(value, bool)


def _list(value: object) -> list[object] | None:
    if not isinstance(value, list):
        return None
    return list(cast("list[object]", value))


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    raw = cast("dict[object, object]", value)
    return {str(key): item for key, item in raw.items()}


def _check_keys(
    value: Mapping[str, object],
    required: Sequence[str],
    where: str,
    errors: list[str],
) -> None:
    allowed = set(required)
    for key in required:
        if key not in value:
            errors.append(f"{where}: missing key {key!r}")
    for key in sorted(value):
        if key not in allowed:
            errors.append(f"{where}: unexpected key {key!r}")


def _check_str(
    value: object,
    where: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
) -> None:
    if not _is_str(value):
        errors.append(f"{where}: must be a string")
        return
    if not allow_empty and not value:
        errors.append(f"{where}: must not be empty")


def _check_bool(value: object, where: str, errors: list[str]) -> None:
    if not _is_bool(value):
        errors.append(f"{where}: must be true or false")


def _check_int(
    value: object,
    where: str,
    errors: list[str],
    *,
    non_negative: bool = False,
) -> None:
    if not _is_int(value):
        errors.append(f"{where}: must be an integer")
        return
    if non_negative and value < 0:
        errors.append(f"{where}: must not be negative")


def _check_number(
    value: object,
    where: str,
    errors: list[str],
    *,
    positive: bool = False,
    non_negative: bool = False,
) -> None:
    if not _is_number(value):
        errors.append(f"{where}: must be a number")
        return
    if positive and value <= 0:
        errors.append(f"{where}: must be greater than zero")
    if non_negative and value < 0:
        errors.append(f"{where}: must not be negative")


def _check_enum(
    value: object,
    allowed: Sequence[str],
    where: str,
    errors: list[str],
) -> None:
    if not _is_str(value):
        errors.append(f"{where}: must be a string")
    elif value not in allowed:
        errors.append(f"{where}: {value!r} is not one of {', '.join(allowed)}")


def _check_str_list(value: object, where: str, errors: list[str]) -> None:
    items = _list(value)
    if items is None:
        errors.append(f"{where}: must be an array")
        return
    for index, item in enumerate(items):
        if not _is_str(item):
            errors.append(f"{where}[{index}]: must be a string")


# --------------------------------------------------------------------------
# Probe contract.
# --------------------------------------------------------------------------


def _check_extents(value: object, errors: list[str]) -> None:
    where = "probe record.extents_m"
    mapped = _mapping(value)
    if mapped is None:
        errors.append(f"{where}: must be an object")
        return
    _check_keys(mapped, ("length", "width", "height"), where, errors)
    for key in ("length", "width", "height"):
        _check_number(mapped.get(key), f"{where}.{key}", errors, non_negative=True)


def _check_wheel_geometry(value: object, errors: list[str]) -> None:
    where = "probe record.wheel_geometry"
    mapped = _mapping(value)
    if mapped is None:
        errors.append(f"{where}: must be an object")
        return
    _check_keys(
        mapped,
        (
            "wheel_count",
            "track_count",
            "wheel_hit_point_names",
            "track_hit_point_names",
        ),
        where,
        errors,
    )
    _check_int(
        mapped.get("wheel_count"), f"{where}.wheel_count", errors, non_negative=True
    )
    _check_int(
        mapped.get("track_count"), f"{where}.track_count", errors, non_negative=True
    )
    _check_str_list(
        mapped.get("wheel_hit_point_names"),
        f"{where}.wheel_hit_point_names",
        errors,
    )
    _check_str_list(
        mapped.get("track_hit_point_names"),
        f"{where}.track_hit_point_names",
        errors,
    )


def _check_interval(value: object, errors: list[str]) -> None:
    where = "probe record.model_interval_kg"
    items = _list(value)
    if items is None or len(items) != 2:
        errors.append(f"{where}: must be an array of two numbers")
        return
    low, high = items
    if not _is_number(low) or not _is_number(high):
        errors.append(f"{where}: must hold two numbers")
        return
    if low > high:
        errors.append(f"{where}: the low bound must not exceed the high bound")


def _check_bounding_box(value: object, errors: list[str]) -> None:
    where = "probe record.bounding_box_real"
    items = _list(value)
    if not items:
        errors.append(f"{where}: must be a non-empty array")
        return
    for index, item in enumerate(items):
        if _is_number(item):
            continue
        parts = _list(item)
        if parts and all(_is_number(part) for part in parts):
            continue
        errors.append(f"{where}[{index}]: must be a number or an array of numbers")


def probe_errors(record: object) -> list[str]:
    """Return every error in one ``probe/1`` record. An empty list is valid."""
    errors: list[str] = []
    mapped = _mapping(record)
    if mapped is None:
        return ["probe record: must be a JSON object"]
    _check_keys(mapped, PROBE_KEYS, "probe record", errors)
    if mapped.get("schema") != PROBE_SCHEMA:
        errors.append(f"probe record.schema: must be {PROBE_SCHEMA!r}")
    for key in ("class", "type_of", "method", "status", "readable_material_class"):
        _check_str(mapped.get(key), f"probe record.{key}", errors)
    _check_str(mapped.get("failure"), "probe record.failure", errors, allow_empty=True)
    _check_bool(mapped.get("spawned"), "probe record.spawned", errors)
    _check_bool(
        mapped.get("sourced_match_empty"),
        "probe record.sourced_match_empty",
        errors,
    )
    _check_bounding_box(mapped.get("bounding_box_real"), errors)
    if mapped.get("spawned") is False and not mapped.get("failure"):
        errors.append(
            "probe record.failure: must hold the failure text when spawned is false"
        )
    _check_extents(mapped.get("extents_m"), errors)
    _check_wheel_geometry(mapped.get("wheel_geometry"), errors)
    _check_interval(mapped.get("model_interval_kg"), errors)
    _check_number(mapped.get("confidence"), "probe record.confidence", errors)
    _check_int(
        mapped.get("assumption_mask"),
        "probe record.assumption_mask",
        errors,
        non_negative=True,
    )
    _check_str_list(
        mapped.get("assumption_bits"),
        "probe record.assumption_bits",
        errors,
    )
    _check_number(mapped.get("get_mass"), "probe record.get_mass", errors)
    _check_number(mapped.get("engine_power"), "probe record.engine_power", errors)
    if mapped.get("engine_relative_only") is not True:
        errors.append("probe record.engine_relative_only: must be true")
    return errors


# --------------------------------------------------------------------------
# Mapping contract.
# --------------------------------------------------------------------------


def _check_mapping_entry(raw: object, index: int, errors: list[str]) -> None:
    where = f"mapping document.entries[{index}]"
    entry = _mapping(raw)
    if entry is None:
        errors.append(f"{where}: must be an object")
        return
    _check_keys(entry, MAPPING_ENTRY_KEYS, where, errors)
    _check_str(entry.get("catalogue_id"), f"{where}.catalogue_id", errors)
    _check_str(entry.get("class_key"), f"{where}.class_key", errors)
    _check_enum(
        entry.get("resolve_path"), RESOLVE_PATHS, f"{where}.resolve_path", errors
    )
    _check_enum(
        entry.get("mapping_basis"),
        MAPPING_BASES,
        f"{where}.mapping_basis",
        errors,
    )
    _check_str(entry.get("mass_field"), f"{where}.mass_field", errors)
    _check_number(entry.get("mass_kg"), f"{where}.mass_kg", errors, positive=True)
    _check_number(entry.get("volume_m3"), f"{where}.volume_m3", errors, positive=True)
    _check_str(entry.get("evidence"), f"{where}.evidence", errors)


def _check_in_game_class(raw: object, index: int, errors: list[str]) -> None:
    where = f"mapping document.in_game_classes[{index}]"
    entry = _mapping(raw)
    if entry is None:
        errors.append(f"{where}: must be an object")
        return
    _check_keys(entry, IN_GAME_KEYS, where, errors)
    _check_str(entry.get("class"), f"{where}.class", errors)
    _check_str(
        entry.get("catalogue_id"),
        f"{where}.catalogue_id",
        errors,
        allow_empty=True,
    )
    _check_enum(
        entry.get("mapping_basis"),
        MAPPING_BASES,
        f"{where}.mapping_basis",
        errors,
    )
    _check_str(entry.get("evidence"), f"{where}.evidence", errors)


def mapping_errors(document: object) -> list[str]:
    """Return every error in a ``mapping/1`` document. Empty is valid."""
    errors: list[str] = []
    mapped = _mapping(document)
    if mapped is None:
        return ["mapping document: must be a JSON object"]
    _check_keys(mapped, MAPPING_KEYS, "mapping document", errors)
    if mapped.get("schema") != MAPPING_SCHEMA:
        errors.append(f"mapping document.schema: must be {MAPPING_SCHEMA!r}")
    entries = _list(mapped.get("entries"))
    if entries is None:
        errors.append("mapping document.entries: must be an array")
    else:
        for index, raw in enumerate(entries):
            _check_mapping_entry(raw, index, errors)
    classes = _list(mapped.get("in_game_classes"))
    if classes is None:
        errors.append("mapping document.in_game_classes: must be an array")
    else:
        for index, raw in enumerate(classes):
            _check_in_game_class(raw, index, errors)
    return errors


# --------------------------------------------------------------------------
# Holdout contract.
# --------------------------------------------------------------------------


def _check_metric(
    value: object,
    where: str,
    errors: list[str],
    *,
    keys: Sequence[str] = METRIC_KEYS,
    int_keys: Sequence[str] = ("n",),
) -> None:
    mapped = _mapping(value)
    if mapped is None:
        errors.append(f"{where}: must be an object")
        return
    _check_keys(mapped, keys, where, errors)
    for key in keys:
        if key in int_keys:
            _check_int(mapped.get(key), f"{where}.{key}", errors, non_negative=True)
        else:
            _check_number(mapped.get(key), f"{where}.{key}", errors)


def _check_metric_map(value: object, where: str, errors: list[str]) -> None:
    mapped = _mapping(value)
    if mapped is None:
        errors.append(f"{where}: must be an object")
        return
    for key in sorted(mapped):
        _check_metric(mapped[key], f"{where}.{key}", errors)


def holdout_errors(document: object) -> list[str]:
    """Return every error in a ``holdout/1`` document. Empty is valid."""
    errors: list[str] = []
    mapped = _mapping(document)
    if mapped is None:
        return ["holdout document: must be a JSON object"]
    _check_keys(mapped, HOLDOUT_KEYS, "holdout document", errors)
    if mapped.get("schema") != HOLDOUT_SCHEMA:
        errors.append(f"holdout document.schema: must be {HOLDOUT_SCHEMA!r}")
    _check_enum(
        mapped.get("method"), HOLDOUT_METHODS, "holdout document.method", errors
    )
    _check_metric(mapped.get("aggregate"), "holdout document.aggregate", errors)
    _check_metric_map(
        mapped.get("by_class_key"),
        "holdout document.by_class_key",
        errors,
    )
    _check_metric_map(
        mapped.get("by_mapping_basis"),
        "holdout document.by_mapping_basis",
        errors,
    )
    _check_metric(
        mapped.get("in_sample"),
        "holdout document.in_sample",
        errors,
        keys=IN_SAMPLE_KEYS,
    )
    _check_number(
        mapped.get("overfit_gap_mdape"),
        "holdout document.overfit_gap_mdape",
        errors,
    )
    _check_metric(
        mapped.get("thresholds"),
        "holdout document.thresholds",
        errors,
        keys=THRESHOLD_KEYS,
        int_keys=("n_min",),
    )
    _check_str_list(mapped.get("failures"), "holdout document.failures", errors)
    return errors


# --------------------------------------------------------------------------
# Ablation contract.
# --------------------------------------------------------------------------


def _check_arm(
    value: object,
    where: str,
    expected_name: str,
    errors: list[str],
    *,
    with_evaluable: bool,
) -> None:
    keys = ARM_KEYS + (("evaluable",) if with_evaluable else ())
    mapped = _mapping(value)
    if mapped is None:
        errors.append(f"{where}: must be an object")
        return
    _check_keys(mapped, keys, where, errors)
    if mapped.get("name") != expected_name:
        errors.append(f"{where}.name: must be {expected_name!r}")
    _check_int(mapped.get("n"), f"{where}.n", errors, non_negative=True)
    for key in ("coverage", "mdape", "width_ratio_median"):
        _check_number(mapped.get(key), f"{where}.{key}", errors)
    if with_evaluable:
        _check_bool(mapped.get("evaluable"), f"{where}.evaluable", errors)


def ablation_errors(document: object) -> list[str]:
    """Return every error in an ``ablation/1`` document. Empty is valid."""
    errors: list[str] = []
    mapped = _mapping(document)
    if mapped is None:
        return ["ablation document: must be a JSON object"]
    _check_keys(mapped, ABLATION_KEYS, "ablation document", errors)
    if mapped.get("schema") != ABLATION_SCHEMA:
        errors.append(f"ablation document.schema: must be {ABLATION_SCHEMA!r}")
    _check_arm(
        mapped.get("arm_a"),
        "ablation document.arm_a",
        ARM_A_NAME,
        errors,
        with_evaluable=False,
    )
    _check_arm(
        mapped.get("arm_b"),
        "ablation document.arm_b",
        ARM_B_NAME,
        errors,
        with_evaluable=True,
    )
    _check_str(mapped.get("corpus_note"), "ablation document.corpus_note", errors)
    _check_str(
        mapped.get("engine_probe_note"),
        "ablation document.engine_probe_note",
        errors,
    )
    return errors


# --------------------------------------------------------------------------
# Strict loaders.
# --------------------------------------------------------------------------


def _read_json(path: Path) -> object:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(path, [f"cannot read: {exc}"]) from exc
    try:
        return cast("object", json.loads(text))
    except json.JSONDecodeError as exc:
        raise ContractError(path, [f"malformed JSON: {exc}"]) from exc


def _load_contract(path: Path, validate: Callable[[object], list[str]]) -> object:
    value = _read_json(path)
    errors = validate(value)
    if errors:
        raise ContractError(path, errors)
    return value


def _as_document(path: Path, value: object, kind: str) -> dict[str, object]:
    mapped = _mapping(value)
    if mapped is None:
        raise ContractError(path, [f"{kind}: must be a JSON object"])
    return mapped


def load_probe_record(path: Path) -> dict[str, object]:
    """Load and validate one ``probe/1`` record."""
    return _as_document(path, _load_contract(path, probe_errors), "probe record")


def load_mapping(path: Path) -> dict[str, object]:
    """Load and validate a ``mapping/1`` document."""
    return _as_document(path, _load_contract(path, mapping_errors), "mapping document")


def load_holdout(path: Path) -> dict[str, object]:
    """Load and validate a ``holdout/1`` document."""
    return _as_document(path, _load_contract(path, holdout_errors), "holdout document")


def load_ablation(path: Path) -> dict[str, object]:
    """Load and validate an ``ablation/1`` document."""
    return _as_document(
        path, _load_contract(path, ablation_errors), "ablation document"
    )


def load_probe_array(path: Path) -> list[dict[str, object]]:
    """Load and validate an array of ``probe/1`` records."""
    value = _read_json(path)
    items = _list(value)
    if items is None:
        raise ContractError(path, ["probe document: must be an array of records"])
    records: list[dict[str, object]] = []
    errors: list[str] = []
    for index, raw in enumerate(items):
        record_errors = probe_errors(raw)
        if record_errors:
            errors.extend(f"[{index}]: {error}" for error in record_errors)
            continue
        mapped = _mapping(raw)
        if mapped is not None:
            records.append(mapped)
    if errors:
        raise ContractError(path, errors)
    return records


# --------------------------------------------------------------------------
# Guarded writes. A symlink is never a write target.
# --------------------------------------------------------------------------


def _relative_posix(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, RuntimeError, ValueError):
        return None


def _is_protected_path(path: Path, root: Path) -> bool:
    relative = _relative_posix(path, root)
    if relative is None:
        return False
    if relative in PROTECTED_FILES:
        return True
    parent = PurePosixPath(relative).parent.as_posix()
    return parent == CATALOGUE_DIR and relative.endswith(".json")


def _refuse_protected_write(path: Path, root: Path) -> None:
    if _is_protected_path(path, root):
        raise OSError(errno.EPERM, "refusing to write a protected file", str(path))


def _refuse_symlink_parent(path: Path) -> None:
    """Refuse a write when a parent or any higher ancestor is a symlink.

    The final component is checked separately in ``_safe_write``. The walk
    covers a symlink grandparent, which the immediate-parent check missed.
    """
    current = path.parent
    while True:
        if current.is_symlink():
            raise OSError(
                errno.ELOOP,
                "refusing to write under a symlinked directory",
                str(path),
            )
        parent = current.parent
        if parent == current:
            return
        current = parent


def _safe_write(path: Path, text: str, *, root: Path = ROOT) -> None:
    """Write text through an O_NOFOLLOW descriptor.

    The guard refuses a protected file, a symlinked parent and a symlink
    target. A symlink target raises OSError with errno.ELOOP.
    """
    _refuse_protected_write(path, root)
    _refuse_symlink_parent(path)
    if path.is_symlink():
        raise OSError(errno.ELOOP, "refusing to write through a symlink", str(path))
    payload = text.encode("utf-8")
    flags = os.O_NOFOLLOW | os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    descriptor = os.open(path, flags, 0o644)
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
    finally:
        os.close(descriptor)


def _atomic_write(path: Path, text: str, *, root: Path = ROOT) -> None:
    """Write text through a sibling temp file and replace the target."""
    _refuse_protected_write(path, root)
    _refuse_symlink_parent(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            _ = handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------
# Protected-file manifest.
# --------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of one file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def protected_paths(root: Path = ROOT) -> list[Path]:
    """Return the protected files under root, the catalogue glob expanded."""
    candidates = [root / relative for relative in PROTECTED_FILES]
    for pattern in PROTECTED_GLOBS:
        candidates.extend(root.glob(pattern))
    unique: dict[str, Path] = {}
    for path in candidates:
        unique[path.relative_to(root).as_posix()] = path
    return [unique[key] for key in sorted(unique)]


def build_manifest(root: Path = ROOT) -> dict[str, str]:
    """Return one SHA-256 per protected file, keyed by its relative path."""
    manifest: dict[str, str] = {}
    for path in protected_paths(root):
        manifest[path.relative_to(root).as_posix()] = sha256_file(path)
    return manifest


def write_manifest(path: Path, *, root: Path = ROOT) -> None:
    """Hash the protected files and write the manifest atomically."""
    manifest = build_manifest(root)
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    _atomic_write(path, text, root=root)
    catalogue_count = sum(1 for key in manifest if key.startswith(f"{CATALOGUE_DIR}/"))
    print(f"vehicle mass accuracy: manifest {path}")
    print(f"  protected list entries: {len(PROTECTED_FILES) + len(PROTECTED_GLOBS)}")
    print(f"  named files: {len(PROTECTED_FILES)}, catalogue files: {catalogue_count}")
    print(f"  hashed paths: {len(manifest)}")


# --------------------------------------------------------------------------
# Self-check fixtures. Every write goes to a private temporary directory.
# --------------------------------------------------------------------------


def _metric_fixture() -> dict[str, object]:
    return {
        "n": 46,
        "coverage": 1.0,
        "mdape": 0.1402,
        "width_ratio_median": 2.9,
        "interval_distance_median": 0.0,
        "bias_median": 0.01,
    }


def _probe_fixture() -> dict[str, object]:
    return {
        "schema": PROBE_SCHEMA,
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


def _mapping_fixture() -> dict[str, object]:
    return {
        "schema": MAPPING_SCHEMA,
        "entries": [
            {
                "catalogue_id": "fixture_entry",
                "class_key": "wheeled",
                "resolve_path": "token",
                "mapping_basis": "exact",
                "mass_field": "curb_weight_kg",
                "mass_kg": 1500.0,
                "volume_m3": 12.5,
                "evidence": "self-check fixture",
            }
        ],
        "in_game_classes": [
            {
                "class": "C_Hatchback_01_F",
                "catalogue_id": "fixture_entry",
                "mapping_basis": "analogue",
                "evidence": "self-check fixture",
            }
        ],
    }


def _holdout_fixture() -> dict[str, object]:
    metric = _metric_fixture()
    return {
        "schema": HOLDOUT_SCHEMA,
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


def _ablation_fixture() -> dict[str, object]:
    return {
        "schema": ABLATION_SCHEMA,
        "arm_a": {
            "name": ARM_A_NAME,
            "n": 6,
            "coverage": 0.5,
            "mdape": 0.2,
            "width_ratio_median": 3.0,
        },
        "arm_b": {
            "name": ARM_B_NAME,
            "n": 6,
            "coverage": 0.5,
            "mdape": 0.2,
            "width_ratio_median": 3.0,
            "evaluable": False,
        },
        "corpus_note": "the sourced corpus holds no material class field",
        "engine_probe_note": "engine-relative only, not real-world accuracy",
    }


def _write_fixture(path: Path, root: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _safe_write(path, json.dumps(payload, indent=2) + "\n", root=root)


def _check_contract_round_trips(private: Path, failures: list[str]) -> None:
    loaders: tuple[tuple[str, dict[str, object], Callable[[Path], object]], ...] = (
        ("probe", _probe_fixture(), load_probe_record),
        ("mapping", _mapping_fixture(), load_mapping),
        ("holdout", _holdout_fixture(), load_holdout),
        ("ablation", _ablation_fixture(), load_ablation),
    )
    for name, fixture, loader in loaders:
        path = private / f"{name}-fixture.json"
        _write_fixture(path, private, fixture)
        try:
            _ = loader(path)
        except ContractError as exc:
            failures.append(f"self-check {name} fixture was rejected: {exc}")


def _expect_reject(
    private: Path,
    name: str,
    valid: object,
    mutated: object,
    validator: Callable[[object], list[str]],
    failures: list[str],
    *,
    malformed: bool = False,
) -> None:
    path = private / f"reject-{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if malformed:
        _ = _safe_write(path, "{ not json", root=private)
        try:
            _ = _load_contract(path, validator)
        except ContractError:
            return
        failures.append(f"self-check {name}: the loader accepted malformed JSON")
        return
    if validator(valid):
        failures.append(f"self-check {name}: the valid fixture was rejected")
    if not validator(mutated):
        failures.append(f"self-check {name}: the invalid fixture was accepted")
    _ = _safe_write(path, json.dumps(mutated), root=private)
    try:
        _ = _load_contract(path, validator)
    except ContractError:
        return
    failures.append(f"self-check {name}: the loader accepted an invalid file")


def _check_contract_rejections(private: Path, failures: list[str]) -> None:
    probe = _probe_fixture()
    missing_key = copy.deepcopy(probe)
    del missing_key["status"]
    _expect_reject(
        private, "probe-missing-key", probe, missing_key, probe_errors, failures
    )

    wrong_type = copy.deepcopy(probe)
    wrong_type["get_mass"] = "8306.63"
    _expect_reject(
        private, "probe-wrong-type", probe, wrong_type, probe_errors, failures
    )

    wrong_schema = copy.deepcopy(probe)
    wrong_schema["schema"] = "aee.vehicle.mass_accuracy.probe/2"
    _expect_reject(
        private, "probe-wrong-schema", probe, wrong_schema, probe_errors, failures
    )

    flag_off = copy.deepcopy(probe)
    flag_off["engine_relative_only"] = False
    _expect_reject(private, "probe-flag-off", probe, flag_off, probe_errors, failures)

    unexpected_key = copy.deepcopy(probe)
    unexpected_key["unexpected_field"] = 1
    _expect_reject(
        private,
        "probe-unexpected-key",
        probe,
        unexpected_key,
        probe_errors,
        failures,
    )

    mapping = _mapping_fixture()
    bad_enum = copy.deepcopy(mapping)
    entries = _list(bad_enum["entries"])
    if entries and isinstance(entries[0], dict):
        entries[0]["resolve_path"] = "guess"
    _expect_reject(private, "mapping-enum", mapping, bad_enum, mapping_errors, failures)

    _expect_reject(private, "mapping-non-object", mapping, [], mapping_errors, failures)

    ablation = _ablation_fixture()
    missing_nested = copy.deepcopy(ablation)
    arm_b = missing_nested["arm_b"]
    if isinstance(arm_b, dict):
        del arm_b["evaluable"]
    _expect_reject(
        private,
        "ablation-missing-nested",
        ablation,
        missing_nested,
        ablation_errors,
        failures,
    )

    holdout = _holdout_fixture()
    bad_metric = copy.deepcopy(holdout)
    aggregate = bad_metric["aggregate"]
    if isinstance(aggregate, dict):
        aggregate["coverage"] = "high"
    _expect_reject(
        private, "holdout-wrong-type", holdout, bad_metric, holdout_errors, failures
    )

    float_threshold = copy.deepcopy(holdout)
    thresholds = float_threshold["thresholds"]
    if isinstance(thresholds, dict):
        thresholds["n_min"] = 30.5
    _expect_reject(
        private,
        "holdout-threshold-float",
        holdout,
        float_threshold,
        holdout_errors,
        failures,
    )

    _expect_reject(
        private,
        "malformed-json",
        holdout,
        holdout,
        holdout_errors,
        failures,
        malformed=True,
    )


def _check_safe_write(private: Path, failures: list[str]) -> None:
    target = private / "target.txt"
    _safe_write(target, "original", root=private)
    link = private / "link.txt"
    link.symlink_to(target)
    try:
        _safe_write(link, "hacked", root=private)
        failures.append("self-check safe-write wrote through a symlink target")
    except OSError as exc:
        if exc.errno != errno.ELOOP:
            failures.append(f"self-check symlink target errno {exc.errno} is not ELOOP")
    if target.read_text(encoding="utf-8") != "original":
        failures.append("self-check symlink target bytes changed")

    real_dir = private / "real-dir"
    real_dir.mkdir()
    link_dir = private / "link-dir"
    link_dir.symlink_to(real_dir)
    try:
        _safe_write(link_dir / "child.txt", "hacked", root=private)
        failures.append("self-check safe-write wrote under a symlinked directory")
    except OSError as exc:
        if exc.errno != errno.ELOOP:
            failures.append(f"self-check symlink parent errno {exc.errno} is not ELOOP")
    if (real_dir / "child.txt").exists():
        failures.append(
            "self-check a symlinked parent write reached the real directory"
        )

    real_grandparent = private / "real-grandparent"
    (real_grandparent / "child").mkdir(parents=True)
    link_grandparent = private / "link-grandparent"
    link_grandparent.symlink_to(real_grandparent)
    try:
        _safe_write(
            link_grandparent / "child" / "grandchild.txt",
            "hacked",
            root=private,
        )
        failures.append("self-check safe-write wrote under a symlinked grandparent")
    except OSError as exc:
        if exc.errno != errno.ELOOP:
            failures.append(
                f"self-check symlink grandparent errno {exc.errno} is not ELOOP"
            )
    if (real_grandparent / "child" / "grandchild.txt").exists():
        failures.append(
            "self-check a symlinked grandparent write reached the real directory"
        )

    protected = private / "data/vehicle/mass_model.json"
    protected.parent.mkdir(parents=True)
    try:
        _safe_write(protected, "hacked", root=private)
        failures.append("self-check safe-write wrote a protected path")
    except OSError as exc:
        if exc.errno != errno.EPERM:
            failures.append(
                f"self-check protected-write errno {exc.errno} is not EPERM"
            )
    if protected.exists():
        failures.append("self-check a protected path was created")


def _check_manifest(private: Path, failures: list[str]) -> None:
    fake = private / "fake-root"
    for relative in PROTECTED_FILES:
        _write_fixture(fake / relative, private, relative)
    catalogue = fake / CATALOGUE_DIR
    catalogue.mkdir(parents=True)
    for name in ("b.json", "a.json"):
        _safe_write(catalogue / name, name, root=private)

    manifest = build_manifest(fake)
    expected = set(PROTECTED_FILES) | {
        f"{CATALOGUE_DIR}/a.json",
        f"{CATALOGUE_DIR}/b.json",
    }
    if set(manifest) != expected:
        failures.append("self-check manifest path set is wrong")
    if len(manifest) != len(PROTECTED_FILES) + 2:
        failures.append(
            f"self-check manifest size {len(manifest)} != {len(PROTECTED_FILES) + 2}"
        )
    if manifest.get("data/vehicle/mass_model.json") != sha256_file(
        fake / "data/vehicle/mass_model.json"
    ):
        failures.append("self-check manifest hash mismatch")

    manifest_path = private / "manifest.json"
    _atomic_write(
        manifest_path,
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        root=private,
    )
    reloaded = _read_json(manifest_path)
    if reloaded != manifest:
        failures.append("self-check manifest did not round-trip")


def self_check() -> list[str]:
    """Exercise the contracts and the guards in a private temporary tree."""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        private = Path(tmp)
        _check_contract_round_trips(private, failures)
        _check_contract_rejections(private, failures)
        _check_safe_write(private, failures)
        _check_manifest(private, failures)
    return failures


# --------------------------------------------------------------------------
# Campaign analysis engine (plan tasks 2, 3 and 4).
#
# The engine is read-only against the repository. It never writes the real
# model, never invents a threshold and never treats an engine value as a
# real-world value. The holdout builds a local shadow model. The ablation
# scores the readable-material arm only on the engine probe. The ingest
# validates every probe record and keeps a failed spawn record.
# --------------------------------------------------------------------------

MASS_ACCURACY_DIR = ROOT / ".omo" / "evidence" / "vehicle-mass-accuracy"
POWER_PROBE_PATH = (
    ROOT / ".omo" / "evidence" / "vehicle-mass-model" / "power-probe.json"
)
PROBE_MARKER = "[AEE-MASS]"
FIXED_CLASS_LIST: tuple[str, ...] = (
    "B_MRAP_01_F",
    "B_Truck_01_transport_F",
    "B_APC_Wheeled_01_cannon_F",
    "B_APC_Tracked_01_rcws_F",
    "C_Hatchback_01_F",
    "B_Motorcycle_01_F",
)
MOTORCYCLE_CLASS = "B_Motorcycle_01_F"
NON_EVALUABLE_MATERIALS: frozenset[str] = frozenset({"", "none", "ground"})
DEFAULT_MAPPING_BASIS = "class_only"
CORPUS_NOTE = (
    "the sourced corpus holds no material class field, so the readable-material "
    "arm is not evaluable on the corpus; the corpus arm is in-sample and is not "
    "independent accuracy"
)
ENGINE_LABEL = (
    "engine_relative_only: getMass is a PhysX engine value with no verified "
    "real-world unit, so every engine-probe comparison is a consistency check, "
    "not real-world accuracy"
)
# Trailing tokens that name a variant of one family. The group key strips them
# so a whole family is held out together and no variant leaks across the split.
_VARIANT_WORDS: frozenset[str] = frozenset(
    {
        "coupe",
        "sedan",
        "hatchback",
        "convertible",
        "wagon",
        "estate",
        "pickup",
        "technical",
        "utility",
        "cargo",
        "transport",
        "ambulance",
        "command",
    }
)
Row = dict[str, object]


def _median(values: Sequence[float]) -> float:
    return statistics.median(values) if values else 0.0


def _row_number(value: object) -> float:
    """Return a row metric as a float. A non-number is zero, never a crash."""
    return float(value) if _is_number(value) else 0.0


def _is_variant_token(token: str) -> bool:
    return token.isdigit() or len(token) == 1 or token in _VARIANT_WORDS


def family_key(entry: catalogue.CatalogueEntry) -> str:
    """Return the vehicle family. Every variant of one family shares a key.

    The model name groups the variants when it is present. When the model is
    empty, the variant id is used with the trailing variant tokens removed.
    """
    if entry.model:
        return entry.model
    if entry.variant_id:
        tokens = [token for token in entry.variant_id.split("_") if token]
        while len(tokens) > 1 and _is_variant_token(tokens[-1]):
            tokens.pop()
        return "_".join(tokens)
    return entry.catalogue_id


def _entry_class_key(
    model: Mapping[str, object], entry: catalogue.CatalogueEntry
) -> str:
    resolved = resolve_mass_class(cast("dict[str, object]", model), entry)
    return str(resolved.get("key", "")) if resolved is not None else ""


def _entry_interval(
    model: Mapping[str, object], entry: catalogue.CatalogueEntry
) -> tuple[str, float, float] | None:
    """Return the modelled interval for one entry, or None when unavailable."""
    resolved = resolve_mass_class(cast("dict[str, object]", model), entry)
    if resolved is None:
        return None
    density = _mapping(model.get("material_density"))
    if density is None:
        return None
    rho = _mapping(density.get(str(resolved.get("density_class", ""))))
    if rho is None:
        return None
    volume = entry_volume_m3(entry)
    if volume is None:
        return None
    rho_low = rho.get("low")
    rho_high = rho.get("high")
    fill_low = resolved.get("fill_low")
    fill_high = resolved.get("fill_high")
    if not _is_number(rho_low) or not _is_number(rho_high):
        return None
    if not _is_number(fill_low) or not _is_number(fill_high):
        return None
    low = volume * float(fill_low) * float(rho_low)
    high = volume * float(fill_high) * float(rho_high)
    return str(resolved.get("key", "")), low, high


def _row_metrics(low: float, high: float, mass: float) -> Row:
    """Return the per-entry metrics for one modelled interval.

    A non-positive mass cannot anchor a ratio. Such a row is marked as a miss
    and kept, so it is counted and never dropped.
    """
    covers = low <= mass <= high
    if low > 0 and high > 0:
        centre = math.sqrt(low * high)
        width_ratio = high / low
    else:
        centre = low
        width_ratio = 0.0
    if mass > 0:
        ape = abs(centre - mass) / mass
        bias = (centre - mass) / mass
        if covers:
            interval_distance = 0.0
        else:
            interval_distance = min(abs(mass - low), abs(mass - high)) / mass
    else:
        ape = 1.0
        bias = 0.0
        interval_distance = 1.0
    return {
        "covers": covers,
        "ape": ape,
        "width_ratio": width_ratio,
        "interval_distance": interval_distance,
        "bias": bias,
    }


def _metric_from_rows(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Aggregate a row set into the ``holdout/1`` metric object."""
    count = len(rows)
    if count == 0:
        return {
            "n": 0,
            "coverage": 0.0,
            "mdape": 0.0,
            "width_ratio_median": 0.0,
            "interval_distance_median": 0.0,
            "bias_median": 0.0,
        }
    coverage = sum(1 for row in rows if bool(row["covers"])) / count
    return {
        "n": count,
        "coverage": round(coverage, 4),
        "mdape": round(_median([_row_number(row["ape"]) for row in rows]), 4),
        "width_ratio_median": round(
            _median([_row_number(row["width_ratio"]) for row in rows]), 4
        ),
        "interval_distance_median": round(
            _median([_row_number(row["interval_distance"]) for row in rows]), 4
        ),
        "bias_median": round(_median([_row_number(row["bias"]) for row in rows]), 4),
    }


def _group_rows(rows: Sequence[Mapping[str, object]], key: str) -> dict[str, object]:
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row[key]), []).append(row)
    return {name: _metric_from_rows(grouped[name]) for name in sorted(grouped)}


def _calibratable_entries(
    model: Mapping[str, object], entries: Sequence[catalogue.CatalogueEntry]
) -> list[catalogue.CatalogueEntry]:
    selected: list[catalogue.CatalogueEntry] = []
    for entry in entries:
        if skip_reason(entry) is not None:
            continue
        if documented_mass(entry) is None:
            continue
        if resolve_mass_class(cast("dict[str, object]", model), entry) is None:
            continue
        selected.append(entry)
    return selected


def _shadow_model(
    model: Mapping[str, object], proposals: Sequence[object]
) -> dict[str, object]:
    """Deep-copy the model and apply the proposals with ``approved=True``.

    The real model is never written. This is a local shadow object only.
    """
    shadow = copy.deepcopy(dict(model))
    fills = {
        str(getattr(proposal, "key", "")): proposal
        for proposal in proposals
        if getattr(proposal, "key", None)
    }
    classes = shadow.get("mass_classes")
    if isinstance(classes, list):
        for raw in classes:
            if not isinstance(raw, dict):
                continue
            proposal = fills.get(str(raw.get("key", "")))
            if proposal is None:
                continue
            raw["fill_low"] = getattr(proposal, "fill_low")
            raw["fill_high"] = getattr(proposal, "fill_high")
            raw["n"] = getattr(proposal, "n")
    calibration = shadow.get("calibration")
    if isinstance(calibration, dict):
        calibration["approved"] = True
    return shadow


def _score_entry(
    shadow: Mapping[str, object],
    entry: catalogue.CatalogueEntry,
    basis_index: Mapping[str, str],
) -> Row | None:
    """Score one held-out entry against the shadow model."""
    interval = _entry_interval(shadow, entry)
    mass = documented_mass(entry)
    if interval is None or mass is None:
        return None
    key, low, high = interval
    single = evaluate(cast("dict[str, object]", shadow), [entry])
    if single.n_entries != 1:
        return None
    row = _row_metrics(low, high, mass[1])
    row["covers"] = single.in_band == 1
    row["class_key"] = key
    row["catalogue_id"] = entry.catalogue_id
    row["mapping_basis"] = basis_index.get(entry.catalogue_id, DEFAULT_MAPPING_BASIS)
    return row


def _fold_rows(
    model: Mapping[str, object],
    train: Sequence[catalogue.CatalogueEntry],
    holdout: Sequence[catalogue.CatalogueEntry],
    basis_index: Mapping[str, str],
) -> list[Row]:
    proposals, _ = calibrate(cast("dict[str, object]", model), list(train))
    shadow = _shadow_model(model, proposals)
    rows: list[Row] = []
    for entry in holdout:
        row = _score_entry(shadow, entry, basis_index)
        if row is not None:
            rows.append(row)
    return rows


def leave_one_out(
    model: Mapping[str, object],
    entries: Sequence[catalogue.CatalogueEntry],
    basis_index: Mapping[str, str],
) -> list[Row]:
    """Hold out one entry per fold. No random number generator."""
    rows: list[Row] = []
    for index, holdout in enumerate(entries):
        train = [entry for other, entry in enumerate(entries) if other != index]
        rows.extend(_fold_rows(model, train, [holdout], basis_index))
    return rows


def grouped_leave_one_out(
    model: Mapping[str, object],
    entries: Sequence[catalogue.CatalogueEntry],
    basis_index: Mapping[str, str],
) -> list[Row]:
    """Hold out one whole vehicle family per fold."""
    groups: dict[str, list[catalogue.CatalogueEntry]] = {}
    for entry in entries:
        groups.setdefault(family_key(entry), []).append(entry)
    rows: list[Row] = []
    for name in sorted(groups):
        held = {entry.catalogue_id for entry in groups[name]}
        train = [entry for entry in entries if entry.catalogue_id not in held]
        rows.extend(_fold_rows(model, train, groups[name], basis_index))
    return rows


def stratified_split(
    model: Mapping[str, object],
    entries: Sequence[catalogue.CatalogueEntry],
    basis_index: Mapping[str, str],
) -> list[Row]:
    """Take every fifth entry as holdout, sorted by class key then id."""
    ordered = sorted(
        entries,
        key=lambda entry: (_entry_class_key(model, entry), entry.catalogue_id),
    )
    train = [entry for index, entry in enumerate(ordered) if (index + 1) % 5 != 0]
    holdout = [entry for index, entry in enumerate(ordered) if (index + 1) % 5 == 0]
    return _fold_rows(model, train, holdout, basis_index)


def _mapping_basis_index(mapping: Mapping[str, object] | None) -> dict[str, str]:
    if mapping is None:
        return {}
    entries = _list(mapping.get("entries"))
    index: dict[str, str] = {}
    if entries is None:
        return index
    for raw in entries:
        entry = _mapping(raw)
        if entry is None:
            continue
        catalogue_id = entry.get("catalogue_id")
        basis = entry.get("mapping_basis")
        if _is_str(catalogue_id) and _is_str(basis):
            index[catalogue_id] = basis
    return index


def _in_sample_metrics(
    model: Mapping[str, object], entries: Sequence[catalogue.CatalogueEntry]
) -> dict[str, object]:
    metrics = evaluate(cast("dict[str, object]", model), list(entries))
    return {
        "n": metrics.n_entries,
        "coverage": round(metrics.fraction_in_band, 4),
        "mdape": round(metrics.mdape, 4),
    }


def _thresholds(model: Mapping[str, object]) -> dict[str, object]:
    bands = _mapping(model.get("geometry_bands")) or {}
    width_max = bands.get("max_width_ratio")
    if not _is_number(width_max):
        width_max = DEFAULT_MAX_WIDTH_RATIO
    return {
        "n_min": MIN_ENTRIES,
        "coverage_min": MIN_FRACTION_IN_BAND,
        "mdape_max": MAX_MDAPE,
        "width_max": float(width_max),
    }


def _holdout_failures(
    model: Mapping[str, object],
    aggregate: Mapping[str, object],
    rows: Sequence[Mapping[str, object]],
) -> list[str]:
    """Reuse the existing approval thresholds on the holdout metrics."""
    failures: list[str] = []
    if not rows:
        failures.append("holdout produced no rows")
    approved = copy.deepcopy(dict(model))
    calibration = approved.get("calibration")
    if isinstance(calibration, dict):
        calibration["approved"] = True
    density = _mapping(model.get("material_density")) or {}
    counts: Counter[str] = Counter(str(row["class_key"]) for row in rows)
    classes: list[ClassMetric] = []
    raw_classes = model.get("mass_classes")
    if isinstance(raw_classes, list):
        for raw in raw_classes:
            entry = _mapping(raw)
            if entry is None:
                continue
            key = str(entry.get("key", ""))
            rho = _mapping(density.get(str(entry.get("density_class", "")))) or {}
            rho_low = rho.get("low")
            rho_high = rho.get("high")
            fill_low = entry.get("fill_low")
            fill_high = entry.get("fill_high")
            classes.append(
                ClassMetric(
                    key,
                    counts.get(key, 0),
                    float(fill_low) if _is_number(fill_low) else 0.0,
                    float(fill_high) if _is_number(fill_high) else 0.0,
                    float(rho_low) if _is_number(rho_low) else 0.0,
                    float(rho_high) if _is_number(rho_high) else 0.0,
                )
            )
    coverage = aggregate.get("coverage")
    mdape = aggregate.get("mdape")
    metrics = Metrics(
        len(rows),
        sum(1 for row in rows if bool(row["covers"])),
        float(coverage) if _is_number(coverage) else 0.0,
        float(mdape) if _is_number(mdape) else 0.0,
        tuple(classes),
    )
    failures.extend(approval_failures(approved, metrics))
    return failures


def holdout_document(
    model: Mapping[str, object],
    entries: Sequence[catalogue.CatalogueEntry],
    mapping: Mapping[str, object] | None,
    method: str,
) -> dict[str, object]:
    """Build one ``holdout/1`` document for one method."""
    if method not in HOLDOUT_METHODS:
        raise SystemExit(f"unknown holdout method: {method}")
    calibratable = _calibratable_entries(model, entries)
    basis_index = _mapping_basis_index(mapping)
    if method == "leave_one_out":
        rows = leave_one_out(model, calibratable, basis_index)
    elif method == "grouped_leave_one_out":
        rows = grouped_leave_one_out(model, calibratable, basis_index)
    else:
        rows = stratified_split(model, calibratable, basis_index)
    aggregate = _metric_from_rows(rows)
    in_sample = _in_sample_metrics(model, calibratable)
    overfit_gap = round(
        _row_number(aggregate["mdape"]) - _row_number(in_sample["mdape"]), 4
    )
    return {
        "schema": HOLDOUT_SCHEMA,
        "method": method,
        "aggregate": aggregate,
        "by_class_key": _group_rows(rows, "class_key"),
        "by_mapping_basis": _group_rows(rows, "mapping_basis"),
        "in_sample": in_sample,
        "overfit_gap_mdape": overfit_gap,
        "thresholds": _thresholds(model),
        "failures": _holdout_failures(model, aggregate, rows),
    }


# --------------------------------------------------------------------------
# Material ablation (plan task 3).
# --------------------------------------------------------------------------


def _density_ranges(model: Mapping[str, object]) -> dict[str, tuple[float, float]]:
    density = _mapping(model.get("material_density"))
    ranges: dict[str, tuple[float, float]] = {}
    if density is None:
        return ranges
    for name, raw in density.items():
        entry = _mapping(raw)
        if entry is None:
            continue
        low = entry.get("low")
        high = entry.get("high")
        if _is_number(low) and _is_number(high):
            ranges[str(name)] = (float(low), float(high))
    return ranges


def _arm_from_rows(
    name: str, rows: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    metric = _metric_from_rows(rows)
    return {
        "name": name,
        "n": metric["n"],
        "coverage": metric["coverage"],
        "mdape": metric["mdape"],
        "width_ratio_median": metric["width_ratio_median"],
    }


def _empty_arm(name: str) -> dict[str, object]:
    return {
        "name": name,
        "n": 0,
        "coverage": 0.0,
        "mdape": 0.0,
        "width_ratio_median": 0.0,
    }


def _corpus_arm_a_rows(
    model: Mapping[str, object], entries: Sequence[catalogue.CatalogueEntry]
) -> list[Row]:
    rows: list[Row] = []
    for entry in _calibratable_entries(model, entries):
        interval = _entry_interval(model, entry)
        mass = documented_mass(entry)
        if interval is None or mass is None:
            continue
        _, low, high = interval
        rows.append(_row_metrics(low, high, mass[1]))
    return rows


def _probe_materials(
    records: Sequence[Mapping[str, object]],
    density: Mapping[str, tuple[float, float]],
) -> list[str]:
    materials: list[str] = []
    for record in records:
        if record.get("spawned") is not True:
            continue
        material = str(record.get("readable_material_class", ""))
        if material not in NON_EVALUABLE_MATERIALS and material in density:
            if material not in materials:
                materials.append(material)
    return sorted(materials)


def _probe_rows(
    records: Sequence[Mapping[str, object]],
    density: Mapping[str, tuple[float, float]],
    *,
    swap_material: bool,
) -> list[Row]:
    """Score the engine probe. Arm A uses the recorded interval. Arm B swaps
    the declared readable material in and keeps the same fill range."""
    rows: list[Row] = []
    metal = density.get("metal")
    for record in records:
        if record.get("spawned") is not True:
            continue
        interval = _list(record.get("model_interval_kg"))
        mass = record.get("get_mass")
        if interval is None or len(interval) != 2 or not _is_number(mass):
            continue
        if float(mass) <= 0:
            continue
        low = interval[0]
        high = interval[1]
        if not _is_number(low) or not _is_number(high):
            continue
        low_value = float(low)
        high_value = float(high)
        if swap_material:
            material = str(record.get("readable_material_class", ""))
            target = density.get(material)
            if material in NON_EVALUABLE_MATERIALS or target is None or metal is None:
                continue
            if target[0] <= 0 or metal[0] <= 0:
                continue
            low_value = low_value * target[0] / metal[0]
            high_value = high_value * target[1] / metal[1]
        if low_value <= 0 or high_value <= 0:
            continue
        rows.append(_row_metrics(low_value, high_value, float(mass)))
    return rows


def _engine_probe_note(
    arm_a: Mapping[str, object],
    arm_b: Mapping[str, object],
    materials: Sequence[str],
    records: Sequence[Mapping[str, object]],
) -> str:
    spawned = sum(1 for record in records if record.get("spawned") is True)
    delta = _row_number(arm_b["width_ratio_median"]) - _row_number(
        arm_a["width_ratio_median"]
    )
    return (
        f"{ENGINE_LABEL}. spawned probe records: {spawned}. "
        f"readable material classes found: "
        f"{', '.join(materials) if materials else 'none'}. "
        f"arm A geometry_class_fill_only width_ratio_median "
        f"{arm_a['width_ratio_median']}, arm B readable_material_class "
        f"width_ratio_median {arm_b['width_ratio_median']}, delta {round(delta, 4)}."
    )


def ablation_document(
    model: Mapping[str, object],
    entries: Sequence[catalogue.CatalogueEntry],
    records: Sequence[Mapping[str, object]] | None,
) -> dict[str, object]:
    """Build one ``ablation/1`` document.

    With an engine probe the two arms are scored on the probe. Without one the
    corpus arm A is recorded and arm B stays not evaluable, because the sourced
    corpus holds no material class field.
    """
    density = _density_ranges(model)
    if records is not None:
        probe = [record for record in records if isinstance(record, dict)]
        arm_a = _arm_from_rows(
            ARM_A_NAME, _probe_rows(probe, density, swap_material=False)
        )
        materials = _probe_materials(probe, density)
        arm_b_rows = _probe_rows(probe, density, swap_material=True)
        evaluable = bool(arm_b_rows) and bool(materials)
        if evaluable:
            arm_b = _arm_from_rows(ARM_B_NAME, arm_b_rows)
        else:
            arm_b = _empty_arm(ARM_B_NAME)
        arm_b["evaluable"] = evaluable
        note = _engine_probe_note(arm_a, arm_b, materials, probe)
    else:
        arm_a = _arm_from_rows(ARM_A_NAME, _corpus_arm_a_rows(model, entries))
        arm_b = _empty_arm(ARM_B_NAME)
        arm_b["evaluable"] = False
        note = (
            "no engine probe supplied, so the readable-material arm was not "
            "scored. engine_relative_only: getMass is an engine value."
        )
    return {
        "schema": ABLATION_SCHEMA,
        "arm_a": arm_a,
        "arm_b": arm_b,
        "corpus_note": CORPUS_NOTE,
        "engine_probe_note": note,
    }


# --------------------------------------------------------------------------
# Engine-probe ingest (plan task 4).
# --------------------------------------------------------------------------


def extract_probe_payload(line: str) -> str | None:
    """Return the JSON text after the marker on one log line, or None.

    ``diag_log`` wraps a string in quotes, so the payload can carry one
    trailing quote after the JSON object. The wrapper quotes are removed.
    """
    position = line.find(PROBE_MARKER)
    if position < 0:
        return None
    payload = line[position + len(PROBE_MARKER) :].strip()
    if len(payload) >= 2 and payload.startswith('"') and payload.endswith('"'):
        payload = payload[1:-1].strip()
    if payload.startswith(("{", "[")) and payload.endswith('"'):
        payload = payload[:-1].rstrip()
    return payload or None


def parse_probe_log(text: str) -> tuple[list[dict[str, object]], list[str]]:
    """Parse every ``[AEE-MASS]`` line. Return valid records and every error."""
    records: list[dict[str, object]] = []
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        payload = extract_probe_payload(line)
        if payload is None:
            continue
        try:
            value: object = json.loads(payload)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: malformed JSON: {exc}")
            continue
        mapped = _mapping(value)
        if mapped is None:
            errors.append(f"line {line_number}: probe record must be a JSON object")
            continue
        record_errors = probe_errors(mapped)
        if record_errors:
            errors.extend(f"line {line_number}: {error}" for error in record_errors)
            continue
        records.append(mapped)
    return records, errors


def _cross_check_power_probe(
    records: Sequence[Mapping[str, object]], power_probe_path: Path
) -> list[str]:
    """Compare against the five confirmed samples. A mismatch is a failure."""
    try:
        reference = json.loads(power_probe_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"power probe reference could not be read: {exc}"]
    mapped = _mapping(reference)
    samples = _list(mapped.get("samples")) if mapped is not None else None
    if samples is None:
        return ["power probe reference holds no samples array"]
    by_class: dict[str, Mapping[str, object]] = {}
    for raw in samples:
        sample = _mapping(raw)
        if sample is None:
            continue
        by_class[str(sample.get("class", ""))] = sample
    failures: list[str] = []
    for record in records:
        sample = by_class.get(str(record.get("class", "")))
        if sample is None:
            continue
        expected_power = sample.get("engine_power")
        actual_power = record.get("engine_power")
        if _is_number(expected_power) and _is_number(actual_power):
            if abs(float(actual_power) - float(expected_power)) > 0.001:
                failures.append(
                    f"class {record.get('class')}: engine_power {actual_power} "
                    f"does not match the power probe {expected_power}"
                )
        elif expected_power is not None:
            failures.append(
                f"class {record.get('class')}: engine_power is not a number"
            )
        if sample.get("bounding_box_real") != record.get("bounding_box_real"):
            failures.append(
                f"class {record.get('class')}: bounding_box_real does not match "
                "the power probe"
            )
    return failures


def ingest_log(
    text: str, power_probe_path: Path
) -> tuple[list[dict[str, object]], int, int, list[str]]:
    """Validate one log. Return records, spawned count, failed count, failures.

    A failed spawn record is retained. A missing or invalid record is a failure,
    never a silent drop.
    """
    records, failures = parse_probe_log(text)
    if not records:
        failures.append("no [AEE-MASS] probe record was found in the log")
    spawned = sum(1 for record in records if record.get("spawned") is True)
    failed = sum(1 for record in records if record.get("spawned") is False)
    if MOTORCYCLE_CLASS in FIXED_CLASS_LIST:
        motorcycle = any(
            record.get("class") == MOTORCYCLE_CLASS and record.get("spawned") is False
            for record in records
        )
        if failed == 0 or not motorcycle:
            failures.append(
                f"the fixed class list holds {MOTORCYCLE_CLASS}, but no failed "
                "spawn record for it was ingested"
            )
    failures.extend(_cross_check_power_probe(records, power_probe_path))
    return records, spawned, failed, failures


def write_ingest(
    log_path: Path, out_path: Path, power_probe_path: Path = POWER_PROBE_PATH
) -> tuple[int, list[str]]:
    """Ingest one log, write the validated records to ``out_path`` on success."""
    text = log_path.read_text(encoding="utf-8", errors="replace")
    records, spawned, failed, failures = ingest_log(text, power_probe_path)
    if failures:
        return 1, failures
    _atomic_write(out_path, json.dumps(records, indent=2, sort_keys=True) + "\n")
    print(f"vehicle mass accuracy: ingest {log_path}")
    print(f"  records: {len(records)}, spawned: {spawned}, failed: {failed}")
    print(f"  wrote: {out_path}")
    return 0, []


# --------------------------------------------------------------------------
# Command line.
# --------------------------------------------------------------------------


def _select_mode(current: str | None, argument: str) -> str:
    if current is not None:
        raise SystemExit(
            "choose only one of --self-check, --manifest, --holdout, "
            "--ablation, --ingest"
        )
    return argument[2:]


@dataclass(frozen=True)
class _Options:
    mode: str
    input_path: Path | None = None
    out: Path | None = None
    mapping: Path | None = None
    probe: Path | None = None
    power_probe: Path | None = None
    method: str = "leave_one_out"


def _parse_args(argv: Sequence[str]) -> _Options:
    mode: str | None = None
    input_path: Path | None = None
    out: Path | None = None
    mapping: Path | None = None
    probe: Path | None = None
    power_probe: Path | None = None
    method = "leave_one_out"
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in ("--self-check", "--holdout", "--ablation"):
            mode = _select_mode(mode, argument)
        elif argument in (
            "--manifest",
            "--ingest",
            "--out",
            "--mapping",
            "--probe",
            "--power-probe",
            "--method",
        ):
            index += 1
            if index >= len(argv):
                raise SystemExit(f"{argument} needs a value")
            value = argv[index]
            if argument in ("--manifest", "--ingest"):
                mode = _select_mode(mode, argument)
                input_path = Path(value)
            elif argument == "--out":
                out = Path(value)
            elif argument == "--mapping":
                mapping = Path(value)
            elif argument == "--probe":
                probe = Path(value)
            elif argument == "--power-probe":
                power_probe = Path(value)
            else:
                method = value
        elif argument in ("-h", "--help"):
            print(USAGE)
            raise SystemExit(0)
        else:
            raise SystemExit(f"unknown argument: {argument}")
        index += 1
    if mode is None:
        raise SystemExit(USAGE)
    return _Options(mode, input_path, out, mapping, probe, power_probe, method)


def _output_path(out: Path | None, default_name: str) -> Path:
    return out if out is not None else MASS_ACCURACY_DIR / default_name


def _load_corpus() -> list[catalogue.CatalogueEntry]:
    """Load the committed in-game census, the basis the model is fitted on.

    The catalogue is kept only for the protected-file manifest. Its real
    overall-dimension box differs from the census by construction, so it is
    not the accuracy basis.
    """
    path = DATA_DIR / CALIBRATION_NAME
    loaded = load_calibration(path)
    if loaded.errors:
        raise ContractError(path, list(loaded.errors))
    return loaded.entries


def _write_document(path: Path, document: Mapping[str, object]) -> None:
    _atomic_write(path, json.dumps(document, indent=2, sort_keys=True) + "\n")


def _print_metric(label: str, metric: Mapping[str, object]) -> None:
    print(
        f"  {label}: n={metric['n']} coverage={metric['coverage']} "
        f"mdape={metric['mdape']} "
        f"width_ratio_median={metric['width_ratio_median']}"
    )


def _report_failures(failures: Sequence[str]) -> None:
    if failures:
        print(f"  failures: {len(failures)}")
        for failure in failures:
            print(f"    {failure}")
    else:
        print("  failures: none")


def _run_holdout(options: _Options) -> int:
    try:
        model = load_model(MODEL_PATH)
        entries = _load_corpus()
        mapping = load_mapping(options.mapping) if options.mapping is not None else None
        document = holdout_document(model, entries, mapping, options.method)
        path = _output_path(options.out, "holdout.json")
        _write_document(path, document)
    except (ContractError, OSError, ValueError) as exc:
        print(f"vehicle mass accuracy: FAIL (holdout)\n  {exc}")
        return 1
    print(f"vehicle mass accuracy: holdout {document['method']} -> {path}")
    aggregate = _mapping(document["aggregate"]) or {}
    in_sample = _mapping(document["in_sample"]) or {}
    _print_metric("aggregate", aggregate)
    print(
        f"  in_sample: n={in_sample.get('n')} coverage={in_sample.get('coverage')} "
        f"mdape={in_sample.get('mdape')}"
    )
    print(f"  overfit_gap_mdape: {document['overfit_gap_mdape']}")
    failures = _list(document["failures"]) or []
    _report_failures([str(failure) for failure in failures])
    return 1 if failures else 0


def _run_ablation(options: _Options) -> int:
    try:
        model = load_model(MODEL_PATH)
        entries = _load_corpus()
        records = None if options.probe is None else load_probe_array(options.probe)
        document = ablation_document(model, entries, records)
        path = _output_path(options.out, "ablation.json")
        _write_document(path, document)
    except (ContractError, OSError, ValueError) as exc:
        print(f"vehicle mass accuracy: FAIL (ablation)\n  {exc}")
        return 1
    print(f"vehicle mass accuracy: ablation -> {path}")
    arm_a = _mapping(document["arm_a"]) or {}
    arm_b = _mapping(document["arm_b"]) or {}
    _print_metric("arm_a", arm_a)
    _print_metric("arm_b", arm_b)
    print(f"  arm_b.evaluable: {arm_b.get('evaluable')}")
    print(f"  corpus_note: {document['corpus_note']}")
    print(f"  engine_probe_note: {document['engine_probe_note']}")
    return 0


def _run_ingest(options: _Options) -> int:
    if options.input_path is None:
        print("vehicle mass accuracy: FAIL (ingest)\n  --ingest needs a log path")
        return 1
    try:
        out = _output_path(options.out, "engine-probe.json")
        power = (
            options.power_probe if options.power_probe is not None else POWER_PROBE_PATH
        )
        code, failures = write_ingest(options.input_path, out, power)
    except (ContractError, OSError) as exc:
        print(f"vehicle mass accuracy: FAIL (ingest)\n  {exc}")
        return 1
    if code != 0:
        print("vehicle mass accuracy: FAIL (ingest)")
        for failure in failures:
            print(f"  {failure}")
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    options = _parse_args(sys.argv[1:] if argv is None else argv)

    if options.mode == "self-check":
        failures = self_check()
        if failures:
            print("vehicle mass accuracy: FAIL (self-check)")
            for failure in failures:
                print(f"  {failure}")
            return 1
        print("vehicle mass accuracy: PASS (self-check)")
        return 0

    if options.mode == "manifest":
        if options.input_path is None:
            print("vehicle mass accuracy: FAIL (manifest)\n  --manifest needs a path")
            return 1
        try:
            write_manifest(options.input_path)
        except (ContractError, OSError) as exc:
            print(f"vehicle mass accuracy: FAIL (manifest)\n  {exc}")
            return 1
        return 0

    if options.mode == "holdout":
        return _run_holdout(options)
    if options.mode == "ablation":
        return _run_ablation(options)
    return _run_ingest(options)


if __name__ == "__main__":
    raise SystemExit(main())
