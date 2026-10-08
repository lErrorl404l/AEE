#!/usr/bin/env python3
"""Generate the AEE terrain and map-feature symbol textures.

Every AEE terrain symbol is a REAL public-domain drawing, re-textured to a
.paa.  The drawings come from the US Army FM 21-31 "Topographic Symbols"
(1961, public domain) and the USGS "Topographic Map Symbols" sheet (2005,
public domain), cropped by the extraction step and committed under
addons/optics/data/terrain/src/.  AEE does NOT hand-draw a terrain symbol.

This generator reads data/symbology/terrain_sources.json (the per-symbol
provenance manifest), rasterises each source to a white-on-transparent 64 px
mask so the engine location and object colour tints it, and converts it to a
.paa with `hemtt utils paa convert`.

The authority is STANAG 3675, succeeded by the DGIWG Symbol Register (the
DTM50 product), with FM 21-31 and the USGS sheet as the public-domain
fallback.  See docs/wiki/research/terrain-symbols.md.

Run:  python3 tools/gen_terrain_symbols.py
      python3 tools/gen_terrain_symbols.py --check
      python3 tools/gen_terrain_symbols.py --table
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
SOURCE_JSON = ROOT / "data" / "symbology" / "terrain_symbols.json"
MANIFEST_JSON = ROOT / "data" / "symbology" / "terrain_sources.json"
TERRAIN_OUT = ROOT / "addons" / "optics" / "data" / "terrain"
SRC_DIR = TERRAIN_OUT / "src"

SIZE = 64
WHITE = (255, 255, 255, 255)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def referenced_symbols(source: dict[str, Any]) -> list[str]:
    """Every symbol id referenced by a location or object row, in table order."""
    referenced: list[str] = []
    for section in ("locations", "objects"):
        for row in source[section]:
            symbol = row.get("symbol")
            if symbol and symbol not in referenced:
                referenced.append(symbol)
    return referenced


def manifest_entries() -> dict[str, dict[str, Any]]:
    doc = load_json(MANIFEST_JSON)
    return {entry["id"]: entry for entry in doc.get("entries", [])}


def _mask_from_source(path: Path) -> Any:
    """Return (rgb, alpha) for a source drawing.

    The symbol keeps its own colours.  Only the background becomes
    transparent.  A source with a real alpha channel carries the symbol in
    that channel (a DGIWG register graphic).  An opaque source (an FM 21-31 or
    USGS crop) has its light ground keyed out by inverting the luminance, so
    the ink stays and the ground clears.
    """
    from PIL import Image, ImageOps

    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A")
    rgb = image.convert("RGB")
    low, _high = alpha.getextrema()
    if low >= 250:
        # Opaque ground: key it out by luminance, keep the ink.
        alpha = ImageOps.invert(image.convert("L"))
    return rgb, alpha


def render(symbol_id: str, src: Path, path: Path) -> None:
    from PIL import Image

    rgb, alpha = _mask_from_source(src)
    scale = (SIZE - 2) / max(alpha.width, alpha.height)
    width = max(1, round(alpha.width * scale))
    height = max(1, round(alpha.height * scale))
    size = (width, height)
    rgb = rgb.resize(size, Image.LANCZOS)
    alpha = alpha.resize(size, Image.LANCZOS)
    # Stretch the ALPHA only, so the ground is fully transparent and the ink
    # is fully opaque.  The RGB is untouched, so the symbol keeps its colour.
    low, high = alpha.getextrema()
    if high > low:
        stretch = 255.0 / (high - low)
        alpha = alpha.point(lambda v: max(0, min(255, round((v - low) * stretch))))
    layer = Image.merge("RGBA", (*rgb.split(), alpha))
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(layer, ((SIZE - width) // 2, (SIZE - height) // 2))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)


def convert(tga: Path, paa: Path) -> None:
    hemtt = shutil.which("hemtt")
    if hemtt is None:
        raise SystemExit("gen_terrain_symbols: hemtt not found on PATH")
    paa.unlink(missing_ok=True)
    result = subprocess.run(
        [hemtt, "utils", "paa", "convert", str(tga), str(paa)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"gen_terrain_symbols: paa convert failed\n{result.stderr}")


def build() -> list[Path]:
    source = load_json(SOURCE_JSON)
    entries = manifest_entries()
    written: list[Path] = []
    TERRAIN_OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for symbol_id in referenced_symbols(source):
            entry = entries.get(symbol_id)
            if entry is None:
                raise SystemExit(
                    f"gen_terrain_symbols: no source manifest entry for {symbol_id!r}"
                )
            src = SRC_DIR / entry["file"]
            if not src.is_file():
                raise SystemExit(f"gen_terrain_symbols: source image missing: {src}")
            tga = tmp_dir / f"{symbol_id}.tga"
            render(symbol_id, src, tga)
            paa = TERRAIN_OUT / f"{symbol_id}.paa"
            convert(tga, paa)
            written.append(paa)
    return written


def check() -> int:
    stale: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        source = load_json(SOURCE_JSON)
        entries = manifest_entries()
        for symbol_id in referenced_symbols(source):
            committed = TERRAIN_OUT / f"{symbol_id}.paa"
            if not committed.is_file():
                stale.append(f"{symbol_id}.paa is missing")
                continue
            entry = entries.get(symbol_id, {})
            src = SRC_DIR / entry.get("file", "")
            if not src.is_file():
                stale.append(f"{symbol_id}: source image missing")
                continue
            tga = tmp_dir / f"{symbol_id}.tga"
            render(symbol_id, src, tga)
            fresh = tmp_dir / f"{symbol_id}.paa"
            convert(tga, fresh)
            if committed.read_bytes() != fresh.read_bytes():
                stale.append(f"{symbol_id}.paa is stale")
    if stale:
        print(f"terrain symbols: FAIL ({len(stale)})")
        for line in stale:
            print(f"  {line}")
        return 1
    print(
        f"terrain symbols: {len(referenced_symbols(load_json(SOURCE_JSON)))} textures fresh"
    )
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check()
    if "--table" in argv:
        entries = manifest_entries()
        for symbol_id in referenced_symbols(load_json(SOURCE_JSON)):
            entry = entries.get(symbol_id, {})
            print(
                f"{symbol_id}\t{entry.get('file', '?')}\t{entry.get('source', '?')}\t"
                f"{entry.get('licence', '?')}"
            )
        return 0
    written = build()
    print(f"terrain symbols: {len(written)} textures written to {TERRAIN_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
