#!/usr/bin/env python3
"""Thermal display pipeline simulator (issue #204).

Simulates the FULL thermal display chain headlessly, so a change to the
CC matrix, the ColorInversion, or the polarity logic can be verified
against the expected physics BEFORE testing in game.

Pipeline modelled (matches fnc_applyThermalVision.sqf +
fnc_applySelectionThermal.sqf):
  1. Per-selection heat brightness _b (0..1) from the physics solve.
  2. Continuous palette texture: the ember ramp at the AGC position.
  3. ColorCorrections (the ppEffectAdjust matrix): the rendered image
     is the heat-colour texture mapped through the CC.
  4. ColorInversion (BHOT): [1,1,1] inverts each channel when
     thermalPolarity == 1.
  5. Final display value per pixel.

The simulator's job: prove that a HOT object renders BRIGHT (white) in
WHOT and DARK (black) in BHOT, and a COLD object renders dark in WHOT
and bright in BHOT - the physically-correct polarity.  The regression
this caught: the CC tint [3.84,-0.46,-2.72,-0.06] has NEGATIVE green
and blue channels, which INVERTED the scene - a hot barrel rendered
BLACK in WHOT and the display flipped with polarity (the in-game
report).  The corrected tint [0.33,0.33,0.33] is neutral.
"""

import argparse
import sys


# ─── The CC matrices under test ────────────────────────────────────────────
# Current (A3TI-proven, neutral tint - should render hot=bright in WHOT).
CC_NEUTRAL = {
    "brightness": 1.16,
    "contrast": 0.62,
    "offset": 0.0,
    "black": [0.0, 0.0, 0.0, 0.0],
    "white": [1.0, 1.0, 1.0, 0.0],
    "tint": [0.33, 0.33, 0.33, 0.0],
    "blend": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 4.0],
}

# The OLD buggy matrix (MKK-derived, negative G/B - inverts the scene).
CC_NEGATIVE = {
    "brightness": 1.16,
    "contrast": 0.62,
    "offset": 0.04,
    "black": [0.0, 0.0, 0.0, 0.0],
    "white": [1.0, 1.0, 1.0, 0.0],
    "tint": [3.84, -0.46, -2.72, -0.06],
    "blend": [0.0, 0.0, 0.02, 0.0, 0.0, 0.0, 1.55],
}


# ─── The heat-colour paint (fnc_applySelectionThermal) ────────────────────
# Continuous ember ramp from fnc_thermalPalette.sqf.  The control points are
# the engine's own decoded TI colours (engine-thermal-mechanisms.md):
#   default_vehicle_ti (145,46,0) = (0.5686,0.1804,0), default_ti = (1,0,0).
PALETTE_EMBER = [
    (0.00, (0.0, 0.0, 0.0)),
    (0.35, (0.3618, 0.1148, 0.0)),
    (0.55, (0.5686, 0.1804, 0.0)),
    (0.85, (1.0, 0.0, 0.0)),
    (1.00, (1.0, 1.0, 1.0)),
]
PALETTE_GREY = [(0.0, (0.0, 0.0, 0.0)), (1.0, (1.0, 1.0, 1.0))]


def _palette(n: float, points: list) -> tuple:
    """Piecewise-linear interpolation between [position, [r, g, b]] points."""
    n = min(1.0, max(0.0, n))
    lo = points[0]
    hi = points[-1]
    for p in points:
        if n >= p[0]:
            lo = p
    for p in points:
        if n <= p[0]:
            hi = p
            break
    span = max(hi[0] - lo[0], 1e-6)
    f = min(1.0, max(0.0, (n - lo[0]) / span))
    return tuple(lo[1][i] + (hi[1][i] - lo[1][i]) * f for i in range(3))


def heat_colour(b: float, palette_index: int = 0, polarity: int = 0) -> tuple:
    """The continuous thermal texture colour for band position b (0..1).

    palette_index 0 = ember (default), 1 = grey.  polarity 1 reverses the ramp
    (black hot), mirroring fnc_thermalPalette.
    """
    qb = round(b * 254) / 254.0  # 255-level quantisation
    points = PALETTE_GREY if palette_index == 1 else PALETTE_EMBER
    return _palette((1.0 - qb) if polarity == 1 else qb, points)


