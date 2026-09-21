#!/usr/bin/env python3
"""Generate feathered thermal-ground tiles (issue #204).

The terrain proxy-plane overlay needs tiles that blend with their
neighbours - a hard-edged grid square reads as a grid.  Each tile is a
WHOT-red heat colour with a RADIAL ALPHA FALLOFF baked in: solid at the
centre, transparent over the outer ~25% of the radius.  Overlapping
tiles alpha-blend, so the transition between a hot tile and a cold
tile is a continuous ramp, not a seam.

The falloff curve is the anti-blocking guarantee.  It is VERIFIABLE
off-game: this script writes a PNG per heat level, converts each to
.paa via `hemtt utils paa convert`, then reads the PAA back and asserts
the alpha profile (solid centre, monotone falloff, transparent edge).

The SQF overlay paints tiles via setObjectTexture, swapping the texture
per tile as the heat field changes - the same mechanism the thermal
object paint already uses (fnc_applySelectionThermal).

Levels: 8 (the thermal render uses 32 for objects; the ground field is
lower-resolution so 8 bands are visually indistinguishable at 5m cells).
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "addons" / "thermal" / "data" / "ground"
LEVELS = 8
SIZE = 256
FALLOFF = 0.25  # outer 25% of radius fades to transparent
HEAT_COL = (255, 26, 51)  # WHOT-red [1.0, 0.10, 0.20] scaled to 8-bit


def alpha_at(dist_frac: float) -> int:
    """Radial alpha falloff: 255 in the solid centre, smoothstep to 0
    across the outer FALLOFF fraction of the radius.

    smoothstep avoids the Mach-band seam a linear falloff leaves at the
    blend boundary.
    """
    if dist_frac <= 1.0 - FALLOFF:
        return 255
    if dist_frac >= 1.0:
        return 0
    t = (dist_frac - (1.0 - FALLOFF)) / FALLOFF
    t = t * t * (3.0 - 2.0 * t)  # smoothstep
    return round(255 * (1.0 - t))


def make_tile(level: int) -> Image.Image:
    """One heat-colour tile with the radial alpha falloff."""
    scale = level / (LEVELS - 1)
    colour = tuple(round(c * scale) for c in HEAT_COL)
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = SIZE // 2
    radius = SIZE // 2 - 1
    # per-pixel falloff (ImageDraw ellipse has no per-pixel alpha)
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - cx, y - cy) / radius
            if d <= 1.0:
                img.putpixel((x, y), colour + (alpha_at(d),))
    return img


def convert(src: Path, dst: Path) -> None:
    subprocess.run(
        ["hemtt", "utils", "paa", "convert", str(src), str(dst)],
        check=True,
        capture_output=True,
    )


def verify_alpha(paa: Path) -> list[int]:
    """Read a PAA back (via hemtt) and return the alpha profile along
    the horizontal centre line: [solid-centre values, falloff values]."""
    png = paa.with_suffix(".png")
    convert(paa, png)
    img = Image.open(png).convert("RGBA")
    alpha = img.split()[3]
    cx = SIZE // 2
    line = []
    for x in range(SIZE):
        a = alpha.getpixel((x, cx))
        line.append(int(a))  # type: ignore[arg-type]
    png.unlink(missing_ok=True)
    return line


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    png_tmp = OUT_DIR / "_tile_tmp.png"
    for level in range(LEVELS):
        tile = make_tile(level)
        png_tmp = OUT_DIR / f"_tile_{level:02d}.png"
        tile.save(png_tmp)
        paa = OUT_DIR / f"ground_heat_{level:02d}.paa"
        convert(png_tmp, paa)
        png_tmp.unlink(missing_ok=True)

        profile = verify_alpha(paa)
        centre = profile[SIZE // 2]
        edge = profile[-1]
        # assertions: solid centre, transparent edge, monotone falloff
        assert centre == 255, f"{paa.name}: centre alpha {centre} != 255"
        assert edge == 0, f"{paa.name}: edge alpha {edge} != 0"
        falloff_zone = profile[int(SIZE * (1 - FALLOFF)) :]
        assert all(b <= a for a, b in zip(falloff_zone, falloff_zone[1:])), (
            f"{paa.name}: non-monotone falloff"
        )
        print(
            f"  {paa.name}: centre={centre} edge={edge} "
            f"falloff_start={falloff_zone[0]} falloff_end={falloff_zone[-1]}"
        )
    print(f"OK: {LEVELS} feathered tiles -> {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
