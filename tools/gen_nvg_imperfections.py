#!/usr/bin/env python3
"""Generate the two NVG imperfection overlay textures (issue #215).

Regeneration (deterministic - a fixed seed makes byte-identical PNGs):

    python3 tools/gen_nvg_imperfections.py
    hemtt utils paa convert addons/nightvision/data/nvg_blemishes.png addons/nightvision/data/nvg_blemishes.paa
    hemtt utils paa convert addons/nightvision/data/nvg_reticulation.png addons/nightvision/data/nvg_reticulation.paa

The PNGs are the reproducible source and are committed.  The PAAs are the
shipped assets and are committed.  Do not hand-edit a PAA.

Sources for the generated features (the per-constant register is in
.omo/plans/aee-nvg-imperfections.md and docs/wiki/research/nvg-imperfections-dossier.md):

  - Dark spot classes and zone density: MIL-I-49428(CR) 06-NOV-1989
    Table III and section 3.6.21 (the 30 percent contrast threshold).
  - Bright emission points: MIL-I-49428 section 3.11.19, <=10 type-B
    ion-barrier holes per tube (8 are drawn).
  - Fixed-pattern noise amplitude: MIL-I-49428 section 3.6.12, <=+/-10
    percent multi-to-multi.
  - Fibre-optic reticulation pitch: Hamamatsu F1094-077 datasheet
    TMCPB0106E (6 um channel, 7.5 um pitch); MIL-I-49428 section 3.11.4
    (chicken-wire fibre diameter <=0.0009 in, ~22.9 um).

UNSOURCED modelling choices are marked beside the value.  The physical
MCP/fibre pitch (7.5-22.9 um on an 18 mm tube face) is sub-pixel at this
texture resolution, so the honeycomb is drawn at a representable pitch as
a modelling choice, not a measured value.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 1024  # texture is the tube square
SEED = 0xAEE215  # fixed: byte-identical regeneration
CENTER = SIZE / 2.0
FACE_R = SIZE / 2.0  # circular tube-face mask: nothing draws outside it
DATA = Path(__file__).resolve().parents[1] / "addons" / "nightvision" / "data"

DARK_SPOTS = 28  # MIL-I-49428 Table III density ORDER (UNSOURCED normalisation)
BRIGHT_POINTS = 8  # MIL-I-49428 section 3.11.19 bound is <=10
RETICULE_R = 5.0  # hex cell radius, px (UNSOURCED representability choice)
RETICULE_ALPHA = 26  # low alpha: the lattice reads as a fine tint


def _in_face(x: float, y: float) -> bool:
    return math.hypot(x - CENTER, y - CENTER) <= FACE_R


def _mask_to_face(img: Image.Image) -> Image.Image:
    """Zero the alpha outside the circular tube-face mask."""
    alpha = img.getchannel("A")
    px = alpha.load()
    for y in range(SIZE):
        for x in range(SIZE):
            if not _in_face(x + 0.5, y + 0.5):
                px[x, y] = 0
    img.putalpha(alpha)
    return img


def _draw_blemishes() -> Image.Image:
    """Texture A: dark spots, bright emission points and FPN mottle."""
    rng = random.Random(SEED)
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fixed-pattern mottle: a coarse low-contrast field, amplitude <=+/-10
    # percent (MIL-I-49428 section 3.6.12).  Drawn as a faint fixed
    # darkening so it shifts contrast, not brightness.
    mottle = Image.new("L", (32, 32))
    mottle.putdata([rng.randint(0, 255) for _ in range(32 * 32)])
    mottle = mottle.resize((SIZE, SIZE), Image.BICUBIC)
    malpha = Image.eval(mottle, lambda v: int(abs(v - 128) / 128 * 22))
    black = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))
    black.putalpha(malpha)
    img = Image.alpha_composite(img, black)
    draw = ImageDraw.Draw(img)

    # Dark spots: zone density rises outward (Table III order).  The exact
    # per-spot radii and alphas are an UNSOURCED visual realisation.
    zones = ((FACE_R / 3.0, 4), (2.0 * FACE_R / 3.0, 9), (FACE_R, DARK_SPOTS - 4 - 9))
    for outer, count in zones:
        for _ in range(count):
            placed = False
            for _ in range(200):
                ang = rng.uniform(0, 2 * math.pi)
                rad = math.sqrt(rng.uniform(0, 1)) * outer
                x = CENTER + rad * math.cos(ang)
                y = CENTER + rad * math.sin(ang)
                r = rng.uniform(3.0, 9.0)  # UNSOURCED radius
                if _in_face(x, y) and _in_face(x + r, y) and _in_face(x, y + r):
                    draw.ellipse(
                        [x - r, y - r, x + r, y + r],
                        fill=(0, 0, 0, rng.randint(40, 90)),
                    )
                    placed = True
                    break
            if not placed:
                raise AssertionError("dark spot could not be placed inside the face")

    # Bright emission points (type-B holes), alpha 60..120, <=10 per tube.
    for _ in range(BRIGHT_POINTS):
        for _ in range(200):
            ang = rng.uniform(0, 2 * math.pi)
            rad = math.sqrt(rng.uniform(0, 1)) * FACE_R * 0.92
            x = CENTER + rad * math.cos(ang)
            y = CENTER + rad * math.sin(ang)
            r = rng.uniform(1.0, 3.0)  # UNSOURCED radius
            if _in_face(x, y) and _in_face(x + r, y) and _in_face(x, y + r):
                draw.ellipse(
                    [x - r, y - r, x + r, y + r],
                    fill=(255, 255, 255, rng.randint(60, 120)),
                )
                break
        else:
            raise AssertionError("bright point could not be placed inside the face")

    return _mask_to_face(img)


def _draw_reticulation() -> Image.Image:
    """Texture B: subtle hexagonal honeycomb lattice, low alpha."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Pointy-top hexagon grid: horizontal spacing sqrt(3)*r, vertical 1.5*r.
    dx = math.sqrt(3.0) * RETICULE_R
    dy = 1.5 * RETICULE_R
    vertices = [
        (
            RETICULE_R * math.cos(math.radians(60 * k + 30)),
            RETICULE_R * math.sin(math.radians(60 * k + 30)),
        )
        for k in range(6)
    ]
    row = 0
    y = 0.0
    while y <= SIZE + RETICULE_R:
        x = 0.0 if row % 2 == 0 else dx / 2.0
        while x <= SIZE + dx:
            pts = [(x + vx, y + vy) for vx, vy in vertices]
            if _in_face(x, y):
                draw.polygon(pts, outline=(0, 0, 0, RETICULE_ALPHA))
            x += dx
        y += dy
        row += 1

    return _mask_to_face(img)


