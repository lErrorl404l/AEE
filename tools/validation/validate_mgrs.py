#!/usr/bin/env python3
"""Validate the MGRS letter tables, the grade, and the world anchors.

Six checks:

  1. Schema.  Every table component is present with the fields the
     generator reads, and every component carries a source grade.
  2. No invented letter.  The band letters, the column sets and the row
     letters are exactly the published sets; the band and row sequences
     omit I and O; the offset is the AA even-zone offset.
  3. Zone strings and digits.  "01" to "60", and the ten digits.
  4. World coverage.  Every world in data/mgrs/geo_sources.json has an
     anchor row.
  5. Anchor agreement.  Each anchor equals the real pure builder
     aee_core_fnc_buildGeoAnchor run through tools/tests/sqf_lite.py, so
     the Python resolution is proven against the shipped kernel.
  6. Source registry.  Every source id the table names is registered in
     data/mgrs/sources.json.

Run:  python3 tools/validation/validate_mgrs.py
Exit 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]
DATA = ROOT / "data" / "mgrs"
TABLES_JSON = DATA / "mgrs_tables.json"
GEO_JSON = DATA / "geo_sources.json"
SOURCES_JSON = DATA / "sources.json"
BUILDER = ROOT / "addons" / "lib" / "functions" / "geo" / "fnc_buildGeoAnchor.sqf"

sys.path.insert(0, str(ROOT / "tools" / "tests"))
from sqf_lite import run_sqf  # noqa: E402

# The published lettering, from DMA TM 8358.1 and the NGA MGRS guidance.
BAND_LETTERS = list("CDEFGHJKLMNPQRSTUVWX")
COLUMN_SETS = [list("ABCDEFGH"), list("JKLMNPQR"), list("STUVWXYZ")]
ROW_LETTERS = list("ABCDEFGHJKLMNPQRSTUV")
EVEN_ZONE_ROW_OFFSET = 5
ZONE_STRINGS = [f"{zone:02d}" for zone in range(1, 61)]
DIGIT_CHARACTERS = list("0123456789")

COMPONENTS = (
    "band_letters",
    "column_sets",
    "row_letters",
    "even_zone_row_offset",
    "zone_strings",
    "digit_characters",
)


def load() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    tables = json.loads(TABLES_JSON.read_text(encoding="utf-8"))
    geo = json.loads(GEO_JSON.read_text(encoding="utf-8"))
    sources = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))
    return tables, geo, sources


def check_schema(tables: dict[str, Any], errors: list[str]) -> None:
    components = tables.get("tables")
    if not isinstance(components, dict):
        errors.append("mgrs_tables.json: missing the tables object")
        return
    for name in COMPONENTS:
        entry = components.get(name)
        if not isinstance(entry, dict):
            errors.append(f"mgrs_tables.json: component {name} is missing")
            continue
        grade = entry.get("grade")
        if not isinstance(grade, str) or not grade:
            errors.append(f"mgrs_tables.json: component {name} has no grade")
        if not entry.get("note"):
            errors.append(f"mgrs_tables.json: component {name} has no note")


def check_letters(tables: dict[str, Any], errors: list[str]) -> None:
    components = tables.get("tables", {})
    if not isinstance(components, dict):
        return
    band = components.get("band_letters", {}).get("letters")
    if band != BAND_LETTERS:
        errors.append("band letters are not the published C..X sequence")
    columns = components.get("column_sets", {}).get("sets")
    if columns != COLUMN_SETS:
        errors.append("column sets are not the published A-H / J-R / S-Z sets")
    rows = components.get("row_letters", {}).get("letters")
    if rows != ROW_LETTERS:
        errors.append("row letters are not the published A..V sequence")
    offset = components.get("even_zone_row_offset", {}).get("value")
    if offset != EVEN_ZONE_ROW_OFFSET:
        errors.append("even-zone row offset is not the AA offset of 5")
    # I and O are never used in the band or the row letters.
    for name, sequence in (("band letters", band), ("row letters", rows)):
        if isinstance(sequence, list) and any(
            letter in ("I", "O") for letter in sequence
        ):
            errors.append(f"{name} contain I or O, which are omitted")


def check_zone_and_digits(tables: dict[str, Any], errors: list[str]) -> None:
    components = tables.get("tables", {})
    if not isinstance(components, dict):
        return
    zones = components.get("zone_strings", {}).get("strings")
    if zones != ZONE_STRINGS:
        errors.append('zone strings are not "01" to "60"')
    digits = components.get("digit_characters", {}).get("characters")
    if digits != DIGIT_CHARACTERS:
        errors.append("digit characters are not 0 to 9")


def check_worlds(geo: dict[str, Any], errors: list[str]) -> None:
    worlds = geo.get("worlds")
    if not isinstance(worlds, list) or not worlds:
        errors.append("geo_sources.json: no world list")
        return
    for world in worlds:
        name = world.get("world", "?")
        anchor = world.get("anchor")
        if not isinstance(anchor, list) or len(anchor) != 9:
            errors.append(f"{name}: no 9-element anchor row")
            continue
        if anchor[8] not in ("mapArea", "cfgworlds"):
            errors.append(f"{name}: anchor source token {anchor[8]!r} is invalid")


def check_anchor_agreement(geo: dict[str, Any], errors: list[str]) -> None:
    """Prove each anchor equals the shipped pure builder."""
    for world in geo.get("worlds", []):
        name = world.get("world", "?")
        expected = world.get("anchor")
        built = run_sqf(
            BUILDER,
            [
                world.get("mapSize", 0),
                world.get("mapZone", 0),
                list(world.get("mapArea", [])),
                world.get("latitude", 0),
                world.get("longitude", 0),
            ],
        )
        if len(built) != 9 or expected is None:
            errors.append(f"{name}: builder did not return a 9-element anchor")
            continue
        for index, (got, want) in enumerate(zip(built[:8], expected[:8])):
            if abs(got - want) > 1e-9:
                errors.append(
                    f"{name}: anchor element {index} differs from the builder "
                    f"({got!r} != {want!r})"
                )
        if built[8] != expected[8]:
            errors.append(
                f"{name}: anchor source token differs from the builder "
                f"({built[8]!r} != {expected[8]!r})"
            )


def check_sources(
    tables: dict[str, Any], sources: dict[str, Any], errors: list[str]
) -> None:
    registered = {
        entry.get("source_id") for entry in sources if isinstance(entry, dict)
    }
    for source_id in tables.get("sources", []):
        if source_id not in registered:
            errors.append(f"source {source_id} is not registered in sources.json")


def main() -> int:
    tables, geo, sources = load()
    if not isinstance(sources, list):
        print("mgrs validation: sources.json must be a top-level array")
        return 1
    errors: list[str] = []
    check_schema(tables, errors)
    check_letters(tables, errors)
    check_zone_and_digits(tables, errors)
    check_worlds(geo, errors)
    check_anchor_agreement(geo, errors)
    check_sources(tables, sources, errors)

    if errors:
        print(f"mgrs validation: FAIL ({len(errors)})")
        for error in errors:
            print(f"  {error}")
        return 1
    print(
        f"mgrs validation: PASS (tables, letters, zones, digits, "
        f"{len(geo.get('worlds', []))} world anchors, sources)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
