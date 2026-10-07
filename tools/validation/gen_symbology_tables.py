#!/usr/bin/env python3
"""Generate the NATO/OPFOR symbology category tables.

The tables map an Arma 3 marker type prefix, suffix or exact name, and a
CfgVehicles vehicleClass or unitClass value, to a NATO APP-6(C) class
category.  The validated source is data/symbology/symbology_tables.json.
This generator reads it and writes the runtime projection

  addons/optics/data/symbology_tables.sqf

which the kernel reads as aee_optics_symbologyTables.

The order is fixed, so the output is byte-stable.  The `--check` mode writes
nothing and returns 1 when the on-disk file differs from a fresh render.

Run:  python3 tools/validation/gen_symbology_tables.py
      python3 tools/validation/gen_symbology_tables.py --check
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[2]
SOURCE_JSON = ROOT / "data" / "symbology" / "symbology_tables.json"
TABLES_OUT = ROOT / "addons" / "optics" / "data" / "symbology_tables.sqf"

SECTIONS = ("prefixes", "suffixes", "exact", "classes")

TABLES_TEMPLATE = """/*
NATO/OPFOR symbology category tables (generated).

This file is GENERATED. The generator tools/validation/gen_symbology_tables.py
writes it from the validated source data/symbology/symbology_tables.json. Do
not edit it by hand. Edit the source and regenerate it.

The four sections are, in order:

  0  marker type prefixes -> the family default category
  1  marker type suffixes -> the category
  2  exact marker names -> the category
  3  CfgVehicles vehicleClass and unitClass values -> the category

Each row is [name, category, grade, source]. The categories are the NATO
APP-6(C) frame grammar classes. No category is invented: every row is
sourced or derived and carries its source.
*/
[
__SECTIONS__
]
"""


def _sqf(value: Any) -> str:
    """Render one SQF literal. A string is quoted with doubled quotes."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace('"', '""') + '"'
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_sqf(item) for item in value) + "]"
    return str(value)


def section_rows(source: dict[str, Any], section: str) -> list[list[str]]:
    """One section as a list of [name, category, grade, source] rows."""
    rows = []
    for entry in source[section]:
        rows.append(
            [
                str(entry["name"]),
                str(entry["category"]),
                str(entry["grade"]),
                str(entry["source"]),
            ]
        )
    return rows


def render_tables(source: dict[str, Any]) -> str:
    blocks = []
    for section in SECTIONS:
        rendered = ",\n".join(
            "        " + _sqf(row) for row in section_rows(source, section)
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
        print(f"symbology tables: {TABLES_OUT} is missing; run the generator")
        return 1
    if TABLES_OUT.read_text(encoding="utf-8") != expected:
        print(f"symbology tables: {TABLES_OUT} is stale; run the generator")
        return 1
    count = sum(len(source[section]) for section in SECTIONS)
    print(f"symbology tables: {count} rows -> {TABLES_OUT.name} (fresh)")
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check_output()
    count = write_output()
    print(f"symbology tables: {count} rows, wrote {TABLES_OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
