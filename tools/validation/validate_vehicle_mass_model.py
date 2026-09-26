#!/usr/bin/env python3
"""Calibration and approval gate for the modelled vehicle mass model.

The model file ``data/vehicle/mass_model.json`` is a model artefact, not a
catalogue capture. This gate proves the model against the committed in-game
census ``data/vehicle/mass_model_calibration.json``. The census pairs the
in-engine default bounding box with a sourced real mass from a held catalogue
analogue, so the calibration basis matches the geometry the runtime reads. The
gate never edits a catalogue file. The estimate is modelled, bounded and
unavailable until calibration passes and a human approves it.

The catalogue loader is kept as a report-only cross-check for provenance. Its
geometry is the real overall-dimension box, so its coverage differs from the
census by construction. The cross-check never changes the exit code.

Four modes:

  default gate   compute n_entries, the in-band fraction, the global MdAPE and
                 the per mass-class width ratio. Exit 0 when ``approved`` is
                 false, because an unapproved model is a legal state. Exit 1
                 when ``approved`` is true and a threshold fails. A catalogue
                 cross-check prints for report only.
  --calibrate    read-only. Derive ``fill_low`` and ``fill_high`` per mass
                 class from the census rows, with a flat 15 per cent
                 small-sample margin, and write the report. No catalogue file
                 changes.
  --write        apply the calibration proposals and the calibration block to
                 ``mass_model.json`` and exit 0. It never sets ``approved`` to
                 true.
  --self-check   run embedded fixtures against a private temporary corpus.
                 It writes no repository file.

The census values are calibration data only. They are never copied into the
model, so the sourced corpus stays clean. Two source values are never
averaged. Each census row names one mass basis, so the shared loader finds
exactly one weight.

Run:  python3 tools/validation/validate_vehicle_mass_model.py
      python3 tools/validation/validate_vehicle_mass_model.py --calibrate
      python3 tools/validation/validate_vehicle_mass_model.py --write
      python3 tools/validation/validate_vehicle_mass_model.py --self-check
Exit: 0 on success, 1 on a model error, a corpus error or a failed approval.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
import tempfile
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# A package import (tests) and a direct script run both resolve the sibling
# loader. The repository root goes on the path first.
_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

ROOT = _REPO
DEFAULT_DATA = ROOT / "data" / "vehicle"
MODEL_NAME = "mass_model.json"
MODEL_SCHEMA = "aee.vehicle.mass_model/1"

# The held weight fields, most specific first. The gate picks the first one
# present. It never averages two fields.
MASS_FIELDS = ("operating_weight_kg", "curb_weight_kg", "gross_weight_kg")
GEOMETRY_FIELDS = ("length_mm", "width_mm", "height_mm")
MM3_PER_M3 = 1_000_000_000.0

# The committed in-game census. The runtime reads the in-game box, so the fit
# and the evaluation use the same in-engine geometry paired with a sourced
# mass. The catalogue loader is kept for a report-only cross-check.
CALIBRATION_NAME = "mass_model_calibration.json"
CALIBRATION_SCHEMA = "aee.vehicle.mass_model_calibration/1"
# The census mass basis maps to the catalogue weight field the shared loader
# reads. One row names one basis, so exactly one weight field is present.
CENSUS_MASS_FIELDS = {
    "operating": "operating_weight_kg",
    "curb": "curb_weight_kg",
    "gross": "gross_weight_kg",
}

# Calibration: a flat small-sample margin widens the band, then the fill is
# rounded. Each token holds only two to four rows, so the min-max range
# understates the true spread. The margin is not tuned to a target.
CALIBRATION_MARGIN = 0.15
FILL_ROUND = 4
METRIC_ROUND = 4

# The approval thresholds from the plan. The width cap stays in step with the
# runtime geometry band. The sample floor is the committed census paired count:
# the census covers the spawnable ground vehicle population, so
# representativeness comes from the population, not the count.
MIN_ENTRIES = 18
MIN_FRACTION_IN_BAND = 0.80
MAX_MDAPE = 0.35
DEFAULT_MAX_WIDTH_RATIO = 6.0
WIDTH_CLASS_MIN = 5

Model = dict[str, Any]


def _number(value: object) -> float | None:
    """Return a real number, rejecting a bool and a numeric string."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _mapping(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def load_model(path: Path) -> Model:
    """Read the model JSON. Raise ValueError when the top level is not an object."""
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path}: the model must be a JSON object")
    return {str(key): item for key, item in loaded.items()}


@dataclass(frozen=True)
class CalibrationLoad:
    """The result of reading the committed in-game census."""

    entries: list[catalogue.CatalogueEntry]
    errors: list[str]


def _census_held(
    value: float, unit: str, source: str, locator: str
) -> dict[str, object]:
    """Build a held value object the shared catalogue loader accepts."""
    return {
        "value": value,
        "unit": unit,
        "source": source,
        "locator": locator,
        "state": "committed in-game census",
        "grade": "documented",
    }


