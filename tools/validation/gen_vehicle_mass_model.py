#!/usr/bin/env python3
"""Generate the runtime vehicle mass model parameter table.

The model artefact ``data/vehicle/mass_model.json`` holds cited material
density ranges, calibrated fill ranges, geometry bands and a power block.
This generator renders that artefact into one SQF parameter table:

  addons/mobility/functions/fnc_getVehicleMassModel.sqf

The generated file is a data table. It reads no engine state, defines no
extra function, and carries no value that is absent from the model
artefact. Prose fields (a note, a source, a locator, a reason) stay in the
artefact and are not rendered.

Run:  python3 tools/validation/gen_vehicle_mass_model.py
      python3 tools/validation/gen_vehicle_mass_model.py --check
Exit: 0 when the table is written or fresh. 1 when ``--check`` finds a
      missing or stale table. 2 when the model artefact breaks the schema.
Check mode writes nothing.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

ROOT = Path(__file__).parents[2]
DEFAULT_MODEL = ROOT / "data" / "vehicle" / "mass_model.json"
DEFAULT_OUT = ROOT / "addons" / "mobility" / "functions" / "fnc_getVehicleMassModel.sqf"

SCHEMA = "aee.vehicle.mass_model/1"
DEFAULT_MATCH = "default"

HEADER = """#include "..\\script_component.hpp"
/*
Vehicle mass model parameter table.

Function: aee_mobility_fnc_getVehicleMassModel.

This file is GENERATED. The generator tools/validation/gen_vehicle_mass_model.py
writes it from the model artefact data/vehicle/mass_model.json. Do not edit it
by hand. Edit the model and regenerate it.

The table holds modelled parameters only. It reads no engine state, it
defines no extra function, and it holds no real-world vehicle value. The
estimate is unavailable while the approved flag is false.

Return Value: ARRAY, five blocks in this order:
  0 approved       BOOL. True only after calibration and approval pass.
  1 densityTable   ARRAY of [className, lowKgM3, highKgM3], one row per
                   classifier class.
  2 massClasses    ARRAY of [key, matchKind, vehicleType, densityClass,
                   fillLow, fillHigh], in match order, default last.
  3 geometryBands  ARRAY [minExtentM, maxExtentM, maxWidthRatio].
  4 powerBlock     ARRAY [enabled, unit, hardFactor, bands].

Public: No
*/

__TABLE__
"""


class ModelError(ValueError):
    """The model artefact does not satisfy the generator contract."""


def _is_number(value: object) -> bool:
    """A JSON number, and not a boolean (a bool is an int subclass)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ModelError(f"{label} must be an object")
    return {str(key): item for key, item in value.items()}


def _sequence(value: object, label: str) -> list[object]:
    if not isinstance(value, list) or not value:
        raise ModelError(f"{label} must be a non-empty array")
    return value


def _text(value: object, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not allow_empty):
        raise ModelError(f"{label} must be a string")
    return value


def _number(value: object, label: str) -> float:
    if not _is_number(value):
        raise ModelError(f"{label} must be a number")
    number = float(cast(float, value))
    if not math.isfinite(number):
        raise ModelError(f"{label} must be finite")
    return number


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ModelError(f"{label} must be a boolean")
    return value


