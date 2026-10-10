#!/usr/bin/env python3
"""Generate the AEE terrain and map-feature symbol textures.

Every AEE terrain symbol is cut from the standard's own VECTOR source.  The
DGIWG Symbol Register serves one SVG per symbol at
https://portal.dgiwg.org/public_dgiwg/portrayal/graphics/SO_####.svg.  Each
referenced SVG is rendered with

    rsvg-convert --keep-aspect-ratio -w 128 -h 128 -o OUT.png IN.svg

so the symbol keeps the register's own colours on a transparent ground.  This
generator normalises that render to a 64 px RGBA icon (colour and alpha kept
as they are) and converts it to a .paa with `hemtt utils paa convert`.

The one non-register symbol (quay) is the USGS public-domain vector symbol,
already transparent.  AEE does not hand-draw a terrain symbol and does not
crop a scanned plate.

The authority is STANAG 3675, succeeded by the DGIWG Symbol Register (the
DTM50 product).  See docs/wiki/research/terrain-symbols.md.

Run:  python3 tools/gen_terrain_symbols.py
      python3 tools/gen_terrain_symbols.py --check
      python3 tools/gen_terrain_symbols.py --table
      python3 tools/gen_terrain_symbols.py --render      (re-cut the src PNGs)
      python3 tools/gen_terrain_symbols.py --verify-svg  (prove src is the SVG render)
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
TERRAIN_OUT = ROOT / "addons" / "cartography" / "data" / "terrain"
SRC_DIR = TERRAIN_OUT / "src"

SIZE = 64
RENDER_ARGS = ["--keep-aspect-ratio", "-w", "128", "-h", "128"]

# A librsvg release encodes the same pixels into different PNG bytes, so a
# byte-for-byte compare of a source PNG against a fresh render is
# environment-dependent: a PNG cut with librsvg 2.62 fails the same check on a
# runner that ships 2.58.  Compare the decoded RGBA structure instead, within a
# tolerance that absorbs encoder and antialiasing noise but still rejects a
# plate crop, a re-colour, a wrong source or a stale file.
MAX_CHANNEL_DELTA = 64  # a pixel this far off is a content change, not noise
MAX_CHANGED_FRACTION = 0.05  # antialiasing moves a few edge pixels, not five percent
NOISE_DELTA = 8  # per-channel differences at or below this are noise
MIN_INK_IOU = 0.98  # the painted (alpha) region must overlap the render


def svg_render_mismatch(committed: Path, fresh: Path) -> str | None:
    """Return why the committed PNG is not the SVG render, or None when it is.

    A byte compare cannot cross a librsvg version.  This compares structure:
    the size, a real alpha channel, the colour content and the painted
    geometry, each within a tolerance.
    """
    from PIL import Image, ImageChops

    with Image.open(committed) as c_img, Image.open(fresh) as f_img:
        if c_img.size != f_img.size:
            return f"size {c_img.size} != SVG render {f_img.size}"
        committed_has_alpha = "A" in c_img.getbands()
        committed_rgba = c_img.convert("RGBA")
        fresh_rgba = f_img.convert("RGBA")

    # A point or line symbol renders on a transparent ground.  A source that
    # dropped the alpha channel is a flat plate crop, not that render.
    render_transparent = fresh_rgba.getchannel("A").getextrema()[0] < 255
    if render_transparent and not committed_has_alpha:
        return "source has no alpha channel (a flat crop, not the SVG render)"

    diff = ImageChops.difference(committed_rgba, fresh_rgba)
    worst = max(band[1] for band in diff.getextrema())
    if worst > MAX_CHANNEL_DELTA:
        return f"colour differs from the SVG render by {worst} (a re-colour or another glyph)"

    def above_noise(band):
        return band.point(lambda value: 255 if value > NOISE_DELTA else 0)

    marked = above_noise(diff.getchannel("R"))
    for channel in ("G", "B", "A"):
        marked = ImageChops.lighter(marked, above_noise(diff.getchannel(channel)))
    changed = marked.histogram()[255]
    total = committed_rgba.width * committed_rgba.height
    if changed > MAX_CHANGED_FRACTION * total:
        return f"{changed} of {total} pixels differ from the SVG render"

    committed_ink = committed_rgba.getchannel("A").point(
        lambda v: 255 if v > 127 else 0
    )
    fresh_ink = fresh_rgba.getchannel("A").point(lambda v: 255 if v > 127 else 0)
    union = ImageChops.lighter(committed_ink, fresh_ink).histogram()[255]
    if union:
        overlap = ImageChops.multiply(committed_ink, fresh_ink).histogram()[255]
        iou = overlap / union
        if iou < MIN_INK_IOU:
            return f"painted geometry differs from the SVG render (IoU {iou:.3f})"
    return None


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


def rsvg() -> str:
    tool = shutil.which("rsvg-convert")
    if tool is None:
        raise SystemExit("gen_terrain_symbols: rsvg-convert not found on PATH")
    return tool


def render_svg(svg: Path, out: Path) -> None:
    """Render a register SVG to a transparent PNG with the standard command."""
    out.unlink(missing_ok=True)
    result = subprocess.run(
        [rsvg(), *RENDER_ARGS, "-o", str(out), str(svg)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not out.is_file():
        raise SystemExit(
            f"gen_terrain_symbols: rsvg-convert failed for {svg}\n{result.stderr}"
        )


def normalise(png: Path, tga: Path) -> None:
    """Scale a source drawing to a 64 px icon, keeping colour and alpha."""
    from PIL import Image

    image = Image.open(png).convert("RGBA")
    scale = (SIZE - 2) / max(image.width, image.height)
    width = max(1, round(image.width * scale))
    height = max(1, round(image.height * scale))
    image = image.resize((width, height), Image.LANCZOS)
    rgb = image.convert("RGB")
    alpha = image.getchannel("A")
    # Stretch the ALPHA only, so the ground is fully transparent and the ink
    # is fully opaque.  The RGB is untouched, so the symbol keeps its colour.
    low, high = alpha.getextrema()
    if high > low:
        stretch = 255.0 / (high - low)
        alpha = alpha.point(lambda v: max(0, min(255, round((v - low) * stretch))))
    layer = Image.merge("RGBA", (*rgb.split(), alpha))
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.alpha_composite(layer, ((SIZE - width) // 2, (SIZE - height) // 2))
    tga.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(tga)


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


def _cut(entry: dict[str, Any], tmp_dir: Path, symbol_id: str, paa: Path) -> None:
    """Cut one texture from the entry's source (SVG render, else committed PNG)."""
    tga = tmp_dir / f"{symbol_id}.tga"
    svg_name = entry.get("svg")
    if svg_name:
        png = tmp_dir / f"{symbol_id}.png"
        render_svg(SRC_DIR / svg_name, png)
    else:
        png = SRC_DIR / entry["file"]
        if not png.is_file():
            raise SystemExit(f"gen_terrain_symbols: source image missing: {png}")
    normalise(png, tga)
    convert(tga, paa)


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
            paa = TERRAIN_OUT / f"{symbol_id}.paa"
            _cut(entry, tmp_dir, symbol_id, paa)
            written.append(paa)
    return written


