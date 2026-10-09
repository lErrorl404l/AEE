#!/usr/bin/env python3
"""Generate the AEE terrain symbol catalogue.

The catalogue is a map legend for the AEE terrain and map-feature symbols.  It
is data driven.  The authority is the DGIWG Symbol Register concept index
(data/symbology/dgiwg_concepts.json), which publishes which concepts each
SO_#### symbol depicts.  Every catalogue row states the register concept the
feature needs, the SO_#### the register publishes for it, what the drawing
shows, the source and licence, and the engine class the texture re-textures.

For each symbol the generator emits:

  * data/symbology/terrain_catalogue.json  the machine-readable catalogue,
  * docs/wiki/research/terrain-catalogue.md  the human legend,
  * docs/wiki/research/terrain-catalogue-contact-sheet.png  every symbol
    drawn with its label.

Run:  python3 tools/gen_terrain_catalogue.py
      python3 tools/gen_terrain_catalogue.py --check
      python3 tools/gen_terrain_catalogue.py --table
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
REGISTER_JSON = ROOT / "data" / "symbology" / "dgiwg_concepts.json"
SOURCES_JSON = ROOT / "data" / "symbology" / "terrain_sources.json"
SYMBOLS_JSON = ROOT / "data" / "symbology" / "terrain_symbols.json"
OUT_JSON = ROOT / "data" / "symbology" / "terrain_catalogue.json"
OUT_MD = ROOT / "docs" / "wiki" / "research" / "terrain-catalogue.md"
OUT_SHEET = ROOT / "docs" / "wiki" / "research" / "terrain-catalogue-contact-sheet.png"
TERRAIN_DIR = ROOT / "addons" / "cartography" / "data" / "terrain"
SRC_DIR = TERRAIN_DIR / "src"

NOTE = (
    "The AEE terrain symbol catalogue, a map legend for the terrain and "
    "map-feature textures. The mapping is data driven from the DGIWG Symbol "
    "Register concept index: each feature names the register concept it needs, "
    "and the SO_#### the register publishes for that concept. A feature that "
    "has no dedicated register glyph is recorded, never silently substituted."
)
ATTRIBUTION = "Contains DGIWG Symbol Register data, (C) DGIWG, CC BY 2.0"
SOURCE = (
    "STANAG 3675 Edition 2, succeeded by the DGIWG Symbol Register (DTM50, "
    "DGIWG 252-3); USGS Topographic Map Symbols (2005) for the one "
    "public-domain fallback."
)

SHEET_COLS = 8
SHEET_CELL = 128
SHEET_LABEL = 30
SHEET_PAD = 8

# The category each feature belongs to, for the legend grouping.  The value is
# the terrain_symbols.json category of the first engine row that uses the symbol.
CATEGORY_ORDER = [
    "relief",
    "vegetation",
    "hydrography",
    "works",
    "transport",
    "boundary",
    "control",
    "military",
    "populated",
]


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def register_index() -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    """Return the symbol table and the inverted concept-to-symbol index."""
    table: dict[str, dict[str, Any]] = {}
    index: dict[str, list[str]] = {}
    for entry in load(REGISTER_JSON):
        table[entry["id"]] = entry
        for concept in entry["concepts"]:
            index.setdefault(concept, []).append(entry["id"])
    return table, index


def engine_usage() -> tuple[dict[str, list[dict[str, str]]], dict[str, str]]:
    """Map each symbol id to the engine classes it re-textures, and its category."""
    doc = load(SYMBOLS_JSON)
    usage: dict[str, list[dict[str, str]]] = {}
    category: dict[str, str] = {}
    for kind, section in (
        ("CfgLocationTypes", "locations"),
        ("RscMapControl", "objects"),
    ):
        for row in doc.get(section, []):
            symbol = row.get("symbol")
            if not symbol:
                continue
            usage.setdefault(symbol, []).append(
                {"kind": kind, "class": str(row["class"])}
            )
            category.setdefault(symbol, str(row.get("category", "")))
    return usage, category


def shared_map(sources: dict[str, Any]) -> dict[str, list[str]]:
    """Map each register id to the feature ids that share its drawing."""
    out: dict[str, list[str]] = {}
    for group in sources.get("shared_symbols", []):
        out[group["dgiwg"]] = list(group["ids"])
    return out


def catalogue_rows() -> list[dict[str, Any]]:
    register, index = register_index()
    sources = load(SOURCES_JSON)
    usage, category = engine_usage()
    shared = shared_map(sources)
    rows: list[dict[str, Any]] = []
    for entry in sources["entries"]:
        symbol_id = entry["id"]
        register_id = entry.get("dgiwg")
        published: list[str] = register[register_id]["concepts"] if register_id else []
        row = {
            "id": symbol_id,
            "name": entry.get("name", symbol_id),
            "category": category.get(symbol_id, ""),
            "depicts": entry.get("depicts", ""),
            "concept": entry.get("concept"),
            "glyph_concept": entry.get("glyph_concept"),
            "grade": entry.get("grade"),
            "register_id": register_id,
            "geom": entry.get("geom"),
            "register_concept_count": len(published),
            "register_concept_published": bool(
                entry.get("glyph_concept") and entry["glyph_concept"] in published
            ),
            "source": entry.get("source", ""),
            "licence": entry.get("licence", ""),
            "used_for": usage.get(symbol_id, []),
            "preview": f"addons/cartography/data/terrain/{symbol_id}.paa",
            "shared_with": [
                s for s in shared.get(register_id or "", []) if s != symbol_id
            ],
        }
        rows.append(row)
    return rows


def render_json(rows: list[dict[str, Any]]) -> str:
    doc = {
        "note": NOTE,
        "attribution": ATTRIBUTION,
        "source": SOURCE,
        "register": "data/symbology/dgiwg_concepts.json",
        "count": len(rows),
        "entries": rows,
    }
    return json.dumps(doc, indent=2) + "\n"


def _row_order(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(row: dict[str, Any]) -> tuple[int, str]:
        category = row["category"]
        rank = CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else 99
        return (rank, row["id"])

    return sorted(rows, key=key)


def render_markdown(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# AEE terrain symbol catalogue",
        "",
        NOTE,
        "",
        f"Source: {SOURCE}",
        "",
        f"Attribution: {ATTRIBUTION}.",
        "",
        "The register id is the DGIWG Symbol Register symbol. The concept is the",
        "register concept the feature needs. The grade is specific when the register",
        "publishes a dedicated glyph, generic when only a shared catch-all glyph",
        "exists, substituted when the register has no usable glyph and a different",
        "published glyph is used, and non_register when no register source exists.",
        "",
    ]
    by_grade: dict[str, int] = {}
    for row in rows:
        by_grade[row["grade"]] = by_grade.get(row["grade"], 0) + 1
    summary = ", ".join(f"{g} {n}" for g, n in sorted(by_grade.items()))
    lines += [f"Count: {len(rows)} symbols ({summary}).", ""]

    for row in _row_order(rows):
        used = (
            ", ".join(f"{u['kind']} {u['class']}" for u in row["used_for"])
            or "not registered"
        )
        register_id = row["register_id"] or "none"
        lines += [
            f"## {row['name']} (`{row['id']}`)",
            "",
            f"- Depicts: {row['depicts']}.",
            f"- Register: {register_id} {row['glyph_concept'] or ''}".rstrip() + ".",
            f"- Concept needed: {row['concept'] or 'none published'}.",
            f"- Grade: {row['grade']}.",
            f"- Geometry: {row['geom'] or 'n/a'}.",
            f"- Licence: {row['licence']}.",
            f"- Used for: {used}.",
        ]
        if row["shared_with"]:
            lines.append(f"- Shared drawing with: {', '.join(row['shared_with'])}.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _font(size: int) -> Any:
    from PIL import ImageFont

    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_sheet(rows: list[dict[str, Any]]) -> Any:
    """Draw every symbol with its label into one contact sheet image."""
    from PIL import Image, ImageDraw

    ordered = _row_order(rows)
    cols = SHEET_COLS
    rows_n = math.ceil(len(ordered) / cols)
    cell = SHEET_CELL + SHEET_LABEL
    width = cols * SHEET_CELL
    height = rows_n * cell
    sheet = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    font = _font(13)
    for i, row in enumerate(ordered):
        cx = (i % cols) * SHEET_CELL
        cy = (i // cols) * cell
        draw.rectangle(
            [cx, cy, cx + SHEET_CELL - 1, cy + cell - 1], outline=(210, 210, 210, 255)
        )
        src = SRC_DIR / f"{row['id']}.png"
        if src.is_file():
            with Image.open(src) as icon:
                art = icon.convert("RGBA")
                art.thumbnail((SHEET_CELL - 2 * SHEET_PAD, SHEET_CELL - 2 * SHEET_PAD))
                sheet.alpha_composite(
                    art,
                    (
                        cx + (SHEET_CELL - art.width) // 2,
                        cy + (SHEET_CELL - art.height) // 2,
                    ),
                )
        label = row["id"]
        box = draw.textbbox((0, 0), label, font=font)
        draw.text(
            (cx + (SHEET_CELL - (box[2] - box[0])) // 2, cy + SHEET_CELL + 6),
            label,
            fill=(20, 20, 20, 255),
            font=font,
        )
    return sheet


def sheet_size(count: int) -> tuple[int, int]:
    rows_n = math.ceil(count / SHEET_COLS)
    return (SHEET_COLS * SHEET_CELL, rows_n * (SHEET_CELL + SHEET_LABEL))


def build() -> int:
    rows = catalogue_rows()
    OUT_JSON.write_text(render_json(rows), encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(rows), encoding="utf-8")
    render_sheet(rows).save(OUT_SHEET)
    print(f"terrain catalogue: {len(rows)} symbols written")
    return 0


def check() -> int:
    from PIL import Image

    rows = catalogue_rows()
    stale: list[str] = []
    if OUT_JSON.read_text(encoding="utf-8") != render_json(rows):
        stale.append("terrain_catalogue.json is stale")
    if not OUT_MD.is_file() or OUT_MD.read_text(encoding="utf-8") != render_markdown(
        rows
    ):
        stale.append("terrain-catalogue.md is stale")
    expected = sheet_size(len(rows))
    if not OUT_SHEET.is_file():
        stale.append("contact sheet is missing")
    else:
        with Image.open(OUT_SHEET) as sheet:
            if sheet.size != expected:
                stale.append(f"contact sheet size {sheet.size} != expected {expected}")
    if stale:
        print(f"terrain catalogue: FAIL ({len(stale)})")
        for line in stale:
            print(f"  {line}")
        return 1
    print(f"terrain catalogue: {len(rows)} symbols fresh")
    return 0


def table() -> int:
    for row in _row_order(catalogue_rows()):
        print(
            f"{row['id']}\t{row['register_id'] or '-'}\t{row['grade']}\t"
            f"{row['glyph_concept'] or '-'}\t{row['name']}"
        )
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check()
    if "--table" in argv:
        return table()
    return build()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
