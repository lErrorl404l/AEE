#!/usr/bin/env python3
"""Derive the AEE supported vehicle class inventory from the addon code.

The inventory is identity evidence only. It records the class tokens the
addon code already branches on. It does not describe the engine class tree.
It does not hold a real-world vehicle value.

The tool reads every *.sqf and *.hpp file under a root (default addons/).
It collects class tokens from two bounded SQF constructs:

  1. an isKindOf "TOKEN" literal;
  2. a class-table row ["TOKEN", spec] inside a file that branches on the
     table with isKindOf (_x select 0).

It also records a vehicle class list used with nearEntities as a query
reference. The tool strips comments before a match, so a token in prose is
not a token in code.

An `engine_base` token is one the code asserts with isKindOf. A `mod_token`
is one the code adds only as a curated table or query token. A ground token
is one that has a class-table row with a positive value. A class-table row
with a zero value marks a non-ground token, as the source does for a
rotorcraft.

Run:  python3 tools/validation/gen_vehicle_class_inventory.py
Writes data/vehicle/classes.json. The output is sorted and deterministic.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import TypedDict

REPO = Path(__file__).parents[2]
DEFAULT_ROOT = REPO / "addons"
DEFAULT_OUT = REPO / "data" / "vehicle" / "classes.json"
SCHEMA = "aee.vehicle.class_inventory/1"


class TokenRefs(TypedDict):
    """The code references to one token."""

    kindof: list[str]
    table: list[tuple[str, str]]
    query: list[str]


class TokenEntry(TypedDict):
    """One row of the inventory."""

    token: str
    kind: str
    is_ground: bool
    provenance: list[str]
    exclusion_reason: str | None


class Inventory(TypedDict):
    """The inventory payload."""

    schema: str
    tokens: list[TokenEntry]


# An isKindOf literal. The token starts with a letter or an underscore.
ISKINDOF_RE = re.compile(r'isKindOf\s+"([A-Za-z_][A-Za-z0-9_]*)"')
# A branch on a class table. Only a file with this branch has a table.
TABLE_BRANCH = "isKindOf (_x select 0)"
# A class-table row. The token starts with a capital letter. The spec is a
# number or a bracketed list. A selection name such as "hull" is not a row.
TABLE_ROW_RE = re.compile(
    r'\["([A-Z][A-Za-z0-9_]*)"\s*,\s*(\[[^\]]*\]|-?[0-9][0-9.]*)\]'
)
# A class list for a nearEntities query.
QUERY_RE = re.compile(r"nearEntities\s*\[\s*\[([^\]]*)\]")
QUOTED_RE = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"')


def strip_comments(text: str) -> str:
    """Return the text with comments removed. Newlines stay in place.

    A // or /* inside a string is not a comment. An SQF string escapes a
    quote by doubling it.
    """
    out: list[str] = []
    index = 0
    length = len(text)
    in_string = False
    in_block = False
    while index < length:
        char = text[index]
        next_char = text[index + 1] if index + 1 < length else ""
        if in_block:
            if char == "*" and next_char == "/":
                in_block = False
                out.append("  ")
                index += 2
                continue
            out.append("\n" if char == "\n" else " ")
            index += 1
            continue
        if in_string:
            out.append(char)
            if char == '"':
                if next_char == '"':
                    out.append(next_char)
                    index += 2
                    continue
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            while index < length and text[index] != "\n":
                out.append(" ")
                index += 1
            continue
        if char == "/" and next_char == "*":
            in_block = True
            out.append("  ")
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _source_files(root: Path) -> list[Path]:
    """Return every *.sqf and *.hpp file under root, in a fixed order."""
    files = [path for pattern in ("*.sqf", "*.hpp") for path in root.rglob(pattern)]
    return sorted(files, key=lambda path: path.as_posix())


def _is_ground(specs: list[str]) -> bool:
    """A positive class-table row makes the token a ground vehicle."""
    for spec in specs:
        text = spec.strip()
        if text.startswith("["):
            if text[1:-1].strip():
                return True
        else:
            try:
                if float(text) > 0:
                    return True
            except ValueError:
                continue
    return False


def _has_zero_row(specs: list[str]) -> bool:
    for spec in specs:
        text = spec.strip()
        if not text.startswith("["):
            try:
                if float(text) == 0:
                    return True
            except ValueError:
                continue
    return False


def collect(root: Path) -> dict[str, TokenRefs]:
    """Return token -> references found under root.

    Each reference holds the kindof and query locations and the table rows
    as (location, spec) pairs.
    """
    refs: dict[str, TokenRefs] = {}

    def entry(token: str) -> TokenRefs:
        return refs.setdefault(token, {"kindof": [], "table": [], "query": []})

    for path in _source_files(root):
        location_prefix = f"{root.name}/{path.relative_to(root).as_posix()}"
        text = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        has_table = TABLE_BRANCH in text
        for number, line in enumerate(text.splitlines(), start=1):
            location = f"{location_prefix}:{number}"
            for match in ISKINDOF_RE.finditer(line):
                entry(match.group(1))["kindof"].append(location)
            if has_table:
                for match in TABLE_ROW_RE.finditer(line):
                    entry(match.group(1))["table"].append((location, match.group(2)))
            for match in QUERY_RE.finditer(line):
                for token in QUOTED_RE.findall(match.group(1)):
                    entry(token)["query"].append(location)
    return refs


def build_inventory(root: Path) -> Inventory:
    """Return the sorted inventory payload for root."""
    refs = collect(root)
    tokens: list[TokenEntry] = []
    for token in sorted(refs):
        ref = refs[token]
        specs = [spec for _location, spec in ref["table"]]
        ground = _is_ground(specs)
        if ground:
            reason: str | None = None
        elif _has_zero_row(specs):
            reason = "class-table row marks the token non-ground (zero value)"
        else:
            reason = "no positive ground class-table row"
        provenance = sorted(
            set(ref["kindof"])
            | {location for location, _spec in ref["table"]}
            | set(ref["query"])
        )
        tokens.append(
            {
                "token": token,
                "kind": "engine_base" if ref["kindof"] else "mod_token",
                "is_ground": ground,
                "provenance": provenance,
                "exclusion_reason": reason,
            }
        )
    return {"schema": SCHEMA, "tokens": tokens}


def write_inventory(root: Path, out: Path) -> Inventory:
    """Write the inventory payload for root to out. Return the payload."""
    payload = build_inventory(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def render_inventory(payload: Inventory) -> str:
    """Return the exact on-disk text for a payload."""
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def check_inventory(root: Path, out: Path) -> int:
    """Return 0 when the committed inventory matches a fresh build.

    Check mode writes nothing. A missing or stale file returns 1, so a
    stale generated inventory fails the gate.
    """
    payload = build_inventory(root)
    if not out.is_file():
        print(f"vehicle class inventory: {out} is missing; run the generator")
        return 1
    if out.read_text(encoding="utf-8") != render_inventory(payload):
        print(f"vehicle class inventory: {out} is stale; run the generator")
        return 1
    ground = sum(1 for token in payload["tokens"] if token["is_ground"])
    print(
        f"vehicle class inventory: {len(payload['tokens'])} tokens, "
        f"{ground} ground -> {out} (fresh)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive the vehicle class inventory.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed inventory is fresh. Write nothing.",
    )
    args = parser.parse_args(argv)
    if args.check:
        return check_inventory(args.root, args.out)
    payload = write_inventory(args.root, args.out)
    ground = sum(1 for token in payload["tokens"] if token["is_ground"])
    print(
        f"vehicle class inventory: {len(payload['tokens'])} tokens, "
        f"{ground} ground -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
