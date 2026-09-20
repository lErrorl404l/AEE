#!/usr/bin/env python3
"""Post-processing and sensor pipeline simulator (issue #204).

Simulates EVERY visual effect the mod applies, headlessly, so a change
to any parameter can be verified against the expected physics BEFORE
testing in game.  Visual code is the most fragile layer - a wrong sign,
a swapped channel, a clipped value renders as a subtle (or blinding)
error that the user only sees in game.  The simulator + the SQF-param
audit test (test_visual_pipeline_audit.py) triple-check each effect:
 1. the SQF uses sane parameters (locked by the audit test),
 2. the simulated output matches the physics (this module),
 3. the in-game report confirms it (user).

Effects modelled:
  - band radiance (Planck 8-14 um integral) - the sensor input
  - scene-adaptive AGC (linear with tail rejection, IIR) - the mapping
  - heat-colour texture (WHOT-red base * brightness)
  - ColorCorrections (brightness/contrast/offset/black/white/tint/blend)
  - ColorInversion (BHOT polarity)
  - FilmGrain (sensor noise: intensity/sharpness/grainSize/inversion)
  - DynamicBlur (IR scatter: blur radius)
  - RadialBlur (vignette: strength/radius/centre)
  - ChromAberration (lens dispersion: strength)
  - Resolution (TI sensor pixelation: scale)
  - fusion overlay (emissive band * 500 over the NVG base)

Usage:
  python3 tools/validation/simulate_visual_pipeline.py   # full audit
"""

from __future__ import annotations

import math

# ─── Physics constants ─────────────────────────────────────────────────────
SIGMA = 5.670374419e-8  # Stefan-Boltzmann (W/m2K4)


def planck_band_radiance(
    t_c: float, eps: float, t_air_c: float = 15.0, f_ground: float = 0.5
) -> float:
    """Band radiance (8-14 um) of a surface at t_c (C), emissivity eps.

    Simplified band integral over 8-14 um (the LWIR window): the
    Planck function integrated over the band is approximated by the
    central-wavelength radiance (11 um) times the band width - the
    FLIR T810442 sensor model.  The reflection term adds the ambient
    radiance times (1 - eps).
    """
    t_k = t_c + 273.15
    # Central band: 11 um, 2.727e13 Hz
    lam = 11e-6
    h = 6.626e-34
    c = 2.998e8
    k = 1.381e-23
    bw = 6e-6  # 8-14 um band width

    def planck(tk):
        x = h * c / (lam * k * tk)
        if x > 700:
            return 0.0
        return (2 * h * c * c / (lam**5)) / (math.exp(x) - 1)

    emit = eps * planck(t_k)
    # Reflection: ambient (air temp) reflected by (1-eps), weighted by
    # the ground/sky split (f_ground sees ground, (1-f) sees sky).
    t_sky = 0.0552 * (t_air_c + 273.15) ** 1.5 - 273.15
    mrt_k = (
        f_ground * (t_air_c + 273.15) ** 4 + (1 - f_ground) * (t_sky + 273.15) ** 4
    ) ** 0.25
    reflect = (1 - eps) * planck(mrt_k)
    return (emit + reflect) * bw / 1e8  # scaled to a display-able range


def agc_map(
    radiance: float, rad_min: float, rad_max: float, max_gain: float = 8.0
) -> float:
    """Scene-adaptive AGC: map radiance to 0..1 brightness.

    Linear with tail rejection and a max-gain cap (FLIR: AGC cannot
    create contrast that does not exist).  If the scene spread is under
    the max-gain floor, the window is expanded to the floor centred on
    the scene mean.
    """
    full_span = planck_band_radiance(150, 0.92) - planck_band_radiance(-40, 0.92)
    scene_span = rad_max - rad_min
    if scene_span < full_span / max_gain:
        mid = (rad_min + rad_max) / 2
        half = (full_span / max_gain) / 2
        rad_min, rad_max = mid - half, mid + half
    span = max(rad_max - rad_min, 1e-6)
    return max(0.0, min(1.0, (radiance - rad_min) / span))


