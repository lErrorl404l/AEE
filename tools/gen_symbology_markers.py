#!/usr/bin/env python3
"""Generate the AEE symbology marker textures.

Every AEE map marker is a real CfgMarkers entry whose icon is a real .paa.
Where the engine's own NATO textures carry the symbol, the config references
them.  Where the engine set genuinely lacks a symbol (the whole unknown-
affiliation u_ family, and the engineer, signal, supply, subsurface and
waypoint glyphs) AEE renders its own texture here.

Each produced texture has two layers.

  * The frame.  AEE draws the affiliation frame from its own spec geometry in
    addons/symbology/functions/symbology/fnc_symbolFrame.sqf, so the frame stays
    inside the unit box and the dimension modifier is applied.

  * The inner glyph.  Where a matching public-domain APP-6 function glyph
    exists in addons/symbology/data/markers/src/, the generator rasterises it
    (rsvg-convert), drops the friendly frame rectangle that the source file
    carries, and composites the glyph onto the AEE frame.  Where no matching
    public-domain glyph exists, the generator draws AEE's own glyph geometry
    from fnc_symbolIcon.sqf.  The per-marker source is reported by --table.

The AEE kernels are evaluated through tools/tests/sqf_lite.py, so the texture
and the drawn symbol share one source of truth.  The frame is drawn in the
affiliation colour and the glyph in black, on a transparent background, so the
texture carries the colour and the engine tint is neutral.

Run:  python3 tools/gen_symbology_markers.py
      python3 tools/gen_symbology_markers.py --check
      python3 tools/gen_symbology_markers.py --table

The conversion is hemtt's: TGA with alpha -> DXT5 PAA (hemtt 1.22.0).  It is
byte-deterministic, so --check re-renders and compares.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
SOURCE_JSON = ROOT / "data" / "symbology" / "symbology_tables.json"
MARKERS_OUT = ROOT / "addons" / "symbology" / "data" / "markers"
GLYPH_SRC = MARKERS_OUT / "src"
SYM = ROOT / "addons" / "symbology" / "functions" / "symbology"
FRAME_KERNEL = SYM / "fnc_symbolFrame.sqf"
ICON_KERNEL = SYM / "fnc_symbolIcon.sqf"

sys.path.insert(0, str(ROOT / "tools" / "tests"))
from sqf_lite import run_sqf  # noqa: E402

# The glyphs the engine ships per b_ / o_ / n_ family.  Read from the shipped
# config: Addons/ui_f.pbo config.cpp, the CfgMarkers NATO family block.
VANILLA_FAMILIES = ("b", "o", "n")
VANILLA_GLYPHS = frozenset(
    {
        "unknown",
        "inf",
        "motor_inf",
        "mech_inf",
        "armor",
        "recon",
        "air",
        "plane",
        "uav",
        "naval",
        "med",
        "art",
        "mortar",
        "hq",
        "support",
        "maint",
        "service",
        "installation",
        "antiair",
    }
)

FAMILY_AFFILIATION = {"b": "friend", "o": "hostile", "n": "neutral", "u": "unknown"}
SIZE = 64
STROKE = 3
# The glyph is black (APP-6).  The frame carries the affiliation colour, so the
# texture keeps its own colours and the engine tint stays neutral.
INK = (0, 0, 0, 255)
AFFIL_RGB = {
    "friend": (0, 0, 255),
    "hostile": (255, 0, 0),
    "neutral": (0, 175, 0),
    "unknown": (255, 255, 128),
}

# The AEE class category -> the public-domain APP-6 function glyph file under
# src/.  The match is by function.  A category that is absent here has no
# matching public-domain glyph, so the generator draws AEE's own geometry from
# fnc_symbolIcon.sqf and --table reports it.
PD_GLYPH = {
    "armour": "APP-6 Armored.svg",
    "motorised": "APP-6 Infantry Motorised.svg",
    "artillery": "APP-6 Artillery.svg",
    "engineer": "APP-6 Engineer.svg",
    "signal": "APP-6 Signals.svg",
    "medical": "APP-6 Medical.svg",
    "supply": "APP-6 Combat Supply.svg",
    "support": "APP-6 Combat Service Support.svg",
    "recon": "APP-6 Reconnaissance.svg",
    "air_defence": "APP-6 Air Defence.svg",
    "rotary": "APP-6 Army Aviation.svg",
    "uav": "APP-6 Unmanned Air Recon.svg",
    "sea_surface": "APP-6 Navy.svg",
}

# The inner glyph box in the unit box.  The frame kernel stays inside [-1, 1];
# this box keeps the glyph clear of every affiliation frame.
INNER = 0.55

# The source art strokes its paths at 3 units on a 170-unit canvas.  Once the
# glyph is scaled into the 64 px marker that is about 0.6 px, which is too thin
# next to the 3 px AEE frame.  The generator multiplies each source stroke width
# by this factor so the glyph line weight matches the frame.  The glyph geometry
# is unchanged.  Only the line weight is scaled.
GLYPH_STROKE_SCALE = 3.0


def load_source() -> dict[str, Any]:
    return json.loads(SOURCE_JSON.read_text(encoding="utf-8"))


def produced_set(source: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    """Every (family, glyph, affiliation, category) that needs a produced .paa."""
    families = [row["category"] for row in source["families"]]
    out: list[tuple[str, str, str, str]] = []
    for family in families:
        for row in source["glyphs"]:
            glyph = row["category"]
            if family in VANILLA_FAMILIES and glyph in VANILLA_GLYPHS:
                continue
            out.append((family, glyph, FAMILY_AFFILIATION[family], row["name"]))
    return out


def _px(x: float, y: float) -> tuple[float, float]:
    return ((x + 1.0) * 0.5 * (SIZE - 1), (1.0 - y) * 0.5 * (SIZE - 1))


def _inner_box() -> tuple[float, float, float, float]:
    x0, y0 = _px(-INNER, INNER)
    x1, y1 = _px(INNER, -INNER)
    return x0, y0, x1, y1


def _stroke_polyline(
    draw: Any,
    points: list[list[float]],
    closed: bool,
    colour: tuple[int, int, int, int] = INK,
) -> None:
    pixel = [_px(point[0], point[1]) for point in points]
    if closed and len(pixel) > 2:
        pixel = pixel + [pixel[0]]
    if len(pixel) > 1:
        draw.line(pixel, fill=colour, width=STROKE, joint="curve")


def _rasterise_glyph(svg_path: Path) -> Any:
    """Rasterise a source SVG to a white-on-transparent mask.

    The source files carry the friendly frame as a full-canvas <rect>.  AEE
    draws its own frame, so the rect is removed and only the inner function
    glyph is kept.
    """
    from PIL import Image

    svg = svg_path.read_text(encoding="utf-8")
    svg = re.sub(r"<rect\b[^>]*?/>", "", svg)
    svg = re.sub(r"<rect\b[^>]*?>.*?</rect>", "", svg, flags=re.DOTALL)
    svg = re.sub(
        r'stroke-width="([0-9.]+)"',
        lambda m: f'stroke-width="{float(m.group(1)) * GLYPH_STROKE_SCALE:g}"',
        svg,
    )

    rsvg = shutil.which("rsvg-convert")
    if rsvg is None:
        raise SystemExit("gen_symbology_markers: rsvg-convert not found on PATH")

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "glyph.svg"
        out = Path(tmp) / "glyph.png"
        src.write_text(svg, encoding="utf-8")
        result = subprocess.run(
            [rsvg, "-w", "340", str(src), "-o", str(out)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit(
                f"gen_symbology_markers: rsvg-convert failed for {svg_path.name}\n"
                f"{result.stderr}"
            )
        rgba = Image.open(out).convert("RGBA")

    mask = rgba.getchannel("A")
    glyph = rgba.copy()
    glyph.putalpha(mask)
    return glyph


def _composite_pd_glyph(image: Any, svg_path: Path) -> None:
    from PIL import Image

    raster = _rasterise_glyph(svg_path)
    x0, y0, x1, y1 = _inner_box()
    scale = min((x1 - x0) / raster.width, (y1 - y0) / raster.height)
    width = max(1, round(raster.width * scale))
    height = max(1, round(raster.height * scale))
    glyph = raster.resize((width, height), Image.LANCZOS)
    left = round((x0 + x1) / 2.0 - width / 2.0)
    top = round((y0 + y1) / 2.0 - height / 2.0)
    image.alpha_composite(glyph, (left, top))


def _draw_aee_glyph(draw: Any, category: str) -> None:
    for kind, points in run_sqf(ICON_KERNEL, [category], {}):
        if kind == "ellipse":
            centre, axes, _angle = points
            cx, cy = _px(centre[0], centre[1])
            ax = axes[0] * 0.5 * (SIZE - 1)
            ay = axes[1] * 0.5 * (SIZE - 1)
            draw.ellipse(
                [cx - ax, cy - ay, cx + ax, cy + ay], outline=INK, width=STROKE
            )
        elif kind == "poly":
            _stroke_polyline(draw, points, closed=True)
        else:
            _stroke_polyline(draw, points, closed=False)


def render(affiliation: str, dimension: str, category: str, path: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    for polyline in run_sqf(FRAME_KERNEL, [affiliation, dimension], {}):
        _stroke_polyline(draw, polyline, closed=True, colour=AFFIL_RGB[affiliation])

    svg_name = PD_GLYPH.get(category)
    if svg_name is not None:
        _composite_pd_glyph(image, GLYPH_SRC / svg_name)
    else:
        _draw_aee_glyph(draw, category)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def convert(tga: Path, paa: Path) -> None:
    hemtt = shutil.which("hemtt")
    if hemtt is None:
        raise SystemExit("gen_symbology_markers: hemtt not found on PATH")
    # hemtt paa convert leaves an existing destination untouched.  Without this
    # unlink a re-render after a kernel change would keep the old texture and
    # --check would compare against it.
    paa.unlink(missing_ok=True)
    result = subprocess.run(
        [hemtt, "utils", "paa", "convert", str(tga), str(paa)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"gen_symbology_markers: paa convert failed\n{result.stderr}")


def build(source: dict[str, Any], out_dir: Path) -> list[Path]:
    written: list[Path] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for family, glyph, affiliation, category in produced_set(source):
            name = f"AEE_{family}_{glyph}"
            tga = tmp_dir / f"{name}.tga"
            render(affiliation, _dimension(source, category), category, tga)
            paa = out_dir / f"{name}.paa"
            convert(tga, paa)
            written.append(paa)
    return written


def _dimension(source: dict[str, Any], category: str) -> str:
    for row in source["glyphs"]:
        if row["name"] == category:
            return str(row["dimension"])
    raise SystemExit(f"gen_symbology_markers: no glyph row for {category!r}")


def source_table(source: dict[str, Any]) -> list[dict[str, str]]:
    """Per produced marker: the glyph source, the frame source and the licence."""
    rows: list[dict[str, str]] = []
    for family, glyph, affiliation, category in produced_set(source):
        svg_name = PD_GLYPH.get(category)
        rows.append(
            {
                "marker": f"AEE_{family}_{glyph}",
                "affiliation": affiliation,
                "dimension": _dimension(source, category),
                "glyph_source": svg_name
                if svg_name
                else "AEE geometry (fnc_symbolIcon.sqf)",
                "frame_source": "AEE kernel (fnc_symbolFrame.sqf)",
                "licence": "Public domain"
                if svg_name
                else "AEE own work (GPL-2.0-or-later)",
            }
        )
    return rows


def check(source: dict[str, Any]) -> int:
    stale: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for family, glyph, affiliation, category in produced_set(source):
            name = f"AEE_{family}_{glyph}"
            committed = MARKERS_OUT / f"{name}.paa"
            if not committed.is_file():
                stale.append(f"{name}.paa is missing")
                continue
            tga = tmp_dir / f"{name}.tga"
            render(affiliation, _dimension(source, category), category, tga)
            fresh = tmp_dir / f"{name}.paa"
            convert(tga, fresh)
            if committed.read_bytes() != fresh.read_bytes():
                stale.append(f"{name}.paa is stale")
    if stale:
        print(f"symbology markers: FAIL ({len(stale)})")
        for line in stale:
            print(f"  {line}")
        return 1
    print(f"symbology markers: {len(produced_set(source))} textures fresh")
    return 0


def main(argv: list[str]) -> int:
    source = load_source()
    if "--check" in argv:
        return check(source)
    if "--table" in argv:
        for row in source_table(source):
            print(
                f"{row['marker']}\t{row['affiliation']}\t{row['dimension']}\t"
                f"{row['glyph_source']}\t{row['frame_source']}\t{row['licence']}"
            )
        return 0
    written = build(source, MARKERS_OUT)
    print(f"symbology markers: {len(written)} textures written to {MARKERS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