def load_calibration(path: Path) -> CalibrationLoad:
    """Read the in-game census as catalogue-shaped records.

    Each row carries the in-engine default box extents in millimetres, the
    resolved class token, the vehicle type, one sourced real mass and its
    basis. The rows become ``CatalogueEntry`` records so the shared resolver
    and the metric functions read one shape.
    """
    errors: list[str] = []
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: cannot read the census: {exc}")
        return CalibrationLoad([], errors)
    payload = _mapping(loaded)
    if payload is None:
        errors.append(f"{path}: the census must be a JSON object")
        return CalibrationLoad([], errors)
    if payload.get("schema") != CALIBRATION_SCHEMA:
        errors.append(f"{path}: schema must be {CALIBRATION_SCHEMA}")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        errors.append(f"{path}: rows must be a non-empty array")
        return CalibrationLoad([], errors)
    entries: list[catalogue.CatalogueEntry] = []
    seen: set[str] = set()
    for index, raw in enumerate(rows):
        where = f"{CALIBRATION_NAME} rows[{index}]"
        row = _mapping(raw)
        if row is None:
            errors.append(f"{where}: must be an object")
            continue
        ident = row.get("id")
        if not isinstance(ident, str) or not ident.strip():
            errors.append(f"{where}: id must be a non-empty string")
            continue
        if ident in seen:
            errors.append(f"{where}: duplicate id {ident}")
            continue
        seen.add(ident)
        token = row.get("class_token")
        if not isinstance(token, str) or not token.strip():
            errors.append(f"{where}: class_token must be a non-empty string")
            continue
        vehicle_type = row.get("vehicle_type")
        if vehicle_type not in catalogue.VEHICLE_TYPES:
            errors.append(
                f"{where}: vehicle_type {vehicle_type!r} is not a runtime type"
            )
            continue
        source = row.get("source")
        locator = row.get("source_locator")
        if not isinstance(source, str) or not source.strip():
            errors.append(f"{where}: source must name the real-mass source")
            continue
        if not isinstance(locator, str) or not locator.strip():
            errors.append(f"{where}: source_locator must name the real-mass locator")
            continue
        mass = _number(row.get("real_mass_kg"))
        if mass is None or mass <= 0:
            errors.append(f"{where}: real_mass_kg must be a positive number")
            continue
        basis = row.get("mass_basis")
        mass_field = CENSUS_MASS_FIELDS.get(basis) if isinstance(basis, str) else None
        if mass_field is None:
            errors.append(
                f"{where}: mass_basis {basis!r} is not one of "
                f"{sorted(CENSUS_MASS_FIELDS)}"
            )
            continue
        dimensions: list[float] = []
        bad_geometry = False
        for field in GEOMETRY_FIELDS:
            value = _number(row.get(field))
            if value is None or value <= 0:
                errors.append(f"{where}: {field} must be a positive number")
                bad_geometry = True
                break
            dimensions.append(value)
        if bad_geometry:
            continue
        values: dict[str, object] = {
            field: _census_held(value, "mm", source, locator)
            for field, value in zip(GEOMETRY_FIELDS, dimensions, strict=True)
        }
        values[mass_field] = _census_held(mass, "kg", source, locator)
        entries.append(
            catalogue.CatalogueEntry(
                catalogue_id=ident,
                canonical_name="",
                maker="",
                model="",
                variant="",
                variant_id="",
                vehicle_type=vehicle_type,
                class_token=token,
                country="",
                era="",
                aliases=(),
                keywords=(),
                runtime_ready=False,
                values=values,
                source_file=CALIBRATION_NAME,
            )
        )
    return CalibrationLoad(entries, errors)


def model_errors(model: Model) -> list[str]:
    """Return every structural error in the model. An empty list is valid."""
    errors: list[str] = []
    if model.get("schema") != MODEL_SCHEMA:
        errors.append(f"schema must be {MODEL_SCHEMA}")

    density = _mapping(model.get("material_density"))
    if density is None or not density:
        errors.append("material_density must be a non-empty object")
        density = {}
    for key, raw in density.items():
        entry = _mapping(raw)
        if entry is None:
            errors.append(f"material_density.{key} must be an object")
            continue
        low = _number(entry.get("low"))
        high = _number(entry.get("high"))
        if low is None or high is None or low <= 0 or high <= low:
            errors.append(f"material_density.{key} needs 0 < low < high")
        if not entry.get("source") or not entry.get("locator"):
            errors.append(f"material_density.{key} needs a source and a locator")

    classes = model.get("mass_classes")
    if not isinstance(classes, list) or not classes:
        errors.append("mass_classes must be a non-empty array")
    else:
        for index, raw in enumerate(classes):
            entry = _mapping(raw)
            if entry is None:
                errors.append(f"mass_classes[{index}] must be an object")
                continue
            where = f"mass_classes[{index}]"
            if not entry.get("key"):
                errors.append(f"{where} needs a key")
            if entry.get("match") not in ("token", "vehicle_type", "default"):
                errors.append(f"{where} match must be token, vehicle_type or default")
            density_class = entry.get("density_class")
            if density_class not in density:
                errors.append(f"{where} density_class {density_class!r} is undefined")
            fill_low = _number(entry.get("fill_low"))
            fill_high = _number(entry.get("fill_high"))
            if fill_low is None or fill_high is None:
                errors.append(f"{where} fill_low and fill_high must be numbers")
            elif fill_low < 0 or fill_high < fill_low:
                errors.append(f"{where} needs 0 <= fill_low <= fill_high")

    bands = _mapping(model.get("geometry_bands"))
    if bands is None:
        errors.append("geometry_bands must be an object")

    calibration = _mapping(model.get("calibration"))
    if calibration is None:
        errors.append("calibration must be an object")
    elif not isinstance(calibration.get("approved"), bool):
        errors.append("calibration.approved must be true or false")
    return errors