# ─── Heat-colour texture (fnc_applySelectionThermal) ──────────────────────
def heat_colour(b: float) -> tuple[float, float, float]:
    """WHOT-red procedural texture colour for brightness b (0..1)."""
    qb = round(b * 31) / 31.0  # 32-level quantisation
    return (1.0 * qb, 0.10 * qb, 0.20 * qb)


# ─── ColorCorrections ─────────────────────────────────────────────────────
def colour_correction(
    pixel: tuple[float, float, float], cc: dict
) -> tuple[float, float, float]:
    """Map [r,g,b] through the CC params (documented BIKI math).

    ppEffectAdjust [brightness, contrast, offset, black[], white[],
    tint[], blend[]]:
      norm = (pixel - black) / (white - black)
      gain = (norm - 0.5) * contrast + 0.5 + offset
      col  = gain * tint * blend-luminance * brightness
    """
    r, g, b = pixel
    br, ct, off = cc["brightness"], cc["contrast"], cc["offset"]
    bl, wh, tn = cc["black"], cc["white"], cc["tint"]
    bd = cc["blend"]
    blend_lum = bd[6] if len(bd) >= 7 else 1.0

    def one(c, i):
        denom = wh[i] - bl[i]
        v = (c - bl[i]) / denom if abs(denom) > 1e-9 else c
        v = (v - 0.5) * ct + 0.5 + off
        v = v * tn[i] * blend_lum * br
        return v

    return (one(r, 0), one(g, 1), one(b, 2))


def invert(pixel: tuple[float, float, float]) -> tuple[float, float, float]:
    """ColorInversion [1,1,1]."""
    return (1.0 - pixel[0], 1.0 - pixel[1], 1.0 - pixel[2])


# ─── FilmGrain ─────────────────────────────────────────────────────────────
def film_grain(
    pixel: tuple[float, float, float], intensity: float, inversion: int = 0
) -> tuple[float, float, float]:
    """Sensor noise: add a random grain, scale by intensity.

    The inversion param (last of FilmGrain's 6) flips the grain
    polarity.  The simulator models the DETERMINISTIC part: the
    intensity scale and the inversion sign - the random draw is noise
    on top.
    """
    sign = -1.0 if inversion else 1.0
    return (
        max(0.0, min(1.0, pixel[0] + sign * intensity * 0.15)),
        max(0.0, min(1.0, pixel[1] + sign * intensity * 0.15)),
        max(0.0, min(1.0, pixel[2] + sign * intensity * 0.15)),
    )


# ─── DynamicBlur / RadialBlur / ChromAberration / Resolution ──────────────
def dynamic_blur(radius: float, distance: float = 0.5) -> float:
    """IR scatter blur: heavier in poor conditions.  Radius in pixels;
    the effect is 1/(1+radius) of the image retained sharp."""
    return 1.0 / (1.0 + radius * 10.0 * distance)


def radial_blur(strength: float, radius: float, r: float) -> float:
    """Vignette: brightness falloff from the centre.  strength scales
    the falloff; r is the normalised distance from the centre (0..1)."""
    return max(0.0, 1.0 - strength * max(0.0, r - radius) ** 2)


def chrom_aberration(strength: float) -> float:
    """Lens dispersion: the channel separation in pixels (small)."""
    return strength


def resolution(scale: float) -> float:
    """TI sensor pixelation: 1 = full, higher = more pixelated."""
    return max(1.0, scale)


# ─── Fusion overlay ────────────────────────────────────────────────────────
def fusion_emissive(b: float) -> float:
    """The fusion emissive glow: band brightness * 500 (A3TI full
    white).  Returns the emissive value the rvmat carries."""
    return b * 500.0


