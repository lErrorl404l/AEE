#!/usr/bin/env python3
"""Compose the full APP-6 cross-product from the real catalogue symbols.

The catalogue holds one real framed symbol per (affiliation, function) the
uploaders drew.  APP-6 composes a symbol from a frame (the affiliation), the
battle-dimension modifier, and a function glyph.  The frame and the glyph are
independent, so the same glyph is a real symbol in every affiliation frame.

This generator extracts the function glyph from each real symbol (the source
SVG with its frame element removed), then re-frames that glyph in all four
affiliation frames.  The frames are drawn by AEE from the APP-6 geometry
(rectangle friend, diamond hostile, square neutral, quatrefoil unknown), filled
with the affiliation colour and outlined black, which keeps the output ours and
completes the set the uploaders did not draw.  The glyph keeps its own colour
(black).  The texture carries the colour, so the engine tint is neutral.

Only combinations the standard defines are emitted: a glyph that exists in one
affiliation is a real symbol in the other three.  A combination with no glyph
is not emitted.

Run:  python3 tools/gen_symbology_crossproduct.py
      python3 tools/gen_symbology_crossproduct.py --check
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from symbology_categories import marker_category, VARIATION_HIDDEN_SCOPE
from typing import Any

ROOT = Path(__file__).parents[1]
CATALOGUE = ROOT / "data" / "symbology" / "nato_catalogue.json"
# The committed Commons SVG set, the same files the catalogue generator reads.
# Deriving from the committed corpus (not a /tmp working copy) keeps the
# composition reproducible in any checkout.
SOURCE_ROOT = ROOT / "data" / "symbology" / "sources" / "svg"
MARKERS_OUT = ROOT / "addons" / "symbology" / "data" / "markers"
CONFIG_OUT = ROOT / "addons" / "symbology" / "config_crossproduct.hpp"
ADDON_PREFIX = "\\z\\aee\\addons\\symbology\\data\\markers"

SIZE = 64
GLYPH_BOX = 44  # the glyph fits this box inside the 64 px marker

AFFIL_LETTER = {"Friend": "F", "Hostile": "H", "Neutral": "N", "Unknown": "U"}
AFFIL_SIDE = {"Friend": 1, "Hostile": 0, "Neutral": 2, "Unknown": 2}
AFFIL_ORDER = ["Friend", "Hostile", "Neutral", "Unknown"]
# The APP-6 / MIL-STD-2525 affiliation frame colours, as the source drawings
# carry them: friend blue, hostile red, neutral green, unknown yellow.
AFFIL_RGB = {
    "Friend": (0, 0, 255),
    "Hostile": (255, 0, 0),
    "Neutral": (0, 175, 0),
    "Unknown": (255, 255, 128),
}
DIM_LETTER = {
    "Land": "L",
    "Air/Space": "A",
    "Sea Surface": "S",
    "Subsurface": "U",
    "Installation": "I",
    "Equipment": "E",
}


def _slug(text: str, limit: int = 30) -> str:
    out: list[str] = []
    prev_us = False
    for ch in text:
        if ch.isalnum():
            out.append(ch)
            prev_us = False
        elif not prev_us:
            out.append("_")
            prev_us = True
    return "".join(out).strip("_")[:limit].rstrip("_") or "Symbol"


def load() -> list[dict[str, Any]]:
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    return [e for e in data["entries"] if e.get("kind", "symbol") == "symbol"]


def glyph_svg(entry: dict[str, Any]) -> str | None:
    """The source SVG with its frame element removed, so only the glyph stays."""
    src = SOURCE_ROOT / entry["dir"] / entry["file"]
    if src.suffix.lower() != ".svg" or not src.exists():
        return None
    text = src.read_text(encoding="utf-8", errors="replace")
    # A CdnMCG frame is a <path id="...Frame">.  A PD APP-6 frame is the outer
    # <rect> that spans the whole viewBox.  Remove whichever is present.
    stripped = re.sub(
        r"<path\b[^>]*\bid=\"[^\"]*Frame[^\"]*\"[^>]*/>", "", text, flags=re.S
    )
    if stripped == text:
        stripped = re.sub(r"<rect\b[^>]*?/>", "", text, count=1, flags=re.S)
    return stripped if stripped != text else None


def _frame_image(affil: str) -> Any:
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    fill = AFFIL_RGB[affil] + (255,)
    ink = (0, 0, 0, 255)
    m = 4
    w = 3
    if affil == "Friend":
        d.rectangle([m, m + 4, SIZE - m, SIZE - m - 4], fill=fill, outline=ink, width=w)
    elif affil == "Hostile":
        pts = [(SIZE / 2, m), (SIZE - m, SIZE / 2), (SIZE / 2, SIZE - m), (m, SIZE / 2)]
        d.polygon(pts, fill=fill)
        d.line(pts + [pts[0]], fill=ink, width=w)
    elif affil == "Neutral":
        d.rectangle(
            [m + 3, m + 3, SIZE - m - 3, SIZE - m - 3], fill=fill, outline=ink, width=w
        )
    else:  # Unknown, the quatrefoil.
        for box in (
            [m, m, SIZE / 2, SIZE / 2],
            [SIZE / 2, m, SIZE - m, SIZE / 2],
            [m, SIZE / 2, SIZE / 2, SIZE - m],
            [SIZE / 2, SIZE / 2, SIZE - m, SIZE - m],
        ):
            d.ellipse(box, fill=fill, outline=ink, width=w)
    return img


def _glyph_image(svg_text: str) -> Any | None:
    from PIL import Image, ImageChops

    rsvg = shutil.which("rsvg-convert")
    if rsvg is None:
        raise SystemExit("gen_symbology_crossproduct: rsvg-convert not found")
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "g.svg"
        p.write_text(svg_text, encoding="utf-8")
        png = Path(tmp) / "g.png"
        r = subprocess.run(
            [
                rsvg,
                "-w",
                str(GLYPH_BOX),
                "-h",
                str(GLYPH_BOX),
                "--keep-aspect-ratio",
                str(p),
                "-o",
                str(png),
            ],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not png.exists():
            return None
        art = Image.open(png).convert("RGBA")
    lum = art.convert("L")
    ink = ImageChops.invert(lum)
    alpha = ImageChops.multiply(ink, art.getchannel("A"))
    if alpha.getbbox() is None:
        return None
    # Keep the glyph's own colour (black); only the alpha comes from the ink
    # mask, so a light background stays transparent.
    glyph = art.copy()
    glyph.putalpha(alpha)
    return glyph


def convert(tga: Path, paa: Path) -> None:
    hemtt = shutil.which("hemtt")
    if hemtt is None:
        raise SystemExit("gen_symbology_crossproduct: hemtt not found")
    paa.unlink(missing_ok=True)
    r = subprocess.run(
        [hemtt, "utils", "paa", "convert", str(tga), str(paa)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"paa convert failed for {paa.name}\n{r.stderr}")


def distinct_glyphs() -> dict[str, dict[str, Any]]:
    """One representative entry per distinct function glyph."""
    glyphs: dict[str, dict[str, Any]] = {}
    for entry in load():
        key = entry["func"]
        if key not in glyphs:
            glyphs[key] = entry
    return glyphs


def crossproduct_names() -> list[tuple[str, dict[str, Any], str]]:
    out: list[tuple[str, dict[str, Any], str]] = []
    seen: set[str] = set()
    for func, entry in sorted(distinct_glyphs().items()):
        dim = entry["dim"]
        for affil in AFFIL_ORDER:
            base = f"AEE_X{AFFIL_LETTER[affil]}{DIM_LETTER[dim]}_{_slug(func)}"
            name = base
            n = 2
            while name in seen:
                name = f"{base}_{n}"
                n += 1
            seen.add(name)
            out.append((name, entry, affil))
    return out


def build() -> int:
    from PIL import Image

    MARKERS_OUT.mkdir(parents=True, exist_ok=True)
    items = crossproduct_names()
    made = 0
    lines = [
        "// Generated by tools/gen_symbology_crossproduct.py.  Do not edit by hand.",
        "// The composed APP-6 cross-product: each real function glyph re-framed in",
        "// the four affiliation frames AEE draws from the APP-6 geometry.",
        "",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for name, entry, affil in items:
            svg = glyph_svg(entry)
            if svg is None:
                continue
            glyph = _glyph_image(svg)
            if glyph is None:
                continue
            frame = _frame_image(affil)
            canvas = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
            canvas.alpha_composite(frame)
            canvas.alpha_composite(
                glyph, ((SIZE - glyph.width) // 2, (SIZE - glyph.height) // 2)
            )
            tga = tmp_dir / f"{name}.tga"
            canvas.save(tga)
            convert(tga, MARKERS_OUT / f"{name}.paa")
            icon = f"{ADDON_PREFIX}\\{name}.paa"
            side = AFFIL_SIDE[affil]
            lines += [
                f"    class {name}: AEE_MarkerBase {{",
                f'        name = "AEE {affil} {entry["dim"]} {entry["func"]}";',
                f'        icon = "{icon}";',
                f'        texture = "{icon}";',
                f"        side = {side};",
                f'        markerClass = "{marker_category(affil, entry["dim"])}";',
                f"        scope = {VARIATION_HIDDEN_SCOPE};",
                "    };",
            ]
            made += 1
    CONFIG_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"cross-product: {made} composed markers written")
    return 0


def main(argv: list[str]) -> int:
    if "--table" in argv:
        for name, entry, affil in crossproduct_names():
            print(f"{name}\t{affil}\t{entry['dim']}\t{entry['func']}")
        return 0
    return build()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