def resolve_mass_class(model: Model, entry: catalogue.CatalogueEntry) -> Model | None:
    """Return the first mass class that matches the entry.

    The order is the class order: a token match, then a vehicle-type match,
    then the default. An empty class token never claims a token class.
    """
    classes = model.get("mass_classes")
    if not isinstance(classes, list):
        return None
    token = catalogue.normalise(entry.class_token)
    resolved: list[Model] = []
    for raw in classes:
        entry_class = _mapping(raw)
        if entry_class is not None:
            resolved.append(entry_class)
    if token:
        for entry_class in resolved:
            if entry_class.get("match") != "token":
                continue
            key = catalogue.normalise(str(entry_class.get("key", "")))
            if key == token:
                return entry_class
    for entry_class in resolved:
        if entry_class.get("match") == "vehicle_type":
            if entry_class.get("key") == entry.vehicle_type:
                return entry_class
    for entry_class in resolved:
        if entry_class.get("match") == "default":
            return entry_class
    return None


def documented_mass(entry: catalogue.CatalogueEntry) -> tuple[str, float] | None:
    """Return the first complete held weight, or None.

    The fields are tried in the fixed order operating, curb, gross. The first
    complete held value wins. The gate never averages two source values.
    """
    for field in MASS_FIELDS:
        held = catalogue.held_value(entry.values, field)
        if held is None:
            continue
        value = _number(held.get("value"))
        if value is not None and value > 0:
            return field, value
    return None


def geometry_dimensions(entry: catalogue.CatalogueEntry) -> list[float] | None:
    """Return the three held dimensions in millimetres, or None."""
    dimensions: list[float] = []
    for field in GEOMETRY_FIELDS:
        held = catalogue.held_value(entry.values, field)
        if held is None:
            return None
        value = _number(held.get("value"))
        if value is None:
            return None
        dimensions.append(value)
    return dimensions


def entry_volume_m3(entry: catalogue.CatalogueEntry) -> float | None:
    """Return the box volume in cubic metres, or None for a degenerate box."""
    dimensions = geometry_dimensions(entry)
    if dimensions is None:
        return None
    volume = dimensions[0] * dimensions[1] * dimensions[2] / MM3_PER_M3
    return volume if volume > 0 else None


def skip_reason(entry: catalogue.CatalogueEntry) -> str | None:
    """Return why an entry cannot calibrate the model, or None."""
    if documented_mass(entry) is None:
        return "no complete held weight"
    dimensions = geometry_dimensions(entry)
    if dimensions is None:
        return "missing length_mm, width_mm or height_mm"
    if not all(value > 0 for value in dimensions):
        return "non-positive dimension (zero volume)"
    return None


@dataclass(frozen=True)
class ClassMetric:
    """One mass class after evaluation or calibration."""

    key: str
    n: int
    fill_low: float
    fill_high: float
    rho_low: float
    rho_high: float

    def width_ratio(self) -> float:
        """Return high over low for the class, or infinity when low is zero."""
        low = self.fill_low * self.rho_low
        if low <= 0:
            return math.inf
        return (self.fill_high * self.rho_high) / low


@dataclass(frozen=True)
class Metrics:
    """The gate metrics for one model state."""

    n_entries: int
    in_band: int
    fraction_in_band: float
    mdape: float
    classes: tuple[ClassMetric, ...]


@dataclass(frozen=True)
class Proposal:
    """One calibration proposal for a mass class with at least one entry."""

    key: str
    n: int
    f_lo_raw: float
    f_hi_raw: float
    fill_low: float
    fill_high: float

    def width_ratio(self, rho_low: float, rho_high: float) -> float:
        low = self.fill_low * rho_low
        if low <= 0:
            return math.inf
        return (self.fill_high * rho_high) / low


@dataclass(frozen=True)
class _Row:
    key: str
    mass: float
    volume: float
    rho_low: float
    rho_high: float
    low: float
    high: float
    in_band: bool
    ape: float