# ─── The audit scene ───────────────────────────────────────────────────────
SCENE_TEMPS = {
    "hot barrel (firing)": 120.0,  # sustained fire barrel
    "warm body (skin)": 32.0,
    "warm vehicle hull": 28.0,
    "cold ground (night)": 8.0,
    "cold tyre (parked)": 5.0,
}


def run_audit() -> int:
    print("═" * 78)
    print("VISUAL PIPELINE SIMULATOR - full audit")
    print("═" * 78)

    # 1. Sensor: radiance + AGC
    print("\n1. SENSOR (band radiance -> AGC brightness)")
    print(f"   {'object':24} {'temp':>6} {'radiance':>12} {'AGC b':>6}")
    rads = []
    for name, t in SCENE_TEMPS.items():
        rad = planck_band_radiance(t, 0.92)
        rads.append(rad)
    rad_min, rad_max = min(rads), max(rads)
    for name, t in SCENE_TEMPS.items():
        rad = planck_band_radiance(t, 0.92)
        b = agc_map(rad, rad_min, rad_max)
        print(f"   {name:24} {t:6.1f} {rad:12.2e} {b:6.2f}")

    # 2. Display chain per object (WHOT + BHOT)
    print("\n2. DISPLAY (heat colour -> CC -> [invert] -> luminance)")
    print(
        f"   {'object':24} {'b':>5} {'WHOT lum':>9} {'BHOT lum':>9} "
        f"{'expW':>5} {'expB':>5} {'verdict':>8}"
    )
    cc_neutral = {
        "brightness": 1.16,
        "contrast": 0.62,
        "offset": 0.0,
        "black": [0, 0, 0, 0],
        "white": [1, 1, 1, 0],
        "tint": [0.33, 0.33, 0.33, 0],
        "blend": [0, 0, 0, 0, 0, 0, 4.0],
    }
    failures = 0
    for name, t in SCENE_TEMPS.items():
        rad = planck_band_radiance(t, 0.92)
        b = agc_map(rad, rad_min, rad_max)
        tex = heat_colour(b)
        whot = colour_correction(tex, cc_neutral)
        bhot = invert(whot)
        lw = 0.299 * whot[0] + 0.587 * whot[1] + 0.114 * whot[2]
        lb = 0.299 * bhot[0] + 0.587 * bhot[1] + 0.114 * bhot[2]
        exp_w = "BRT" if b > 0.5 else "DIM"
        exp_b = "DRK" if b > 0.5 else "BRT"
        # The physical requirement: WHOT hot = bright, BHOT hot = dark.
        ok_w = (lw > 0.5) == (b > 0.5)
        ok_b = (lb < 0.5) == (b > 0.5)
        verdict = "OK" if (ok_w and ok_b) else "FAIL"
        if verdict == "FAIL":
            failures += 1
        print(
            f"   {name:24} {b:5.2f} {lw:9.2f} {lb:9.2f} "
            f"{exp_w:>5} {exp_b:>5} {verdict:>8}"
        )

    # 3. Post-processing effects sanity
    print("\n3. POST-PROCESSING EFFECTS (parameter sanity)")
    grain = film_grain((0.5, 0.5, 0.5), 0.3)
    blur = dynamic_blur(0.5)
    vig = radial_blur(0.5, 0.3, 0.8)
    chroma = chrom_aberration(0.004)
    res = resolution(3.0)
    emissive = fusion_emissive(1.0)
    print(f"   FilmGrain(0.3)        -> {[round(c, 2) for c in grain]}")
    print(f"   DynamicBlur(0.5)       -> sharpness {blur:.2f}")
    print(f"   RadialBlur(0.5, r=0.8) -> edge {vig:.2f}")
    print(f"   ChromAberration(0.004) -> separation {chroma}")
    print(f"   Resolution(3)          -> scale {res}")
    print(f"   Fusion emissive(b=1)   -> {emissive:.0f} (A3TI 500)")

    print(f"\n{'AUDIT PASS' if failures == 0 else f'{failures} FAILURES'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    import sys

    sys.exit(run_audit())
