#!/usr/bin/env python3
"""Validate the NATO/OPFOR symbology category tables.

Checks:

  1. Schema.  Every section is present and every row has a name, a category,
     a grade and a source.
  2. Category set.  Every category is one of the APP-6(C) class categories.
     A corrupt category fails the run.
  3. Coverage.  Every shipped Arma 3 marker family prefix and the exact
     marker names are present, and every enumerated marker suffix is present.
  4. Freshness.  The generated addons/optics/data/symbology_tables.sqf equals
     a fresh render, so a hand-edited table fails the run.
  5. Kernel agreement.  The pure kernel aee_optics_fnc_symbolCategory maps the
     shipped marker types to the expected categories.

Run:  python3 tools/validation/validate_symbology.py
Exit 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
SOURCE_JSON = ROOT / "data" / "symbology" / "symbology_tables.json"
TABLES_SQF = ROOT / "addons" / "optics" / "data" / "symbology_tables.sqf"
KERNEL = (
    ROOT / "addons" / "optics" / "functions" / "symbology" / "fnc_symbolCategory.sqf"
)

sys.path.insert(0, str(ROOT / "tools" / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "validation"))
from gen_symbology_tables import render_tables  # noqa: E402
from sqf_lite import run_sqf  # noqa: E402

SECTIONS = ("prefixes", "suffixes", "exact", "classes")
GRADES = ("sourced", "derived", "UNSOURCED")

# The shipped Arma 3 CfgMarkers families and the exact marker names.
REQUIRED_PREFIXES = (
    "b_",
    "o_",
    "n_",
    "c_",
    "hd_",
    "flag_",
    "Contact_",
    "GroundSupport_",
    "group_",
    "loc_",
)
REQUIRED_EXACT = ("Empty", "EmptyIcon", "Flag", "KIA")
REQUIRED_SUFFIXES = (
    "inf",
    "armor",
    "mech_inf",
    "motor_inf",
    "art",
    "air",
    "plane",
    "heli",
    "naval",
    "installation",
    "hq",
    "med",
    "recon",
    "support",
    "unknown",
    "dot",
)

# The mapping the kernel must produce for the shipped marker types.
KERNEL_EXPECTED = {
    "b_inf": "infantry",
    "o_armor": "armour",
    "n_inf": "infantry",
    "c_air": "rotary",
    "hd_dot": "waypoint",
    "group_3": "unknown",
    "flag_NATO": "unknown",
    "GroundSupport_CAS_WEST": "support",
}


def load() -> dict:
    return json.loads(SOURCE_JSON.read_text(encoding="utf-8"))


def check_schema(source: dict, errors: list[str]) -> None:
    for section in SECTIONS:
        rows = source.get(section)
        if not isinstance(rows, list) or not rows:
            errors.append(f"symbology_tables.json: section {section} is missing")
            continue
        for row in rows:
            if not isinstance(row, dict) or not row.get("name"):
                errors.append(f"{section}: a row has no name")
                continue
            if not row.get("category"):
                errors.append(f"{section}: {row.get('name')} has no category")
            if row.get("grade") not in GRADES:
                errors.append(
                    f"{section}: {row.get('name')} grade {row.get('grade')!r} "
                    f"is not sourced, derived or UNSOURCED"
                )
            if not row.get("source"):
                errors.append(f"{section}: {row.get('name')} has no source")


def check_categories(source: dict, errors: list[str]) -> None:
    allowed = set(source.get("categories", []))
    if not allowed:
        errors.append("symbology_tables.json: no category list")
        return
    for section in SECTIONS:
        for row in source.get(section, []):
            category = row.get("category")
            if category not in allowed:
                errors.append(
                    f"{section}: {row.get('name')} category {category!r} is "
                    f"not an APP-6(C) class category"
                )


def check_coverage(source: dict, errors: list[str]) -> None:
    prefixes = {row.get("name") for row in source.get("prefixes", [])}
    for name in REQUIRED_PREFIXES:
        if name not in prefixes:
            errors.append(f"the shipped prefix {name!r} is not covered")
    exact = {row.get("name") for row in source.get("exact", [])}
    for name in REQUIRED_EXACT:
        if name not in exact:
            errors.append(f"the exact marker {name!r} is not covered")
    suffixes = {row.get("name") for row in source.get("suffixes", [])}
    for name in REQUIRED_SUFFIXES:
        if name not in suffixes:
            errors.append(f"the marker suffix {name!r} is not covered")


def check_freshness(source: dict, errors: list[str]) -> None:
    if not TABLES_SQF.is_file():
        errors.append("addons/optics/data/symbology_tables.sqf is missing")
        return
    if TABLES_SQF.read_text(encoding="utf-8") != render_tables(source):
        errors.append(
            "addons/optics/data/symbology_tables.sqf is stale; run the generator"
        )


def check_kernel(source: dict, errors: list[str]) -> None:
    if not KERNEL.is_file():
        errors.append("fnc_symbolCategory.sqf is missing")
        return
    tables = run_sqf(TABLES_SQF, [])
    for marker_type, expected in KERNEL_EXPECTED.items():
        got = run_sqf(
            KERNEL, [marker_type, "marker"], {"aee_optics_symbologyTables": tables}
        )
        if got != expected:
            errors.append(
                f"kernel maps {marker_type!r} to {got!r}, expected {expected!r}"
            )


def main() -> int:
    source = load()
    errors: list[str] = []
    check_schema(source, errors)
    check_categories(source, errors)
    check_coverage(source, errors)
    check_freshness(source, errors)
    check_kernel(source, errors)

    if errors:
        print(f"symbology validation: FAIL ({len(errors)})")
        for error in errors:
            print(f"  {error}")
        return 1
    rows = sum(len(source[section]) for section in SECTIONS)
    print(
        f"symbology validation: PASS ({rows} rows, "
        f"{len(REQUIRED_PREFIXES)} shipped prefixes, kernel agreement)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