def _class_metrics(model: Model, rows: list[_Row]) -> tuple[ClassMetric, ...]:
    density = _mapping(model.get("material_density")) or {}
    classes = model.get("mass_classes")
    metrics: list[ClassMetric] = []
    if not isinstance(classes, list):
        return ()
    for raw in classes:
        entry_class = _mapping(raw)
        if entry_class is None:
            continue
        key = str(entry_class.get("key", ""))
        density_class = str(entry_class.get("density_class", ""))
        rho = _mapping(density.get(density_class)) or {}
        rho_low = _number(rho.get("low")) or 0.0
        rho_high = _number(rho.get("high")) or 0.0
        fill_low = _number(entry_class.get("fill_low")) or 0.0
        fill_high = _number(entry_class.get("fill_high")) or 0.0
        n = sum(1 for row in rows if row.key == key)
        metrics.append(ClassMetric(key, n, fill_low, fill_high, rho_low, rho_high))
    return tuple(metrics)


def evaluate(model: Model, entries: Sequence[catalogue.CatalogueEntry]) -> Metrics:
    """Compute the gate metrics from the model and the held catalogue values."""
    density = _mapping(model.get("material_density")) or {}
    rows: list[_Row] = []
    for entry in entries:
        if skip_reason(entry) is not None:
            continue
        mass = documented_mass(entry)
        volume = entry_volume_m3(entry)
        entry_class = resolve_mass_class(model, entry)
        if mass is None or volume is None or entry_class is None:
            continue
        rho = _mapping(density.get(str(entry_class.get("density_class", ""))))
        if rho is None:
            continue
        rho_low = _number(rho.get("low")) or 0.0
        rho_high = _number(rho.get("high")) or 0.0
        fill_low = _number(entry_class.get("fill_low")) or 0.0
        fill_high = _number(entry_class.get("fill_high")) or 0.0
        low = volume * fill_low * rho_low
        high = volume * fill_high * rho_high
        in_band = low <= mass[1] <= high
        if low > 0 and high > 0:
            centre = math.sqrt(low * high)
            ape = abs(centre - mass[1]) / mass[1]
        else:
            ape = 1.0
        rows.append(
            _Row(
                key=str(entry_class.get("key", "")),
                mass=mass[1],
                volume=volume,
                rho_low=rho_low,
                rho_high=rho_high,
                low=low,
                high=high,
                in_band=in_band,
                ape=ape,
            )
        )
    n_entries = len(rows)
    in_band = sum(1 for row in rows if row.in_band)
    fraction = in_band / n_entries if n_entries else 0.0
    mdape = statistics.median(row.ape for row in rows) if rows else math.inf
    return Metrics(n_entries, in_band, fraction, mdape, _class_metrics(model, rows))


def approval_failures(model: Model, metrics: Metrics) -> list[str]:
    """Return the approval failures. An unapproved model has no failures."""
    calibration = _mapping(model.get("calibration")) or {}
    if calibration.get("approved") is not True:
        return []
    bands = _mapping(model.get("geometry_bands")) or {}
    max_width = _number(bands.get("max_width_ratio")) or DEFAULT_MAX_WIDTH_RATIO
    failures: list[str] = []
    if metrics.n_entries < MIN_ENTRIES:
        failures.append(
            f"n_entries {metrics.n_entries} is below the minimum {MIN_ENTRIES}"
        )
    if metrics.fraction_in_band < MIN_FRACTION_IN_BAND:
        failures.append(
            f"fraction_in_band {metrics.fraction_in_band:.4f} is below "
            f"{MIN_FRACTION_IN_BAND}"
        )
    if metrics.mdape > MAX_MDAPE:
        failures.append(f"mdape {metrics.mdape:.4f} is above the maximum {MAX_MDAPE}")
    for class_metric in metrics.classes:
        if class_metric.n < WIDTH_CLASS_MIN:
            continue
        ratio = class_metric.width_ratio()
        if ratio > max_width:
            failures.append(
                f"class {class_metric.key} width_ratio {ratio:.4f} is above {max_width}"
            )
    return failures


def _fit_fills(
    rows: Sequence[tuple[float, float, float, float]],
) -> tuple[float, float, float, float]:
    """Return (f_lo_raw, f_hi_raw, fill_low, fill_high) for one group of rows.

    ``f_lo_raw = min(mass/(volume*rho_high))`` and
    ``f_hi_raw = max(mass/(volume*rho_low))``. Each is widened by the flat
    small-sample margin and rounded to four decimals.
    """
    f_lo_raw = min(mass / (volume * rho_high) for mass, volume, _, rho_high in rows)
    f_hi_raw = max(mass / (volume * rho_low) for mass, volume, rho_low, _ in rows)
    return (
        f_lo_raw,
        f_hi_raw,
        round(f_lo_raw * (1.0 - CALIBRATION_MARGIN), FILL_ROUND),
        round(f_hi_raw * (1.0 + CALIBRATION_MARGIN), FILL_ROUND),
    )


