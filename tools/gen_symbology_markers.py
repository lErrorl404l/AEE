#!/usr/bin/env python3
"""Generate the AEE symbology marker textures.

Every AEE map marker is a real CfgMarkers entry whose icon is a real .paa.
Where the engine's own NATO textures carry the symbol, the config references
them.  Where the engine set genuinely lacks a symbol (the whole unknown-
affiliation u_ family, and the engineer, signal, supply, subsurface and
waypoint glyphs) AEE renders its own texture here.

The geometry is NOT invented.  The generator evaluates the committed pure
kernels

  addons/optics/functions/symbology/fnc_symbolFrame.sqf
  addons/optics/functions/symbology/fnc_symbolIcon.sqf

through tools/tests/sqf_lite.py, so the texture and the drawn symbol share one
source of truth.  The frame is stroked and the inner glyph is stroked, in
white on transparent, so the engine marker colour tints the texture the way it
tints the vanilla NATO markers.

Run:  python3 tools/gen_symbology_markers.py
      python3 tools/gen_symbology_markers.py --check

The conversion is hemtt's: TGA with alpha -> DXT5 PAA (hemtt 1.22.0).  It is
byte-deterministic, so --check re-renders and compares.
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
SOURCE_JSON = ROOT / "data" / "symbology" / "symbology_tables.json"
MARKERS_OUT = ROOT / "addons" / "optics" / "data" / "markers"
SYM = ROOT / "addons" / "optics" / "functions" / "symbology"
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
WHITE = (255, 255, 255, 255)


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


def _stroke_polyline(draw: Any, points: list[list[float]], closed: bool) -> None:
    pixel = [_px(point[0], point[1]) for point in points]
    if closed and len(pixel) > 2:
        pixel = pixel + [pixel[0]]
    if len(pixel) > 1:
        draw.line(pixel, fill=WHITE, width=STROKE, joint="curve")


def render(affiliation: str, dimension: str, category: str, path: Path) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    for polyline in run_sqf(FRAME_KERNEL, [affiliation, dimension], {}):
        _stroke_polyline(draw, polyline, closed=True)

    for kind, points in run_sqf(ICON_KERNEL, [category], {}):
        if kind == "ellipse":
            centre, axes, _angle = points
            cx, cy = _px(centre[0], centre[1])
            ax = axes[0] * 0.5 * (SIZE - 1)
            ay = axes[1] * 0.5 * (SIZE - 1)
            draw.ellipse(
                [cx - ax, cy - ay, cx + ax, cy + ay], outline=WHITE, width=STROKE
            )
        elif kind == "poly":
            _stroke_polyline(draw, points, closed=True)
        else:
            _stroke_polyline(draw, points, closed=False)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def convert(tga: Path, paa: Path) -> None:
    hemtt = shutil.which("hemtt")
    if hemtt is None:
        raise SystemExit("gen_symbology_markers: hemtt not found on PATH")
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
    written = build(source, MARKERS_OUT)
    print(f"symbology markers: {len(written)} textures written to {MARKERS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
