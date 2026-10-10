#!/usr/bin/env python3
"""Validate the AEE dynamic variation-family declaration.

Checks:

  1. Schema.  The declaration carries the schema string
     aee.symbology.variation_families/1.
  2. Families.  Every family has a non-empty entry, markerClass, resolver and
     options list.
  3. Sources.  Every option source is one of the five known value sets.
  4. Tables.  Every option names a non-empty table it derives from.
  5. Entry.  Every family entry is not a concrete catalogue class.

Run:  python3 tools/validation/validate_variation.py
Exit 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
SOURCE_JSON = ROOT / "data" / "symbology" / "variation_families.json"

SCHEMA = "aee.symbology.variation_families/1"

# The five value sets the generator derives.  An option source must be one.
KNOWN_SOURCES = ("families", "dimensions", "glyphs", "echelons", "palette")

# The generated concrete marker headers.  A family entry must not name one of
# their classes, because the entry is the option-driven family class.
CONCRETE_HEADERS = (
    "config_markers.hpp",
    "config_crossproduct.hpp",
    "config_taxonomy.hpp",
    "config_modifiers.hpp",
    "config_family.hpp",
)
CLASS_RE = re.compile(r"^\s*class\s+(AEE_\w+)", re.MULTILINE)


def load() -> dict:
    return json.loads(SOURCE_JSON.read_text(encoding="utf-8"))


def concrete_classes() -> set[str]:
    """Every concrete AEE class emitted by the generated marker headers."""
    names: set[str] = set()
    for header in CONCRETE_HEADERS:
        path = ROOT / "addons" / "symbology" / header
        if path.is_file():
            names.update(CLASS_RE.findall(path.read_text(encoding="utf-8")))
    return names


def check_schema(source: dict, errors: list[str]) -> None:
    if source.get("schema") != SCHEMA:
        errors.append(f"schema {source.get('schema')!r} is not {SCHEMA!r}")


def check_families(source: dict, errors: list[str]) -> None:
    families = source.get("families")
    if not isinstance(families, list) or not families:
        errors.append("variation_families.json: no families")
        return
    for family in families:
        fid = family.get("id") or "?"
        for field in ("id", "label", "entry", "markerClass", "resolver"):
            if not family.get(field):
                errors.append(f"family {fid!r} has no {field}")
        options = family.get("options")
        if not isinstance(options, list) or not options:
            errors.append(f"family {fid!r} has no options")
            continue
        seen: set[str] = set()
        for option in options:
            oid = option.get("id") or "?"
            if not option.get("id"):
                errors.append(f"family {fid!r}: an option has no id")
            if not option.get("label"):
                errors.append(f"family {fid!r}: option {oid!r} has no label")
            if option.get("source") not in KNOWN_SOURCES:
                errors.append(
                    f"family {fid!r}: option {oid!r} source "
                    f"{option.get('source')!r} is not a known value set"
                )
            if not option.get("table"):
                errors.append(f"family {fid!r}: option {oid!r} has no table")
            if option.get("grade") not in ("sourced", "derived", "UNSOURCED"):
                errors.append(
                    f"family {fid!r}: option {oid!r} grade "
                    f"{option.get('grade')!r} is not sourced, derived or UNSOURCED"
                )
            if oid in seen:
                errors.append(f"family {fid!r}: option {oid!r} is duplicated")
            seen.add(oid)


def check_entry(source: dict, errors: list[str]) -> None:
    concrete = concrete_classes()
    if not concrete:
        errors.append("no generated marker headers found; run the generators")
    for family in source.get("families", []):
        entry = family.get("entry")
        if entry and entry in concrete:
            errors.append(
                f"family {family.get('id')!r} entry {entry!r} is a concrete "
                f"catalogue class"
            )


def main() -> int:
    source = load()
    errors: list[str] = []
    check_schema(source, errors)
    check_families(source, errors)
    check_entry(source, errors)

    if errors:
        print(f"variation validation: FAIL ({len(errors)})")
        for error in errors:
            print(f"  {error}")
        return 1

    families = source["families"]
    options = sum(len(family["options"]) for family in families)
    print(
        f"variation validation: PASS ({len(families)} families, "
        f"{options} options, schema {SCHEMA})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
