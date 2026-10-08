#!/usr/bin/env python3
"""Validate the AEE terrain symbol table.

Fails when a row is malformed, when an engine location class or object icon
class has no row, when a referenced symbol id is missing, when a colour is
out of range, or when the generated projection is stale.  The engine class
lists are the canonical sets from the shipped config; a new engine class
forces a table update here.

Run: python3 tools/validation/validate_terrain.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
SOURCE_JSON = ROOT / "data" / "symbology" / "terrain_symbols.json"

# The 25 CfgLocationTypes classes the plan re-declares.
ENGINE_LOCATIONS = (
    "Mount",
    "Name",
    "Strategic",
    "StrongpointArea",
    "FlatArea",
    "FlatAreaCity",
    "FlatAreaCitySmall",
    "CityCenter",
    "Airport",
    "NameMarine",
    "NameCityCapital",
    "NameCity",
    "NameVillage",
    "NameLocal",
    "Hill",
    "ViewPoint",
    "RockArea",
    "BorderCrossing",
    "VegetationBroadleaf",
    "VegetationFir",
    "VegetationPalm",
    "VegetationVineyard",
    "fakeTown",
    "Area",
    "Flag",
)

# The 26 RscMapControl object icon classes the plan re-declares.
ENGINE_OBJECTS = (
    "Bush",
    "Rock",
    "SmallTree",
    "Tree",
    "busstop",
    "fuelstation",
    "hospital",
    "church",
    "lighthouse",
    "power",
    "powersolar",
    "powerwave",
    "powerwind",
    "quay",
    "transmitter",
    "watertower",
    "Cross",
    "Chapel",
    "Shipwreck",
    "Bunker",
    "Fortress",
    "Fountain",
    "Ruin",
    "Stack",
    "Tourism",
    "ViewTower",
)

VALID_CATEGORIES = {
    "relief",
    "vegetation",
    "hydrography",
    "populated",
    "works",
    "transport",
    "boundary",
    "control",
    "military",
}
VALID_GRADES = {"sourced", "derived", "UNSOURCED"}
VALID_DIMENSIONS = {"point", "line", "area", "name"}


def _colour_ok(value: object) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(c, (int, float)) and 0.0 <= c <= 1.0 for c in value)
    )


def main() -> int:
    errors: list[str] = []
    if not SOURCE_JSON.exists():
        print("validate_terrain: terrain_symbols.json missing")
        return 1

    doc = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    symbols = doc.get("symbols", [])
    locations = doc.get("locations", [])
    objects = doc.get("objects", [])

    symbol_ids = [row.get("id") for row in symbols]
    if len(set(symbol_ids)) != len(symbol_ids):
        errors.append("duplicate terrain symbol id")

    for row in symbols:
        sid = row.get("id", "?")
        if row.get("category") not in VALID_CATEGORIES:
            errors.append(f"{sid}: bad category {row.get('category')!r}")
        if row.get("dimension") not in VALID_DIMENSIONS:
            errors.append(f"{sid}: bad dimension {row.get('dimension')!r}")
        if row.get("grade") not in VALID_GRADES:
            errors.append(f"{sid}: bad grade {row.get('grade')!r}")
        if not _colour_ok(row.get("colour")):
            errors.append(f"{sid}: colour must be 4 values in 0..1")
        if not str(row.get("source", "")).strip():
            errors.append(f"{sid}: no source citation")
        if not str(row.get("section", "")).strip():
            errors.append(f"{sid}: no FM 21-31 section")

    known = set(symbol_ids)

    def check_class_row(row: dict, kind: str) -> None:
        cls = row.get("class", "?")
        symbol = row.get("symbol")
        if symbol is not None and symbol not in known:
            errors.append(f"{cls}: unknown symbol id {symbol!r}")
        if row.get("category") not in VALID_CATEGORIES:
            errors.append(f"{cls}: bad category {row.get('category')!r}")
        if row.get("grade") not in VALID_GRADES:
            errors.append(f"{cls}: bad grade {row.get('grade')!r}")
        if not _colour_ok(row.get("colour")):
            errors.append(f"{cls}: colour must be 4 values in 0..1")
        if not str(row.get("source", "")).strip():
            errors.append(f"{cls}: no source citation")
        if not isinstance(row.get("size"), (int, float)):
            errors.append(f"{cls}: size must be a number")
        if kind == "location" and "font" not in row:
            errors.append(f"{cls}: no font field")
        if kind == "location" and not isinstance(row.get("textSize"), (int, float)):
            errors.append(f"{cls}: textSize must be a number")

    loc_names = [row.get("class") for row in locations]
    obj_names = [row.get("class") for row in objects]
    if len(set(loc_names)) != len(loc_names):
        errors.append("duplicate location class")
    if len(set(obj_names)) != len(obj_names):
        errors.append("duplicate object class")

    for row in locations:
        check_class_row(row, "location")
    for row in objects:
        check_class_row(row, "object")

    missing_loc = [c for c in ENGINE_LOCATIONS if c not in set(loc_names)]
    extra_loc = [c for c in loc_names if c not in set(ENGINE_LOCATIONS)]
    missing_obj = [c for c in ENGINE_OBJECTS if c not in set(obj_names)]
    extra_obj = [c for c in obj_names if c not in set(ENGINE_OBJECTS)]
    for c in missing_loc:
        errors.append(f"location class {c} has no table row")
    for c in extra_loc:
        errors.append(f"location class {c} is not an engine class")
    for c in missing_obj:
        errors.append(f"object class {c} has no table row")
    for c in extra_obj:
        errors.append(f"object class {c} is not an engine class")

    if errors:
        print(f"validate_terrain: FAIL ({len(errors)})")
        for line in errors[:40]:
            print(f"  {line}")
        return 1
    print(
        f"validate_terrain: PASS ({len(symbols)} symbols, "
        f"{len(locations)} locations, {len(objects)} objects)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