def _non_transparent(img: Image.Image) -> int:
    return sum(1 for a in img.getchannel("A").tobytes() if a > 0)


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)

    blemishes = _draw_blemishes()
    reticulation = _draw_reticulation()

    blemishes.save(DATA / "nvg_blemishes.png")
    reticulation.save(DATA / "nvg_reticulation.png")

    assert blemishes.mode == "RGBA" and reticulation.mode == "RGBA"
    assert _non_transparent(blemishes) >= 200, "blemish texture is nearly empty"
    assert _non_transparent(reticulation) >= 200, "reticulation texture is nearly empty"
    assert BRIGHT_POINTS <= 10, (
        "MIL-I-49428 section 3.11.19 allows at most 10 bright points"
    )

    # No non-transparent pixel may lie outside the circular face.
    for img in (blemishes, reticulation):
        alpha = img.getchannel("A").load()
        for y in range(SIZE):
            for x in range(SIZE):
                if alpha[x, y] > 0 and not _in_face(x + 0.5, y + 0.5):
                    raise AssertionError(f"pixel ({x},{y}) is outside the face mask")

    print(f"nvg_blemishes.png   black={_non_transparent(blemishes)} non-transparent px")
    print(
        f"nvg_reticulation.png black={_non_transparent(reticulation)} non-transparent px"
    )
    print(f"dark spots={DARK_SPOTS} bright points={BRIGHT_POINTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