def _prepared_rows(
    model: Model, entries: Sequence[catalogue.CatalogueEntry]
) -> list[tuple[catalogue.CatalogueEntry, str, float, float, float, float]]:
    """Return (entry, resolved key, mass, volume, rho_low, rho_high) tuples."""
    density = _mapping(model.get("material_density")) or {}
    prepared: list[
        tuple[catalogue.CatalogueEntry, str, float, float, float, float]
    ] = []
    for entry in entries:
        if skip_reason(entry) is not None:
            continue
        mass = documented_mass(entry)
        volume = entry_volume_m3(entry)
        entry_class = resolve_mass_class(model, entry)
        if mass is None or volume is None or entry_class is None:
            continue
        rho = _mapping(density.get(str(entry_class.get("density_class", ""))))
        if rho is None:
            continue
        rho_low = _number(rho.get("low")) or 0.0
        rho_high = _number(rho.get("high")) or 0.0
        if rho_low <= 0 or rho_high <= 0:
            continue
        prepared.append(
            (entry, str(entry_class.get("key", "")), mass[1], volume, rho_low, rho_high)
        )
    return prepared


def leave_one_out(model: Model, entries: Sequence[catalogue.CatalogueEntry]) -> Metrics:
    """Score the census out of sample.

    Each row is held out of its own fill. The fill is refit from the other
    rows of the same class token. A token with no sibling falls back to the
    vehicle-type pool, then to the committed fill. The class metrics still
    read the committed fills, because the width cap applies to the model.
    """
    prepared = _prepared_rows(model, entries)
    rows: list[_Row] = []
    for entry, key, mass, volume, rho_low, rho_high in prepared:
        siblings = [
            item for item in prepared if item[1] == key and item[0] is not entry
        ]
        if not siblings:
            siblings = [
                item
                for item in prepared
                if item[0].vehicle_type == entry.vehicle_type and item[0] is not entry
            ]
        if siblings:
            _, _, fill_low, fill_high = _fit_fills(
                [(item[2], item[3], item[4], item[5]) for item in siblings]
            )
        else:
            entry_class = resolve_mass_class(model, entry)
            fill_low = (
                _number(entry_class.get("fill_low")) or 0.0 if entry_class else 0.0
            )
            fill_high = (
                _number(entry_class.get("fill_high")) or 0.0 if entry_class else 0.0
            )
        low = volume * fill_low * rho_low
        high = volume * fill_high * rho_high
        in_band = low <= mass <= high
        if low > 0 and high > 0:
            centre = math.sqrt(low * high)
            ape = abs(centre - mass) / mass
        else:
            ape = 1.0
        rows.append(_Row(key, mass, volume, rho_low, rho_high, low, high, in_band, ape))
    n_entries = len(rows)
    in_band = sum(1 for row in rows if row.in_band)
    fraction = in_band / n_entries if n_entries else 0.0
    mdape = statistics.median(row.ape for row in rows) if rows else math.inf
    return Metrics(n_entries, in_band, fraction, mdape, _class_metrics(model, rows))


def calibrate(
    model: Model, entries: Sequence[catalogue.CatalogueEntry]
) -> tuple[list[Proposal], Metrics]:
    """Derive the fill proposals and the leave-one-out metrics they produce.

    A token row is fitted from the rows that resolve to it. A vehicle-type row
    is fitted from every row of that type, pooled. Each group widens by the
    flat small-sample margin and rounds to four decimals.
    """
    density = _mapping(model.get("material_density")) or {}
    type_classes: dict[str, Model] = {}
    classes = model.get("mass_classes")
    if isinstance(classes, list):
        for raw in classes:
            entry_class = _mapping(raw)
            if entry_class is not None and entry_class.get("match") == "vehicle_type":
                type_classes[str(entry_class.get("key", ""))] = entry_class

    grouped: dict[str, list[tuple[float, float, float, float]]] = {}
    pooled: dict[str, list[tuple[float, float, float, float]]] = {}
    for entry, key, mass, volume, rho_low, rho_high in _prepared_rows(model, entries):
        grouped.setdefault(key, []).append((mass, volume, rho_low, rho_high))
        type_class = type_classes.get(entry.vehicle_type)
        if type_class is not None:
            rho = _mapping(density.get(str(type_class.get("density_class", ""))))
            if rho is not None:
                type_low = _number(rho.get("low")) or 0.0
                type_high = _number(rho.get("high")) or 0.0
                if type_low > 0 and type_high > 0:
                    pooled.setdefault(entry.vehicle_type, []).append(
                        (mass, volume, type_low, type_high)
                    )

    proposals: list[Proposal] = []
    proposed_keys: set[str] = set()
    for key, rows in grouped.items():
        f_lo_raw, f_hi_raw, fill_low, fill_high = _fit_fills(rows)
        proposals.append(
            Proposal(key, len(rows), f_lo_raw, f_hi_raw, fill_low, fill_high)
        )
        proposed_keys.add(key)
    for key, rows in pooled.items():
        if key in proposed_keys:
            continue
        f_lo_raw, f_hi_raw, fill_low, fill_high = _fit_fills(rows)
        proposals.append(
            Proposal(key, len(rows), f_lo_raw, f_hi_raw, fill_low, fill_high)
        )

    proposed_model = _with_fills(model, proposals)
    return proposals, leave_one_out(proposed_model, entries)


