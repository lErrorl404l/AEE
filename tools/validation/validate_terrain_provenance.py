#!/usr/bin/env python3
"""Prove every shipped AEE terrain texture is cut from a standard VECTOR source.

AEE ships no cropped plate scan.  Every register entry must carry a DGIWG
Symbol Register id, a concept name, and a committed SVG whose render is the
committed source PNG.  The compare is structural, not byte-for-byte, so it
holds across librsvg versions.  Every non-register entry must be recorded
in `no_register_source` with a public-domain or CC BY licence.

This fails when:
  - a referenced symbol has no manifest entry;
  - a register entry has no SVG, or its source PNG is not the render of
    that SVG (a crop, a re-colour, a wrong source, or a stale file);
  - a register entry's licence is not CC BY;
  - a non-register entry is not recorded, or its licence is not open;
  - any source image is plate-sized (a scan crop is about 1200 px wide; a
    register render is at most 128 px);
  - any entry still names an FM 21-31 plate crop.

Run: python3 tools/validation/validate_terrain_provenance.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[2]
SOURCE_JSON = ROOT / "data" / "symbology" / "terrain_symbols.json"
MANIFEST_JSON = ROOT / "data" / "symbology" / "terrain_sources.json"
TERRAIN_DIR = ROOT / "addons" / "optics" / "data" / "terrain"
SRC_DIR = TERRAIN_DIR / "src"

# A register render is 128 px.  A scanned plate crop is far larger.
MAX_SOURCE_PX = 256
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


def referenced(doc: dict) -> list[str]:
    out: list[str] = []
    for section in ("locations", "objects"):
        for row in doc.get(section, []):
            symbol = row.get("symbol")
            if symbol and symbol not in out:
                out.append(symbol)
    return out


def main() -> int:
    from PIL import Image

    errors: list[str] = []
    for path in (SOURCE_JSON, MANIFEST_JSON):
        if not path.exists():
            print(f"validate_terrain_provenance: {path.name} missing")
            return 1

    doc = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    entries = {e["id"]: e for e in manifest.get("entries", [])}
    # A feature with no register drawing is recorded: a substituted glyph for a
    # feature the register does not publish, or a non-register public-domain
    # source.  Both are listed, so an unrecorded substitution fails here.
    recorded = {e["id"] for e in manifest.get("substituted", [])}
    recorded |= {e["id"] for e in entries.values() if e.get("grade") == "non_register"}
    refs = referenced(doc)

    rsvg = shutil.which("rsvg-convert")
    if rsvg is None:
        print("validate_terrain_provenance: rsvg-convert not found on PATH")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for symbol in refs:
            entry = entries.get(symbol)
            if entry is None:
                errors.append(f"{symbol}: no source manifest entry")
                continue
            src = SRC_DIR / entry.get("file", "")
            if not src.is_file():
                errors.append(f"{symbol}: source image is missing")
                continue

            with Image.open(src) as image:
                if max(image.size) > MAX_SOURCE_PX:
                    errors.append(
                        f"{symbol}: source image is plate-sized {image.size} "
                        f"(a scan crop, not a register render)"
                    )

            licence = str(entry.get("licence", "")).lower()
            if entry.get("dgiwg"):
                if not (entry.get("concept") or entry.get("glyph_concept")):
                    # A recorded substitution (grade substituted) may have no
                    # register concept when the register publishes none for the
                    # feature; it is gated by the catalogue substitution test.
                    if entry.get("grade") != "substituted":
                        errors.append(f"{symbol}: register entry has no concept name")
                if "cc by" not in licence:
                    errors.append(f"{symbol}: register entry licence is not CC BY")
                svg_name = entry.get("svg")
                if not svg_name:
                    errors.append(f"{symbol}: register entry has no SVG source")
                    continue
                svg = SRC_DIR / svg_name
                if not svg.is_file():
                    errors.append(f"{symbol}: register SVG {svg_name} is missing")
                    continue
                fresh = tmp_dir / f"{symbol}.png"
                result = subprocess.run(
                    [rsvg, *RENDER_ARGS, "-o", str(fresh), str(svg)],
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0 or not fresh.is_file():
                    errors.append(f"{symbol}: rsvg-convert failed for {svg_name}")
                    continue
                mismatch = svg_render_mismatch(src, fresh)
                if mismatch:
                    errors.append(
                        f"{symbol}: source PNG is not the render of {svg_name} "
                        f"({mismatch})"
                    )
            else:
                if symbol not in recorded:
                    errors.append(
                        f"{symbol}: no register source and not recorded in "
                        f"no_register_source"
                    )
                if "public domain" not in licence and "cc by" not in licence:
                    errors.append(f"{symbol}: fallback licence is not open")

            if "fm 21-31" in str(entry.get("source", "")).lower():
                errors.append(f"{symbol}: entry still names an FM 21-31 plate crop")

    for orphan in sorted(set(entries) - set(refs)):
        errors.append(f"{orphan}: manifest entry is not referenced")
    for orphan in sorted(recorded - set(entries)):
        errors.append(f"{orphan}: recorded as no-register-source but has no entry")

    if errors:
        print(f"validate_terrain_provenance: FAIL ({len(errors)})")
        for line in errors[:40]:
            print(f"  {line}")
        return 1
    register = sum(1 for s in refs if entries.get(s, {}).get("dgiwg"))
    print(
        f"validate_terrain_provenance: PASS ({len(refs)} textures, "
        f"{register} register SVG renders, {len(recorded)} recorded fallbacks)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