def load_model(path: Path = DEFAULT_MODEL) -> dict[str, object]:
    """Read the model artefact and reject a broken top level."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ModelError(f"cannot read {path}: {exc}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ModelError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ModelError(f"{path} must hold a JSON object")
    return {str(key): item for key, item in payload.items()}


def build_table(payload: dict[str, object]) -> list[object]:
    """Validate the model artefact and return the five-block parameter table.

    Every value in the table comes from the artefact. A field that is absent,
    mistyped, inverted or unresolved refuses the render.
    """
    if payload.get("schema") != SCHEMA:
        raise ModelError(f"schema must be {SCHEMA}")

    density_in = _mapping(payload.get("material_density"), "material_density")
    density_table: list[object] = []
    for name, raw in density_in.items():
        block = _mapping(raw, f"material_density.{name}")
        low = _number(block.get("low"), f"material_density.{name}.low")
        high = _number(block.get("high"), f"material_density.{name}.high")
        _text(block.get("unit"), f"material_density.{name}.unit")
        if low >= high:
            raise ModelError(f"material_density.{name} low must be below high")
        density_table.append([name, block["low"], block["high"]])

    class_rows = _sequence(payload.get("mass_classes"), "mass_classes")
    class_table: list[object] = []
    default_seen = 0
    for index, raw in enumerate(class_rows):
        row = _mapping(raw, f"mass_classes[{index}]")
        key = _text(row.get("key"), f"mass_classes[{index}].key")
        match = _text(row.get("match"), f"mass_classes[{index}].match")
        vehicle_type = _text(
            row.get("vehicle_type"),
            f"mass_classes[{index}].vehicle_type",
            allow_empty=True,
        )
        density_class = _text(
            row.get("density_class"), f"mass_classes[{index}].density_class"
        )
        if density_class not in density_in:
            raise ModelError(
                f"mass_classes[{index}].density_class {density_class} "
                "is not a material_density key"
            )
        fill_low = _number(row.get("fill_low"), f"mass_classes[{index}].fill_low")
        fill_high = _number(row.get("fill_high"), f"mass_classes[{index}].fill_high")
        if fill_low > fill_high:
            raise ModelError(
                f"mass_classes[{index}] fill_low must not exceed fill_high"
            )
        if match == DEFAULT_MATCH:
            default_seen += 1
            if index != len(class_rows) - 1:
                raise ModelError("the default mass class must be the last row")
        class_table.append(
            [key, match, vehicle_type, density_class, row["fill_low"], row["fill_high"]]
        )
    if default_seen != 1:
        raise ModelError("mass_classes must hold exactly one default row")

    geometry = _mapping(payload.get("geometry_bands"), "geometry_bands")
    min_extent = _number(geometry.get("min_extent_m"), "geometry_bands.min_extent_m")
    max_extent = _number(geometry.get("max_extent_m"), "geometry_bands.max_extent_m")
    width_ratio = _number(
        geometry.get("max_width_ratio"), "geometry_bands.max_width_ratio"
    )
    if min_extent >= max_extent:
        raise ModelError("geometry_bands min extent must be below max extent")
    if width_ratio <= 0:
        raise ModelError("geometry_bands.max_width_ratio must be positive")
    geometry_bands: list[object] = [
        geometry["min_extent_m"],
        geometry["max_extent_m"],
        geometry["max_width_ratio"],
    ]

    power = _mapping(payload.get("power_to_weight"), "power_to_weight")
    enabled = _boolean(power.get("enabled"), "power_to_weight.enabled")
    unit = _text(power.get("unit"), "power_to_weight.unit")
    hard_factor = _number(power.get("hard_factor"), "power_to_weight.hard_factor")
    _mapping(power.get("bands"), "power_to_weight.bands")
    power_block: list[object] = [enabled, unit, hard_factor, power["bands"]]

    calibration = _mapping(payload.get("calibration"), "calibration")
    approved = _boolean(calibration.get("approved"), "calibration.approved")

    return [approved, density_table, class_table, geometry_bands, power_block]


def _sqf(value: object) -> str:
    """Render one value as a single-line SQF literal."""
    if value is None:
        return "[]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace('"', '""') + '"'
    if _is_number(value):
        return _format_number(cast(float, value))
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_sqf(item) for item in value) + "]"
    if isinstance(value, dict):
        pairs = ", ".join(f"[{_sqf(key)}, {_sqf(item)}]" for key, item in value.items())
        return "[" + pairs + "]"
    raise ModelError(f"cannot render a {type(value).__name__} as an SQF literal")


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value)}.0"
    return repr(float(value))


def _render(value: object, level: int = 0) -> str:
    """Render a table as an indented SQF literal."""
    pad = "    " * level
    if isinstance(value, (list, tuple)):
        if not value:
            return "[]"
        inner = ",\n".join(f"{pad}    {_render(item, level + 1)}" for item in value)
        return "[\n" + inner + "\n" + pad + "]"
    return _sqf(value)


def render_table(table: list[object]) -> str:
    """Render the full generated file for one parameter table."""
    return HEADER.replace("__TABLE__", _render(table))


def check_output(out: Path, text: str) -> int:
    """Return 0 when the committed file matches the render, else 1. Writes nothing."""
    if not out.is_file():
        print(
            f"vehicle mass model: {out} is missing; run the generator", file=sys.stderr
        )
        return 1
    if out.read_text(encoding="utf-8") != text:
        print(f"vehicle mass model: {out} is stale; run the generator", file=sys.stderr)
        return 1
    print(f"vehicle mass model: {out} (fresh)")
    return 0


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Render the vehicle mass model parameter table."
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed table is fresh. Write nothing.",
    )
    args = parser.parse_args(argv)

    try:
        payload = load_model(args.model)
        table = build_table(payload)
    except ModelError as exc:
        print(f"vehicle mass model: {exc}", file=sys.stderr)
        return 2

    text = render_table(table)
    if args.check:
        return check_output(args.out, text)

    args.out.write_text(text, encoding="utf-8")
    density_count = len(cast(list[object], table[1]))
    class_count = len(cast(list[object], table[2]))
    print(
        f"vehicle mass model: {density_count} density classes, "
        f"{class_count} mass classes -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