def _with_fills(model: Model, proposals: Sequence[Proposal]) -> Model:
    """Return a shallow copy of the model with the proposed fills applied."""
    fills = {proposal.key: proposal for proposal in proposals}
    copy = dict(model)
    classes = model.get("mass_classes")
    if isinstance(classes, list):
        updated: list[Any] = []
        for raw in classes:
            entry = _mapping(raw)
            if entry is None:
                updated.append(raw)
                continue
            proposal = fills.get(str(entry.get("key", "")))
            if proposal is None:
                updated.append(dict(entry))
                continue
            entry = dict(entry)
            entry["fill_low"] = proposal.fill_low
            entry["fill_high"] = proposal.fill_high
            entry["n"] = proposal.n
            updated.append(entry)
        copy["mass_classes"] = updated
    return copy


def apply_proposals(
    model: Model, proposals: Sequence[Proposal], metrics: Metrics
) -> Model:
    """Apply the proposals and the calibration block, never approving."""
    updated = json.loads(json.dumps(model))
    if not isinstance(updated, dict):
        raise ValueError("model must be a JSON object")
    result: Model = {str(key): value for key, value in updated.items()}
    proposed = _with_fills(result, proposals)
    calibration = _mapping(proposed.get("calibration"))
    if calibration is None:
        calibration = {}
    calibration["n_entries"] = metrics.n_entries
    calibration["mdape"] = round(metrics.mdape, METRIC_ROUND)
    calibration["fraction_in_band"] = round(metrics.fraction_in_band, METRIC_ROUND)
    proposed["calibration"] = calibration
    return proposed


def format_report(
    data_dir: Path,
    model: Model,
    metrics: Metrics,
    proposals: Sequence[Proposal],
    entries: Sequence[catalogue.CatalogueEntry],
) -> str:
    """Render the calibration report as deterministic text."""
    skipped: Counter[str] = Counter(
        reason for reason in map(skip_reason, entries) if reason is not None
    )
    lines = [
        "vehicle mass model calibration report",
        f"schema: {model.get('schema', '')}",
        f"data dir: {data_dir}",
        f"entries considered: {metrics.n_entries}",
        "entries skipped:",
    ]
    if skipped:
        for reason, count in sorted(skipped.items()):
            lines.append(f"  {reason}: {count}")
    else:
        lines.append("  none")
    lines.append(f"fraction_in_band: {metrics.fraction_in_band:.4f}")
    lines.append(f"mdape: {metrics.mdape:.4f}")
    lines.append("mass classes with entries:")
    for class_metric in metrics.classes:
        if class_metric.n == 0:
            continue
        lines.append(
            f"  {class_metric.key}: n={class_metric.n} "
            f"fill_low={class_metric.fill_low:.4f} "
            f"fill_high={class_metric.fill_high:.4f} "
            f"width_ratio={class_metric.width_ratio():.4f}"
        )
    lines.append("proposed fills:")
    for proposal in proposals:
        lines.append(
            f"  {proposal.key}: n={proposal.n} "
            f"f_lo_raw={proposal.f_lo_raw:.6f} "
            f"f_hi_raw={proposal.f_hi_raw:.6f} "
            f"fill_low={proposal.fill_low:.4f} "
            f"fill_high={proposal.fill_high:.4f}"
        )
    lines.append("approved stays false until a human sets it")
    return "\n".join(lines) + "\n"


def write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------
# Self-check fixtures. These build a private corpus in a temporary directory.
# --------------------------------------------------------------------------


def _held(value: float) -> dict[str, object]:
    return {
        "value": value,
        "unit": "mm" if value > 100 else "kg",
        "source": "self-check fixture",
        "locator": "self-check fixture",
        "state": "self-check fixture",
        "grade": "documented",
    }


def _self_entry(
    catalogue_id: str,
    *,
    length_mm: float | None,
    width_mm: float | None,
    height_mm: float | None,
    mass_field: str = "curb_weight_kg",
    mass: float | None = None,
    gross: float | None = None,
    vehicle_type: str = "wheeled",
) -> catalogue.CatalogueEntry:
    values: dict[str, object] = {}
    for field, value in (
        ("length_mm", length_mm),
        ("width_mm", width_mm),
        ("height_mm", height_mm),
    ):
        if value is not None:
            values[field] = _held(value)
    if mass is not None:
        values[mass_field] = _held(mass)
    if gross is not None:
        values["gross_weight_kg"] = _held(gross)
    return catalogue.CatalogueEntry(
        catalogue_id=catalogue_id,
        canonical_name="",
        maker="",
        model="",
        variant="",
        variant_id="",
        vehicle_type=vehicle_type,
        class_token="",
        country="",
        era="",
        aliases=(),
        keywords=(),
        runtime_ready=False,
        values=values,
        source_file="self-check",
    )