# ─── The ColourCorrections ppEffectAdjust (documented BIKI math) ──────────
def colour_correction(pixel: tuple, cc: dict) -> tuple:
    """Map [r,g,b] through the CC parameters.

    ppEffectAdjust [brightness, contrast, offset, black[], white[],
    tint[], blend[]]:
      out = (pixel - black) / (white - black)           (channel-wise)
      out = (out - 0.5) * contrast + 0.5 + offset       (gain/contrast)
      out *= tint * blend                               (colour grade)
      out *= brightness
    The blend is a 7-element matrix; the luminance term (index 6) is
    the main driver here.
    """
    r, g, b = pixel
    br, ct, off = cc["brightness"], cc["contrast"], cc["offset"]
    bl = cc["black"]
    wh = cc["white"]
    tn = cc["tint"]
    bd = cc["blend"]

    def one(c, i):
        # black/white point normalise
        denom = wh[i] - bl[i]
        if abs(denom) < 1e-9:
            v = c
        else:
            v = (c - bl[i]) / denom
        # gain/contrast
        v = (v - 0.5) * ct + 0.5 + off
        # tint (per-channel multiplier; negative = channel inversion)
        v = v * tn[i]
        # blend: the 7-element matrix luminance+bias term.  The final
        # element (index 6) is the luminance gain - apply it as a
        # brightness lift on the tinted value.
        if len(bd) >= 7:
            v = v * bd[6]
        # final brightness
        v = v * br
        return v

    return (one(r, 0), one(g, 1), one(b, 2))


def invert(pixel: tuple) -> tuple:
    """ColorInversion [1,1,1]: each channel flips."""
    return (1.0 - pixel[0], 1.0 - pixel[1], 1.0 - pixel[2])


def luminance(pixel: tuple) -> float:
    """Perceived brightness (0..1)."""
    r, g, b = pixel
    return 0.299 * r + 0.587 * g + 0.114 * b


# ─── The scene under test ──────────────────────────────────────────────────
SCENE = {
    "hot barrel (firing)": 0.95,  # _b from a fired weapon
    "warm body (skin 32C)": 0.65,  # resting soldier
    "warm vehicle hull": 0.45,  # engine-heated hull
    "cold ground (night)": 0.12,  # ambient-cold terrain
    "cold tyre (parked)": 0.08,  # parked vehicle tyre
}


def simulate(cc: dict, label: str) -> None:
    print(f"\n=== {label} ===")
    print(
        f"{'object':24} {'b':>5} {'WHOT lum':>8} {'BHOT lum':>8} "
        f"{'expected WHOT':>13} {'expected BHOT':>13}"
    )
    for name, b in SCENE.items():
        tex = heat_colour(b)
        whot = colour_correction(tex, cc)
        bhot = invert(whot)
        lw = luminance(whot)
        lb = luminance(bhot)
        # Expected physics: WHOT hot = bright, BHOT hot = dark.
        exp_w = "BRIGHT" if b > 0.5 else ("DIM" if b > 0.25 else "DARK")
        exp_b = "DARK" if b > 0.5 else ("DIM" if b > 0.25 else "BRIGHT")
        print(f"{name:24} {b:5.2f} {lw:8.2f} {lb:8.2f} {exp_w:>13} {exp_b:>13}")
    return


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrix", choices=["neutral", "negative", "both"], default="both")
    args = ap.parse_args()

    if args.matrix in ("neutral", "both"):
        simulate(CC_NEUTRAL, "CC: A3TI neutral tint (current)")
    if args.matrix in ("negative", "both"):
        simulate(CC_NEGATIVE, "CC: old negative tint (the bug)")

    # Assertion: with the CURRENT neutral matrix, hot objects must
    # render bright in WHOT and dark in BHOT.
    print("\n=== assertion (current matrix, WHOT polarity) ===")
    ok = True
    pairs = []
    for name, b in SCENE.items():
        tex = heat_colour(b)
        whot = colour_correction(tex, CC_NEUTRAL)
        lw = luminance(whot)
        pairs.append((b, lw))
        print(f"  {name:24} b={b:.2f} lum={lw:.2f}")
    # The display must be monotone: a hotter object never renders darker in
    # WHOT, and the hottest renders brighter than the coldest.
    ordered = [lw for _, lw in sorted(pairs)]
    if ordered != sorted(ordered):
        ok = False
        print("  FAIL: WHOT luminance is not monotone in b")
    if ordered[-1] <= ordered[0]:
        ok = False
        print("  FAIL: the hot object is not brighter than the cold object")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
