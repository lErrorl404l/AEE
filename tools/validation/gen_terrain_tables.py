#!/usr/bin/env python3
"""Generate the AEE terrain and map-feature symbol tables.

The tables map an Arma 3 location class (CfgLocationTypes) and an Arma 3
object icon class (RscMapControl) to a terrain symbol id, a category, a
dimension and the standard colour.  The validated source is
data/symbology/terrain_symbols.json.  This generator reads it and writes the
runtime projection

  addons/optics/data/terrain_symbols.sqf

which the kernel reads as aee_optics_terrainTables.

The order is fixed, so the output is byte-stable.  The `--check` mode writes
nothing and returns 1 when the on-disk file differs from a fresh render.

Run:  python3 tools/validation/gen_terrain_tables.py
      python3 tools/validation/gen_terrain_tables.py --check
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]
SOURCE_JSON = ROOT / "data" / "symbology" / "terrain_symbols.json"
TABLES_OUT = ROOT / "addons" / "optics" / "data" / "terrain_symbols.sqf"

SECTIONS = ("symbols", "locations", "objects")

TABLES_TEMPLATE = """/*
Terrain and map-feature symbol tables (generated).

This file is GENERATED. The generator tools/validation/gen_terrain_tables.py
writes it from the validated source data/symbology/terrain_symbols.json. Do
not edit it by hand. Edit the source and regenerate it.

The authority is STANAG 3675, succeeded by the DGIWG Symbol Register (the
DTM50 product), with the US Army FM 21-31 and the USGS Topographic Map
Symbols sheet as the public-domain fallback. AEE draws the standard geometry
itself.

The three sections are, in order:

  0  terrain symbol id -> [id, category, dimension, colour, section, grade, source]
  1  location class     -> [class, symbol, category, colour, size, font, shadow, grade, source]
  2  object icon class  -> [class, symbol, category, colour, size, importance, grade, source]

A location or object row whose symbol is "" carries a colour only and no icon.
No value is invented: every row is sourced or derived and carries its source.
*/
[
__SECTIONS__
]
"""

SYMBOL_FIELDS = ("id", "category", "dimension", "colour", "section", "grade", "source")
LOCATION_FIELDS = (
    "class",
    "symbol",
    "category",
    "colour",
    "size",
    "font",
    "textSize",
    "shadow",
    "grade",
    "source",
)
OBJECT_FIELDS = (
    "class",
    "symbol",
    "category",
    "colour",
    "size",
    "importance",
    "grade",
    "source",
)


def _sqf(value: Any) -> str:
    """Render one SQF literal. A string is quoted with doubled quotes."""
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace('"', '""') + '"'
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_sqf(item) for item in value) + "]"
    return str(value)


def _row(entry: dict[str, Any], fields: tuple[str, ...]) -> list[Any]:
    return [_sqf(entry.get(field)) for field in fields]


def render_tables(source: dict[str, Any]) -> str:
    fields = {
        "symbols": SYMBOL_FIELDS,
        "locations": LOCATION_FIELDS,
        "objects": OBJECT_FIELDS,
    }
    blocks = []
    for section in SECTIONS:
        rendered = ",\n".join(
            "        " + "[" + ", ".join(_row(entry, fields[section])) + "]"
            for entry in source[section]
        )
        blocks.append("    [\n" + rendered + "\n    ]")
    return TABLES_TEMPLATE.replace("__SECTIONS__", ",\n".join(blocks))


def load_source() -> dict[str, Any]:
    return json.loads(SOURCE_JSON.read_text(encoding="utf-8"))


def write_output() -> int:
    source = load_source()
    TABLES_OUT.parent.mkdir(parents=True, exist_ok=True)
    TABLES_OUT.write_text(render_tables(source), encoding="utf-8")
    return sum(len(source[section]) for section in SECTIONS)


def check_output() -> int:
    """Return 0 when the generated file matches a fresh render."""
    source = load_source()
    expected = render_tables(source)
    if not TABLES_OUT.is_file():
        print(f"terrain tables: {TABLES_OUT} is missing; run the generator")
        return 1
    if TABLES_OUT.read_text(encoding="utf-8") != expected:
        print(f"terrain tables: {TABLES_OUT} is stale; run the generator")
        return 1
    count = sum(len(source[section]) for section in SECTIONS)
    print(f"terrain tables: {count} rows -> {TABLES_OUT.name} (fresh)")
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check_output()
    count = write_output()
    print(f"terrain tables: {count} rows, wrote {TABLES_OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