def _self_model() -> Model:
    return {
        "schema": MODEL_SCHEMA,
        "material_density": {
            "metal": {
                "low": 1000,
                "high": 2000,
                "unit": "kg/m3",
                "source": "self-check",
                "locator": "self-check",
            }
        },
        "mass_classes": [
            {
                "key": "wheeled",
                "match": "vehicle_type",
                "vehicle_type": "wheeled",
                "density_class": "metal",
                "fill_low": 0.0,
                "fill_high": 0.0,
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
        "power_to_weight": {"enabled": False, "unit": "enginePower/tonne", "bands": {}},
        "calibration": {
            "approved": False,
            "n_entries": 0,
            "mdape": None,
            "fraction_in_band": None,
            "report": "calibration-report.txt",
        },
    }


def self_check() -> list[str]:
    """Exercise the gate on fixtures in a private temporary corpus."""
    failures: list[str] = []
    entries = [
        _self_entry(
            "fix_a",
            length_mm=1000,
            width_mm=1000,
            height_mm=1000,
            mass=100.0,
        ),
        _self_entry(
            "fix_b",
            length_mm=1000,
            width_mm=1000,
            height_mm=2000,
            mass=150.0,
        ),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        model_path = Path(tmp) / MODEL_NAME
        model = _self_model()
        model_path.write_text(json.dumps(model), encoding="utf-8")
        loaded = load_model(model_path)
        if model_errors(loaded):
            return ["self-check model is malformed: " + "; ".join(model_errors(loaded))]

        metrics = evaluate(loaded, entries)
        if metrics.n_entries != 2:
            failures.append(f"self-check n_entries {metrics.n_entries} != 2")
        if metrics.fraction_in_band != 0.0:
            failures.append("self-check zero-fill fraction_in_band was not 0")

        proposals, calibrated = calibrate(loaded, entries)
        proposal = {item.key: item for item in proposals}
        if "wheeled" not in proposal:
            failures.append("self-check calibration produced no wheeled proposal")
        else:
            wheeled = proposal["wheeled"]
            if abs(wheeled.f_lo_raw - 0.0375) > 1e-9:
                failures.append(f"self-check f_lo_raw {wheeled.f_lo_raw} != 0.0375")
            if abs(wheeled.f_hi_raw - 0.1) > 1e-9:
                failures.append(f"self-check f_hi_raw {wheeled.f_hi_raw} != 0.1")
            if abs(wheeled.fill_low - 0.0319) > 1e-9:
                failures.append(f"self-check fill_low {wheeled.fill_low} != 0.0319")
            if abs(wheeled.fill_high - 0.115) > 1e-9:
                failures.append(f"self-check fill_high {wheeled.fill_high} != 0.115")
        if calibrated.fraction_in_band != 1.0:
            failures.append(
                "self-check calibrated fraction_in_band "
                f"{calibrated.fraction_in_band} != 1.0"
            )
        wheeled_metric = next(
            (item for item in calibrated.classes if item.key == "wheeled"), None
        )
        if wheeled_metric is None or abs(wheeled_metric.width_ratio() - 7.2100) > 0.01:
            failures.append("self-check calibrated width_ratio was not 7.21")

        updated = apply_proposals(loaded, proposals, calibrated)
        updated_calibration = updated.get("calibration")
        if not isinstance(updated_calibration, dict):
            failures.append("self-check apply_proposals lost the calibration block")
        elif updated_calibration.get("approved") is not False:
            failures.append("self-check apply_proposals changed the approved flag")
        updated_classes = updated.get("mass_classes")
        if isinstance(updated_classes, list) and updated_classes:
            first = updated_classes[0]
            if isinstance(first, dict) and first.get("fill_high") != 0.115:
                failures.append("self-check apply_proposals did not write fill_high")

        # Zero volume and missing geometry are skipped, never scored.
        bad = [
            _self_entry(
                "fix_zero",
                length_mm=0,
                width_mm=1000,
                height_mm=1000,
                mass=100.0,
            ),
            _self_entry(
                "fix_missing",
                length_mm=None,
                width_mm=1000,
                height_mm=1000,
                mass=100.0,
            ),
        ]
        if skip_reason(bad[0]) != "non-positive dimension (zero volume)":
            failures.append("self-check zero volume was not skipped")
        if skip_reason(bad[1]) != "missing length_mm, width_mm or height_mm":
            failures.append("self-check missing geometry was not skipped")
        if evaluate(loaded, bad).n_entries != 0:
            failures.append("self-check a degenerate entry reached the metrics")

        # A complete held value at one field is chosen by order, never averaged.
        both = _self_entry(
            "fix_conflict",
            length_mm=1000,
            width_mm=1000,
            height_mm=1000,
            mass_field="curb_weight_kg",
            mass=100.0,
            gross=200.0,
        )
        picked = documented_mass(both)
        if picked != ("curb_weight_kg", 100.0):
            failures.append(f"self-check documented_mass picked {picked}, not curb 100")

        # The approval thresholds bite only when approved is true.
        if approval_failures(loaded, metrics):
            failures.append("self-check an unapproved model produced failures")
        strict = _self_model()
        strict_calibration = strict.get("calibration")
        if isinstance(strict_calibration, dict):
            strict_calibration["approved"] = True
        strict_failures = approval_failures(strict, metrics)
        if not any("fraction_in_band" in item for item in strict_failures):
            failures.append("self-check zero-fill approval did not fail in-band")
        if not any("mdape" in item for item in strict_failures):
            failures.append("self-check zero-fill approval did not fail mdape")
    return failures


def _parse_args(argv: Sequence[str]) -> tuple[Path, str, Path | None]:
    data_dir = DEFAULT_DATA
    report: Path | None = None
    modes: list[str] = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--data-dir":
            index += 1
            if index >= len(argv):
                raise SystemExit("--data-dir needs a path")
            data_dir = Path(argv[index])
        elif arg == "--report":
            index += 1
            if index >= len(argv):
                raise SystemExit("--report needs a path")
            report = Path(argv[index])
        elif arg in ("--calibrate", "--write", "--self-check"):
            modes.append(arg[2:])
        elif arg in ("-h", "--help"):
            print(
                "usage: validate_vehicle_mass_model.py "
                "[--data-dir PATH] [--calibrate | --write | --self-check] "
                "[--report PATH]"
            )
            raise SystemExit(0)
        else:
            raise SystemExit(f"unknown argument: {arg}")
        index += 1
    if len(modes) > 1:
        raise SystemExit("choose only one of --calibrate, --write, --self-check")
    mode = modes[0] if modes else "gate"
    return data_dir, mode, report


def _print_metrics(metrics: Metrics) -> None:
    print(f"  n_entries: {metrics.n_entries}")
    print(f"  in_band: {metrics.in_band}")
    print(f"  fraction_in_band: {metrics.fraction_in_band:.4f}")
    print(f"  mdape: {metrics.mdape:.4f}")
    for class_metric in metrics.classes:
        if class_metric.n == 0:
            continue
        try:
            ratio = f"{class_metric.width_ratio():.4f}"
        except OverflowError:
            ratio = "inf"
        print(f"  class {class_metric.key}: n={class_metric.n} width_ratio={ratio}")


def _catalogue_cross_check(model: Model, data_dir: Path) -> None:
    """Print the catalogue coverage for provenance only. It never fails the gate."""
    load = catalogue.load(data_dir)
    if load.errors:
        print("  catalogue cross-check: skipped (the catalogue did not load cleanly)")
        return
    metrics = evaluate(model, load.entries)
    print(
        "  catalogue cross-check (report only): the catalogue holds real "
        "overall-dimension boxes, so its basis differs from the census by construction"
    )
    print(
        f"    n_entries {metrics.n_entries} "
        f"fraction_in_band {metrics.fraction_in_band:.4f} "
        f"mdape {metrics.mdape:.4f}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    data_dir, mode, report = _parse_args(sys.argv[1:] if argv is None else argv)

    if mode == "self-check":
        failures = self_check()
        if failures:
            print("vehicle mass model gate: FAIL")
            for failure in failures:
                print(f"  {failure}")
            return 1
        print("vehicle mass model gate: PASS (self-check)")
        return 0

    model_path = data_dir / MODEL_NAME
    try:
        model = load_model(model_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"vehicle mass model gate: FAIL\n  cannot read {model_path}: {exc}")
        return 1

    errors = model_errors(model)
    if errors:
        print("vehicle mass model gate: FAIL (malformed model)")
        for error in errors:
            print(f"  {error}")
        return 1

    load = load_calibration(data_dir / CALIBRATION_NAME)
    if load.errors:
        print("vehicle mass model gate: FAIL (census)")
        for error in load.errors:
            print(f"  {error}")
        return 1

    if mode in ("calibrate", "write"):
        proposals, metrics = calibrate(model, load.entries)
        if mode == "calibrate":
            report_path = report
            if report_path is None:
                calibration = _mapping(model.get("calibration")) or {}
                report_path = ROOT / str(
                    calibration.get("report", "calibration-report.txt")
                )
            write_report(
                report_path,
                format_report(data_dir, model, metrics, proposals, load.entries),
            )
            print(f"vehicle mass model calibration: wrote {report_path}")
            _print_metrics(metrics)
            for proposal in proposals:
                print(
                    f"  propose {proposal.key}: fill_low={proposal.fill_low:.4f} "
                    f"fill_high={proposal.fill_high:.4f}"
                )
            return 0
        updated = apply_proposals(model, proposals, metrics)
        model_path.write_text(
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"vehicle mass model: wrote {model_path}")
        _print_metrics(metrics)
        return 0

    metrics = evaluate(model, load.entries)
    failures = approval_failures(model, metrics)
    calibration = _mapping(model.get("calibration")) or {}
    approved = calibration.get("approved") is True
    if failures:
        print(f"vehicle mass model gate: FAIL (approved {approved})")
        _print_metrics(metrics)
        for failure in failures:
            print(f"  {failure}")
        return 1
    print(f"vehicle mass model gate: PASS (approved {approved})")
    _print_metrics(metrics)
    out_of_sample = leave_one_out(model, load.entries)
    print(
        "  leave_one_out (recorded in the calibration block): "
        f"coverage {out_of_sample.fraction_in_band:.4f} "
        f"mdape {out_of_sample.mdape:.4f}"
    )
    _catalogue_cross_check(model, data_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