def render_sources() -> list[Path]:
    """Re-cut every register src PNG from its SVG with the standard command."""
    entries = manifest_entries()
    written: list[Path] = []
    for symbol_id, entry in entries.items():
        svg_name = entry.get("svg")
        if not svg_name:
            continue
        out = SRC_DIR / entry["file"]
        render_svg(SRC_DIR / svg_name, out)
        written.append(out)
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
            fresh = tmp_dir / f"{symbol_id}.paa"
            _cut(entry, tmp_dir, symbol_id, fresh)
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


def verify_svg() -> int:
    """Prove every committed src PNG is the render of its register SVG.

    The compare is structural, not byte-for-byte, so it holds across librsvg
    versions.  See svg_render_mismatch.
    """
    entries = manifest_entries()
    bad: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for symbol_id, entry in entries.items():
            svg_name = entry.get("svg")
            if not svg_name:
                continue
            committed = SRC_DIR / entry["file"]
            if not committed.is_file():
                bad.append(f"{symbol_id}: src PNG is missing")
                continue
            fresh = tmp_dir / f"{symbol_id}.png"
            render_svg(SRC_DIR / svg_name, fresh)
            mismatch = svg_render_mismatch(committed, fresh)
            if mismatch:
                bad.append(f"{symbol_id}: {mismatch}")
    if bad:
        print(f"terrain symbols: SVG provenance FAIL ({len(bad)})")
        for line in bad:
            print(f"  {line}")
        return 1
    print(f"terrain symbols: {len(entries)} src PNGs are exact SVG renders")
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check()
    if "--verify-svg" in argv:
        return verify_svg()
    if "--render" in argv:
        written = render_sources()
        print(f"terrain symbols: {len(written)} source PNGs re-cut from SVG")
        return 0
    if "--table" in argv:
        entries = manifest_entries()
        for symbol_id in referenced_symbols(load_json(SOURCE_JSON)):
            entry = entries.get(symbol_id, {})
            print(
                f"{symbol_id}\t{entry.get('dgiwg') or '-'}\t{entry.get('concept', '?')}\t"
                f"{entry.get('file', '?')}\t{entry.get('licence', '?')}"
            )
        return 0
    written = build()
    print(f"terrain symbols: {len(written)} textures written to {TERRAIN_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
