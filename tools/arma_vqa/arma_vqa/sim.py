"""Approximate offline renderer for Arma 3 post-process stacks and thermal output.

IMPORTANT - what this is and is not
-----------------------------------
The Arma 3 post-process shaders are not public. This module implements a
*model*: the documented meaning of each parameter (e.g. ColorCorrections
brightness 1 = unchanged, TI output = Start + t * Width) driven through
plausible formulas, applied in priority order to a synthetic test scene.

* TI output-range maths and Resolution are straight from the wiki.
* ColorCorrections ordering of operations, vignette (radial) geometry, grain,
  blur, chromatic aberration, radial blur and wet distortion *scales* are
  assumptions. Metrics derived from those carry "model" / "uncalibrated"
  confidence and their findings are capped (see SIM rules).
* SSAO, HBAOPlus and LightShafts need depth / sun information and are not
  simulated.

Use it to catch gross problems (crushed blacks, clipped whites, lost tonal
range, washed-out or monochrome results, compounding stacks) without starting
the game, and to compare variants. Calibrate against in-game screenshots with
`calibration.json` (see README) before trusting absolute numbers.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .analyze import Instance, Result
from .catalog import RULES, cap
from .rules import Rules, defaults_of, pack_color_corrections
from .sqf import UNKNOWN

W, H = 480, 270
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

DEFAULT_CAL = {
    "blur_sigma_per_unit": 2.5,       # DynamicBlur value -> gaussian sigma in px @ 480 wide  (UNCALIBRATED)
    "grain_amp_per_unit": 0.5,        # FilmGrain intensity -> noise std                       (UNCALIBRATED)
    "chroma_shift_scale": 1.0,        # ChromAberration power -> shift (fraction of width)     (UNCALIBRATED)
    "radial_blur_scale": 3.0,         # RadialBlur power -> zoom span                          (UNCALIBRATED)
    "wet_scale": 1.0,                 # WetDistortion amplitude multiplier                     (UNCALIBRATED)
    # ColorCorrections structure. The wiki gives parameter meanings but not the maths, so there are
    # selectable models; `arma_vqa calibrate` picks the one that matches real in-game screenshots.
    #   desat_first (default): desaturate/tint -> contrast about cc_pivot -> brightness -> offset -> blend.
    #       Chosen because it reproduces the wiki's own examples: the "Black & White" example uses desat weights
    #       [1,1,1] (sum 3) with contrast 0.4 (~1/3), which only gives a sane image if desaturation happens
    #       BEFORE a multiplicative contrast; and "brightness 0 = black, 2 = white" implies an additive shift.
    #   legacy: brightness*, contrast about 0.5, offset, then desaturate. Blows out the wiki's B&W example.
    "cc_model": "desat_first",
    "cc_pivot": 0.0,                  # contrast pivot (desat_first only)                       (UNCALIBRATED)
    "cc_brightness": "additive",      # additive: c + (b-1)   multiplicative: c * b            (UNCALIBRATED)
}


def load_calibration(path: str | None) -> dict:
    cal = dict(DEFAULT_CAL)
    cal["calibrated"] = False
    if path:
        with open(path, encoding="utf-8") as f:
            cal.update(json.load(f))
        cal["calibrated"] = True
    return cal


# ---------------------------------------------------------------------------
# synthetic scene
# ---------------------------------------------------------------------------
def make_scene(w: int = W, h: int = H) -> tuple[np.ndarray, dict]:
    rng = np.random.default_rng(7)
    img = np.zeros((h, w, 3), np.float32)
    horizon = int(h * 0.42)
    ty = np.linspace(0, 1, horizon, dtype=np.float32)[:, None, None]
    img[:horizon] = np.array([0.22, 0.42, 0.82], np.float32) * (1 - ty) + np.array([0.78, 0.86, 0.95], np.float32) * ty
    # ground with texture
    gy = np.linspace(0, 1, h - horizon, dtype=np.float32)[:, None, None]
    ground = np.array([0.30, 0.38, 0.17], np.float32) * (1 - gy) + np.array([0.20, 0.17, 0.10], np.float32) * gy
    tex = rng.normal(0, 0.035, (h - horizon, w, 1)).astype(np.float32)
    img[horizon:] = ground + tex
    # treeline silhouette
    xs = np.arange(w)
    tree_h = (6 + 5 * np.sin(xs / 9.0) + 4 * np.sin(xs / 3.7 + 1)).astype(int)
    for x in range(w):
        y0 = max(0, horizon - tree_h[x])
        img[y0:horizon + 2, x] = np.array([0.08, 0.16, 0.07], np.float32)
    # sun (over-bright) top right
    yy, xx = np.mgrid[0:h, 0:w]
    sun = np.exp(-(((xx - w * 0.82) ** 2 + (yy - h * 0.12) ** 2) / (2 * 9.0 ** 2)))[..., None].astype(np.float32)
    img = img + sun * np.array([1.0, 0.95, 0.8], np.float32)
    # high-contrast "building" with edge detail
    bx0, bx1, by0, by1 = int(w * 0.08), int(w * 0.30), int(h * 0.20), int(h * 0.62)
    img[by0:by1, bx0:bx1] = np.array([0.55, 0.52, 0.48], np.float32)
    for k in range(6):
        for m in range(4):
            x0 = bx0 + 8 + k * 14
            y0 = by0 + 8 + m * 18
            img[y0:y0 + 8, x0:x0 + 8] = 0.04
    # skin-tone ellipse + olive uniform block
    cx, cy = int(w * 0.52), int(h * 0.55)
    face = (((xx - cx) / 17.0) ** 2 + ((yy - cy) / 22.0) ** 2) < 1
    img[face] = np.array([0.80, 0.58, 0.46], np.float32)
    img[cy + 22:cy + 52, cx - 24:cx + 24] = np.array([0.23, 0.26, 0.14], np.float32)
    # flat mid-grey patch (grain meter)
    gx0, gx1, gy0, gy1 = int(w * 0.36), int(w * 0.44), int(h * 0.12), int(h * 0.30)
    img[gy0:gy1, gx0:gx1] = 0.5
    # shadow region
    img[int(h * 0.68):int(h * 0.78), int(w * 0.60):int(w * 0.80)] = 0.02
    # bottom strip: grey ramp (top half) + colour patches (bottom half)
    sh = int(h * 0.14)
    s0 = h - sh
    ramp = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    img[s0:s0 + sh // 2] = ramp
    cols = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 1, 1), (1, 0, 1), (1, 1, 0), (0.8, 0.58, 0.46), (0.25, 0.4, 0.15), (0.5, 0.5, 0.5)]
    pw = w // len(cols)
    for i, c in enumerate(cols):
        img[s0 + sh // 2:, i * pw:(i + 1) * pw] = np.array(c, np.float32)
    img = np.clip(img, 0, 1)
    regions = {
        "ramp": (s0, s0 + sh // 2),
        "grain_patch": (gy0, gy1, gx0, gx1),
        "detail": (by0, by1, bx0, bx1),
    }
    return img, regions


# ---------------------------------------------------------------------------
# effects
# ---------------------------------------------------------------------------
def _pil(img: np.ndarray) -> Image.Image:
    return Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8))


def _arr(im: Image.Image) -> np.ndarray:
    return np.asarray(im, dtype=np.float32) / 255.0


def _num(v, d):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else float(d)


def _col(v, d):
    if not isinstance(v, list):
        return list(d)
    return [_num(v[i] if i < len(v) else d[i], d[i]) for i in range(4)]


def fx_color_corrections(img, p, cal):
    br, ct, off = _num(p[0], 1), _num(p[1], 1), _num(p[2], 0)
    blend = _col(p[3], [0, 0, 0, 0])
    colz = _col(p[4], [1, 1, 1, 1])
    wts = _col(p[5], [0.299, 0.587, 0.114, 0])
    w3 = np.array(wts[:3], np.float32)
    col = np.array(colz[:3], np.float32)
    if cal.get("cc_model", "desat_first") == "legacy":
        c = img * br
        c = (c - 0.5) * ct + 0.5
        c = c + off
        g = (c * w3).sum(-1, keepdims=True)
        c = g * col * (1 - colz[3]) + c * col * colz[3]
    else:
        g = (img * w3).sum(-1, keepdims=True)           # weights are NOT normalised (wiki B&W example: [1,1,1])
        c = g * col * (1 - colz[3]) + img * col * colz[3]
        pv = float(cal.get("cc_pivot", 0.0))
        c = (c - pv) * ct + pv
        c = c + (br - 1.0) if cal.get("cc_brightness", "additive") == "additive" else c * br
        c = c + off
    c = c * (1 - blend[3]) + np.array(blend[:3], np.float32) * blend[3]
    c = np.clip(c, 0, 1)
    if len(p) > 6 and isinstance(p[6], list) and len(p[6]) >= 7:
        a, b, ang, cx, cy, inner, _interp = [_num(x, 0) for x in p[6][:7]]
        if a > 0 and b > 0:
            h, w = img.shape[:2]
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            x = xx / w - 0.5 - cx
            y = (yy / h - 0.5 - cy) * (h / w)
            th = np.deg2rad(ang)
            xr = x * np.cos(th) + y * np.sin(th)
            yr = -x * np.sin(th) + y * np.cos(th)
            d = np.sqrt((xr / max(a, 1e-3)) ** 2 + (yr / max(b, 1e-3)) ** 2)
            t = np.clip((d - inner) / max(1 - inner, 1e-3), 0, 1)[..., None]
            c = img * (1 - t) + c * t
    return c


def fx_dynamic_blur(img, p, cal):
    sigma = min(_num(p[0], 0) * cal["blur_sigma_per_unit"], 30.0)
    if sigma <= 0.05:
        return img
    return _arr(_pil(img).filter(ImageFilter.GaussianBlur(radius=sigma)))


def fx_film_grain(img, p, cal):
    inten = _num(p[0], 0.005)
    size = max(1.0, _num(p[2] if len(p) > 2 else 2.01, 2.01))
    x0 = _num(p[3] if len(p) > 3 else 0.75, 0.75)
    x1 = _num(p[4] if len(p) > 4 else 1.0, 1.0)
    mono_val = p[5] if len(p) > 5 else 0
    mono = (mono_val is True) or (isinstance(mono_val, (int, float)) and mono_val == 0) or mono_val is False
    h, w = img.shape[:2]
    rng = np.random.default_rng(11)
    sh, sw = max(1, int(h / size)), max(1, int(w / size))
    shape = (sh, sw, 1) if mono else (sh, sw, 3)
    n = rng.normal(0, 1, shape).astype(np.float32)
    n = np.stack([np.asarray(Image.fromarray(n[..., k]).resize((w, h), Image.BILINEAR)) for k in range(n.shape[2])], -1)
    luma = (img * LUMA).sum(-1, keepdims=True)
    weight = x0 + (x1 - x0) * luma
    return np.clip(img + n * inten * cal["grain_amp_per_unit"] * weight, 0, 1)


def fx_color_inversion(img, p, cal):
    inv = np.array([_num(p[0], 0), _num(p[1], 0), _num(p[2], 0)], np.float32)
    return img * (1 - inv) + (1 - img) * inv


def _shift(ch: np.ndarray, dx: int, dy: int) -> np.ndarray:
    h, w = ch.shape
    ys = np.clip(np.arange(h) - dy, 0, h - 1)
    xs = np.clip(np.arange(w) - dx, 0, w - 1)
    return ch[np.ix_(ys, xs)]


def fx_chrom_aberration(img, p, cal):
    h, w = img.shape[:2]
    dx = int(round(_num(p[0], 0.005) * w * cal["chroma_shift_scale"]))
    dy = int(round(_num(p[1], 0.005) * h * cal["chroma_shift_scale"]))
    out = img.copy()
    out[..., 0] = _shift(img[..., 0], dx, dy)
    out[..., 2] = _shift(img[..., 2], -dx, -dy)
    return out


def fx_radial_blur(img, p, cal):
    h, w = img.shape[:2]
    px, py = _num(p[0], 0.01), _num(p[1], 0.01)
    ox, oy = _num(p[2], 0.06), _num(p[3], 0.06)
    span = max(px, py) * cal["radial_blur_scale"]
    if span <= 1e-4:
        return img
    base = _pil(img)
    acc = np.zeros_like(img)
    n = 8
    for k in range(n):
        s = 1 + span * k / (n - 1)
        r = base.resize((int(w * s), int(h * s)), Image.BILINEAR)
        l, t = (r.width - w) // 2, (r.height - h) // 2
        acc += _arr(r.crop((l, t, l + w, t + h)))
    acc /= n
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx / w - 0.5) / max(ox * 4, 1e-3)) ** 2 + ((yy / h - 0.5) / max(oy * 4, 1e-3)) ** 2)
    m = np.clip(d - 1, 0, 1)[..., None]
    return img * (1 - m) + acc * m


def fx_wet(img, p, cal):
    h, w = img.shape[:2]
    val = _num(p[0], 1)
    top, bot = _num(p[1], 1), _num(p[2], 1)
    ha1, ha2, va1, va2 = [_num(p[i], 0.005) for i in (7, 8, 9, 10)]
    posx, posy = _num(p[13], 10), _num(p[14], 6)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ny, nx = yy / h, xx / w
    wgt = (top * (1 - ny) + bot * ny) * min(val, 1.0)
    dx = (ha1 * np.sin(ny * posy * 2 * np.pi) + ha2 * np.sin(ny * posy * 3.4 * np.pi + 1.3)) * w * cal["wet_scale"] * wgt * 4
    dy = (va1 * np.sin(nx * posx * 2 * np.pi) + va2 * np.sin(nx * posx * 3.4 * np.pi + 0.7)) * h * cal["wet_scale"] * wgt * 4
    sx = np.clip((xx + dx).round().astype(int), 0, w - 1)
    sy = np.clip((yy + dy).round().astype(int), 0, h - 1)
    return img[sy, sx]


def fx_resolution(img, p, cal):
    h, w = img.shape[:2]
    v = _num(p[0], -1)
    if v <= 0 or v >= h:
        return img
    nw = max(1, int(round(w * v / h)))
    small = _pil(img).resize((nw, int(v)), Image.BILINEAR)
    return _arr(small.resize((w, h), Image.NEAREST))


def fx_sharpness(img, p, cal):
    s = _num(p[0], 0)
    if s <= 0:
        return img
    blur = _arr(_pil(img).filter(ImageFilter.GaussianBlur(radius=1.2)))
    return np.clip(img + s * (img - blur), 0, 1)


def fx_invert_ti(img, p, cal):  # not used; placeholder to keep table explicit
    return img


FX = {
    "ColorCorrections": fx_color_corrections,
    "DynamicBlur": fx_dynamic_blur,
    "FilmGrain": fx_film_grain,
    "ColorInversion": fx_color_inversion,
    "ChromAberration": fx_chrom_aberration,
    "RadialBlur": fx_radial_blur,
    "WetDistortion": fx_wet,
    "Resolution": fx_resolution,
    "Sharpness": fx_sharpness,
}
NOT_SIMULATED = {"SSAO", "HBAOPlus", "LightShafts"}
BLURRING = {"DynamicBlur", "RadialBlur", "WetDistortion", "Resolution"}


# ---------------------------------------------------------------------------
# scenarios
# ---------------------------------------------------------------------------
@dataclass
class SimItem:
    effect: str
    params: list
    priority: float
    label: str
    file: str
    line: int
    assumed_priority: bool = False
    unresolved: int = 0


@dataclass
class Scenario:
    name: str
    items: list[SimItem] = field(default_factory=list)
    kind: str = "pp"  # pp | ti
    ti: dict | None = None
    origin: str = ""


def _flat_numbers(v):
    if isinstance(v, list):
        for x in v:
            yield from _flat_numbers(x)
    elif isinstance(v, (int, float)) and not isinstance(v, bool):
        yield float(v)
    else:
        yield None


def _deviation(rules: Rules, effect: str, params: list) -> float:
    d = list(_flat_numbers(defaults_of(rules, effect)))
    p = list(_flat_numbers(params))
    tot = 0.0
    for a, b in zip(p, d):
        if a is None or b is None:
            continue
        tot += abs(a - b) / max(1.0, abs(b))
    return tot


def _fill(rules: Rules, effect: str, params: list) -> tuple[list, int]:
    """Fill UNKNOWN / missing entries with defaults. Returns (params, unresolved_count)."""
    spec = rules.effects[effect]
    if effect == "ColorCorrections":
        params, _ = pack_color_corrections(params)
    out: list = []
    unresolved = 0
    for k, ps in enumerate(spec["params"]):
        if k < len(params):
            v = params[k]
            if v is UNKNOWN:
                out.append(ps["default"])
                unresolved += 1
            elif isinstance(v, list) and isinstance(ps["default"], list):
                dv = ps["default"]
                row = []
                for i, dflt in enumerate(dv):
                    x = v[i] if i < len(v) else dflt
                    if x is UNKNOWN:
                        unresolved += 1
                        x = dflt
                    row.append(x)
                out.append(row)
            else:
                out.append(v)
        elif not ps.get("optional"):
            out.append(ps["default"])
    return out, unresolved


def _peak_item(rules: Rules, inst: Instance) -> SimItem | None:
    if not inst.effect or inst.effect in NOT_SIMULATED:
        return None
    best = None
    best_dev = -1.0
    for op in inst.adjusts:
        if not isinstance(op.value, list):
            continue
        filled, unresolved = _fill(rules, inst.effect, op.value)
        dev = _deviation(rules, inst.effect, filled)
        if dev > best_dev:
            best_dev, best = dev, (filled, unresolved, op)
    if best is None:
        return None
    filled, unresolved, op = best
    base = rules.effects[inst.effect]["base_priority"]
    assumed = not isinstance(inst.priority, (int, float)) or isinstance(inst.priority, bool)
    prio = float(base if assumed and base is not None else (inst.priority if not assumed else 0))
    return SimItem(inst.effect, filled, prio, inst.label, op.file, op.line, assumed, unresolved)


def build_scenarios(res: Result, rules: Rules) -> list[Scenario]:
    scs: list[Scenario] = []
    by_file: dict[str, list[Instance]] = {}
    for i in res.instances:
        if i.kind in ("handle", "named") and i.adjusts:
            by_file.setdefault(i.file, []).append(i)
    all_items: dict[Any, SimItem] = {}
    skipped: set[str] = set()
    for f, insts in by_file.items():
        sc = Scenario(name=f"{_rel(res.root, f)}", origin=f)
        for i in insts:
            if i.effect in NOT_SIMULATED:
                skipped.add(i.effect)
            it = _peak_item(rules, i)
            if it:
                sc.items.append(it)
                key = (i.effect, i.uid) if i.kind == "handle" else (i.effect, "named")
                prev = all_items.get(key)
                if prev is None or _deviation(rules, i.effect, it.params) > _deviation(rules, i.effect, prev.params):
                    all_items[key] = it
        if sc.items:
            scs.append(sc)
    # optics (config)
    for o in res.optics:
        its = []
        for e in o.effects:
            inst = res.optic_effects.get(e.lower())
            if inst and inst.effect and inst.adjusts:
                it = _peak_item(rules, inst)
                if it:
                    if not isinstance(inst.priority, (int, float)):
                        it.assumed_priority = True
                    its.append(it)
        if its:
            scs.append(Scenario(name=f"optic {o.name.split('::')[-1]} ({_rel(res.root, o.file)})", items=its, origin=o.file))
    if len([s for s in scs if s.kind == "pp"]) >= 2 and len(all_items) >= 2:
        scs.append(Scenario(name="ALL effects of the mod active at once (worst case)", items=list(all_items.values()), origin="*"))
    # thermal
    tp = rules.tc["ti_parameters"]
    tf: dict[str, dict] = {}
    for t in res.ti_calls:
        if t["value"] is None:
            continue
        d = tf.setdefault(t["file"], {"OutputRangeStart": tp["OutputRangeStart"]["default"], "OutputRangeWidth": tp["OutputRangeWidth"]["default"], "line": t["line"]})
        d[t["name"]] = t["value"]
    for f, d in tf.items():
        if any(k in d for k in ("OutputRangeStart", "OutputRangeWidth")):
            scs.append(Scenario(name=f"thermal: {_rel(res.root, f)}", kind="ti", ti=d, origin=f))
    return scs


def _rel(root: str, p: str) -> str:
    try:
        return os.path.relpath(p, root) if os.path.isabs(p) else p
    except ValueError:
        return p


# ---------------------------------------------------------------------------
# rendering + metrics
# ---------------------------------------------------------------------------
def render_stack(scene: np.ndarray, items: list[SimItem], cal: dict) -> np.ndarray:
    img = scene.copy()
    for it in sorted(items, key=lambda x: x.priority):
        fn = FX.get(it.effect)
        if fn:
            img = np.clip(fn(img, it.params, cal), 0, 1)
    return img


def _sat(img):
    mx, mn = img.max(-1), img.min(-1)
    return float(np.mean((mx - mn) / (mx + 1e-4)))


def _lap_var(luma_img):
    k = luma_img[1:-1, 1:-1] * -4 + luma_img[:-2, 1:-1] + luma_img[2:, 1:-1] + luma_img[1:-1, :-2] + luma_img[1:-1, 2:]
    return float(np.var(k))


def compute_metrics(before: np.ndarray, after: np.ndarray, regions: dict) -> dict:
    lb, la = (before * LUMA).sum(-1), (after * LUMA).sum(-1)
    r0, r1 = regions["ramp"]
    ramp = la[r0:r1].mean(0)
    levels = len(np.unique(np.round(ramp * 255).astype(int)))
    base_levels = len(np.unique(np.round(lb[r0:r1].mean(0) * 255).astype(int)))
    gy0, gy1, gx0, gx1 = regions["grain_patch"]
    dy0, dy1, dx0, dx1 = regions["detail"]
    return {
        "clip_low_pct": float(np.mean(ramp <= 1.5 / 255) * 100),
        "clip_high_pct": float(np.mean(ramp >= 253.5 / 255) * 100),
        "levels_remaining": int(levels),
        "levels_input": int(base_levels),
        "mean_luma_shift": float(la.mean() - lb.mean()),
        "saturation_ratio": _sat(after) / max(_sat(before), 1e-4),
        "contrast_ratio": float(la.std() / max(lb.std(), 1e-4)),
        "detail_ratio": _lap_var(la[dy0:dy1, dx0:dx1]) / max(_lap_var(lb[dy0:dy1, dx0:dx1]), 1e-9),
        "grain_noise_std": float(la[gy0:gy1, gx0:gx1].std()),
    }


def metric_findings(sc: Scenario, m: dict, rules: Rules, cal: dict) -> list[tuple[str, str, str, str]]:
    """-> [(rule, severity, message, prov)]"""
    th = rules.thresholds
    out = []
    eff = {i.effect for i in sc.items}
    stack = " + ".join(sorted(eff))

    def add(rule, msg, maxsev="warning"):
        out.append((rule, cap(RULES[rule]["sev"], maxsev), f"[{sc.name}] {msg} (stack: {stack}; modelled)", "model"))

    if m["clip_low_pct"] > th["clip_low_pct"]:
        add("SIM001", f"{m['clip_low_pct']:.0f}% of the dark tonal range is crushed to black")
    if m["clip_high_pct"] > th["clip_high_pct"]:
        add("SIM002", f"{m['clip_high_pct']:.0f}% of the bright tonal range is clipped to white")
    if m["levels_remaining"] < th["levels_remaining_min"]:
        add("SIM003", f"only {m['levels_remaining']} of 256 grey levels remain ({m['levels_input']} in the source ramp)")
    if abs(m["mean_luma_shift"]) > th["mean_luma_shift_abs"]:
        add("SIM004", f"average luminance moves by {m['mean_luma_shift']:+.2f}")
    if m["saturation_ratio"] < th["saturation_ratio_min"] or m["saturation_ratio"] > th["saturation_ratio_max"]:
        add("SIM005", f"saturation is x{m['saturation_ratio']:.2f} of the original", "info")
    if m["contrast_ratio"] < th["contrast_ratio_min"] or m["contrast_ratio"] > th["contrast_ratio_max"]:
        add("SIM006", f"luminance spread is x{m['contrast_ratio']:.2f} of the original")
    if eff & BLURRING and m["detail_ratio"] < th["detail_ratio_min"]:
        add("SIM007", f"fine detail drops to {m['detail_ratio'] * 100:.0f}% of the original", "info")
    if "FilmGrain" in eff and m["grain_noise_std"] > th["grain_noise_std_max"]:
        add("SIM008", f"grain noise std {m['grain_noise_std']:.2f} on a flat patch", "info")
    for e in sorted(eff & NOT_SIMULATED):
        out.append(("SIM009", "info", f"[{sc.name}] {e} is not simulated offline", "model"))
    return out


# ---- thermal -----------------------------------------------------------
def make_thermal_scene(w: int = W, h: int = H) -> np.ndarray:
    """Synthetic 'thermal value' map in 0..1."""
    t = np.zeros((h, w), np.float32)
    horizon = int(h * 0.42)
    t[:horizon] = np.linspace(0.05, 0.15, horizon)[:, None]
    t[horizon:] = 0.32
    yy, xx = np.mgrid[0:h, 0:w]
    t[(((xx - w * 0.3) / 40) ** 2 + ((yy - h * 0.55) / 70) ** 2) < 1] = 0.55   # warm building
    for cx in (0.52, 0.62):
        t[(((xx - w * cx) / 10) ** 2 + ((yy - h * 0.58) / 28) ** 2) < 1] = 0.9   # people
    halo = (((xx - w * 0.78) / 50) ** 2 + ((yy - h * 0.66) / 24) ** 2) < 1
    t[halo] = np.maximum(t[halo], 0.7)                                          # warm surroundings
    t[(((xx - w * 0.78) / 28) ** 2 + ((yy - h * 0.66) / 14) ** 2) < 1] = 1.0   # engine
    sh = int(h * 0.12)
    t[h - sh:] = np.linspace(0, 1, w)[None, :]
    return np.clip(t, 0, 1)


_PALETTES = {
    0: lambda g: np.stack([g, g, g], -1),
    1: lambda g: np.stack([1 - g] * 3, -1),
    2: lambda g: np.stack([0.6 * g, 0.15 + 0.85 * g, 0.6 * g], -1),
    3: lambda g: np.stack([0 * g, 0.3 * (1 - g), 0 * g], -1),
    4: lambda g: np.stack([0.15 + 0.85 * g, 0.6 * g, 0.6 * g], -1),
    5: lambda g: np.stack([0.3 * (1 - g), 0 * g, 0 * g], -1),
    6: lambda g: np.stack([0.25 + 0.75 * g, g, g], -1),
}


def _pal7(g):
    stops = np.array([[0, .25, 0], [0, .8, 0], [1, .2, 0], [1, 1, 1]], np.float32)
    x = np.clip(g, 0, 1) * 3
    i = np.minimum(x.astype(int), 2)
    f = (x - i)[..., None]
    return stops[i] * (1 - f) + stops[i + 1] * f


_PALETTES[7] = _pal7


def render_thermal(t: np.ndarray, start: float, width: float, mode: int = 0) -> np.ndarray:
    out = np.clip(start + t * width, 0, 1)
    return np.clip(_PALETTES[mode](out), 0, 1).astype(np.float32)


def thermal_metrics(start: float, width: float) -> dict:
    lo, hi = max(0.0, start), min(1.0, start + width)
    usable = max(0.0, hi - lo)
    clipped_top = max(0.0, (start + width - 1.0) / width) if width > 0 else 0.0
    clipped_bottom = max(0.0, -start / width) if width > 0 else 0.0
    return {"output_low": lo, "output_high": hi, "grey_levels": int(round(usable * 255)),
            "thermal_range_clipped_top_pct": clipped_top * 100, "thermal_range_clipped_bottom_pct": clipped_bottom * 100}


# ---- sheet composition -------------------------------------------------
def _text(draw: ImageDraw.ImageDraw, xy, s: str, fill=(235, 235, 235)):
    draw.text(xy, s, fill=fill)


def compose_sheet(title: str, panels: list[tuple[str, np.ndarray]], lines: list[str]) -> Image.Image:
    pad, cap_h = 8, 14
    pw, ph = panels[0][1].shape[1], panels[0][1].shape[0]
    cols = min(len(panels), 2 if len(panels) in (2, 4) else 3)
    rows = (len(panels) + cols - 1) // cols
    width = cols * pw + (cols + 1) * pad
    text_h = 14 * (len(lines) + 2)
    height = text_h + rows * (ph + cap_h + pad) + pad
    sheet = Image.new("RGB", (width, height), (24, 24, 28))
    d = ImageDraw.Draw(sheet)
    _text(d, (pad, 4), title, (255, 255, 255))
    for i, ln in enumerate(lines):
        _text(d, (pad, 4 + 14 * (i + 1)), ln, (190, 200, 210))
    y0 = text_h
    for k, (cap_s, arr) in enumerate(panels):
        r, c = divmod(k, cols)
        x = pad + c * (pw + pad)
        y = y0 + r * (ph + cap_h + pad)
        _text(d, (x, y), cap_s)
        sheet.paste(_pil(arr), (x, y + cap_h))
    return sheet


def run_scenarios(scs: list[Scenario], rules: Rules, cal: dict, out_dir: str | None) -> tuple[list[dict], list[tuple]]:
    """Render scenarios. Returns (summaries, findings[(rule,sev,msg,prov, file)])."""
    scene, regions = make_scene()
    tscene = make_thermal_scene()
    summaries: list[dict] = []
    findings: list[tuple] = []
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    for n, sc in enumerate(scs, 1):
        slug = "".join(ch if ch.isalnum() else "_" for ch in sc.name)[:48].strip("_")
        if sc.kind == "ti":
            d = sc.ti
            s, w = d["OutputRangeStart"], d["OutputRangeWidth"]
            tp = rules.tc["ti_parameters"]
            m = thermal_metrics(s, w)
            panels = [(f"default Start {tp['OutputRangeStart']['default']:g} Width {tp['OutputRangeWidth']['default']:g} (WHOT)",
                       render_thermal(tscene, tp["OutputRangeStart"]["default"], tp["OutputRangeWidth"]["default"], 0)),
                      (f"mod Start {s:g} Width {w:g} (WHOT)", render_thermal(tscene, s, w, 0)),
                      (f"mod BHOT (mode 1)", render_thermal(tscene, s, w, 1)),
                      (f"mod mode 2 (green)", render_thermal(tscene, s, w, 2))]
            lines = [f"output window {m['output_low']:.2f}..{m['output_high']:.2f}  grey levels ~{m['grey_levels']}  "
                     f"clipped top {m['thermal_range_clipped_top_pct']:.0f}%  bottom {m['thermal_range_clipped_bottom_pct']:.0f}%",
                     "palettes for modes 1-7 are approximations built from the wiki mode names"]
            summaries.append({"scenario": sc.name, "kind": "ti", "metrics": m, "image": None})
            if out_dir:
                p = os.path.join(out_dir, f"{n:02d}_{slug}.png")
                compose_sheet(sc.name, panels, lines).save(p)
                summaries[-1]["image"] = p
            continue
        after = render_stack(scene, sc.items, cal)
        m = compute_metrics(scene, after, regions)
        mf = metric_findings(sc, m, rules, cal)
        for rule, sev, msg, prov in mf:
            findings.append((rule, sev, msg, prov, sc.origin))
        info = {"scenario": sc.name, "kind": "pp", "metrics": m, "image": None,
                "items": [{"effect": it.effect, "priority": it.priority, "assumed_priority": it.assumed_priority,
                           "params": it.params, "source": f"{_rel('', it.file)}:{it.line}", "unresolved_params": it.unresolved}
                          for it in sorted(sc.items, key=lambda x: x.priority)]}
        summaries.append(info)
        if out_dir:
            order = " -> ".join(f"{it.effect}@{it.priority:g}{'*' if it.assumed_priority else ''}" for it in sorted(sc.items, key=lambda x: x.priority))
            lines = [f"order: {order}   (* = priority unknown, base priority assumed)",
                     f"levels {m['levels_remaining']}/256  clipL {m['clip_low_pct']:.0f}%  clipH {m['clip_high_pct']:.0f}%  "
                     f"lumaShift {m['mean_luma_shift']:+.2f}  sat x{m['saturation_ratio']:.2f}  contrast x{m['contrast_ratio']:.2f}",
                     "approximate model - not engine-accurate" + ("" if cal.get("calibrated") else "; blur/grain/chroma scales uncalibrated")]
            p = os.path.join(out_dir, f"{n:02d}_{slug}.png")
            compose_sheet(sc.name, [("reference", scene), ("modelled result", after)], lines).save(p)
            info["image"] = p
    return summaries, findings


# ---------------------------------------------------------------------------
# calibration against real screenshots
# ---------------------------------------------------------------------------
def load_pair(before_path: str, after_path: str, width: int = W) -> tuple[np.ndarray, np.ndarray]:
    """Load a before/after screenshot pair, both resized to the same small size."""
    b = Image.open(before_path).convert("RGB")
    a = Image.open(after_path).convert("RGB")
    h = max(1, int(round(b.height * width / b.width)))
    b = b.resize((width, h), Image.LANCZOS)
    a = a.resize((width, h), Image.LANCZOS)
    return _arr(b), _arr(a)


def _mae(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.abs(x - y).mean())


def fit_color_corrections(pairs: list[tuple[np.ndarray, np.ndarray, list]], cal: dict) -> list[dict]:
    """Rank the candidate ColorCorrections models by how well they reproduce real screenshots.
    pairs: [(before, after, ppEffectAdjust params)]. Use several parameter sets (different contrast,
    brightness, colorize) so the candidates can be told apart."""
    out = []
    for model in ("desat_first", "legacy"):
        pivots = (0.0, 0.18, 0.5) if model == "desat_first" else (None,)
        bms = ("additive", "multiplicative") if model == "desat_first" else (None,)
        for pv in pivots:
            for bm in bms:
                c = dict(cal)
                c["cc_model"] = model
                if pv is not None:
                    c["cc_pivot"] = pv
                    c["cc_brightness"] = bm
                err = float(np.mean([_mae(fx_color_corrections(b, p, c), a) for b, a, p in pairs]))
                out.append({"error": err, "cc_model": model, "cc_pivot": pv, "cc_brightness": bm})
    out.sort(key=lambda d: d["error"])
    return out


def fit_dynamic_blur(pairs: list[tuple[np.ndarray, np.ndarray, list]], cal: dict) -> list[dict]:
    out = []
    for k in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 14.0):
        c = dict(cal)
        c["blur_sigma_per_unit"] = k
        err = float(np.mean([_mae(fx_dynamic_blur(b, p, c), a) for b, a, p in pairs]))
        out.append({"error": err, "blur_sigma_per_unit": k})
    out.sort(key=lambda d: d["error"])
    return out


def quick_render(effect: str, params: list, rules: Rules, cal: dict, out_path: str) -> dict:
    """Render one effect with given params (used by the `sim` CLI command)."""
    scene, regions = make_scene()
    filled, unresolved = _fill(rules, effect, params)
    base = rules.effects[effect]["base_priority"] or 0
    it = SimItem(effect, filled, float(base), effect, "<cli>", 0, True, unresolved)
    after = render_stack(scene, [it], cal) if effect in FX else scene
    m = compute_metrics(scene, after, regions)
    sc = Scenario(name=f"{effect} {params}", items=[it])
    lines = [f"levels {m['levels_remaining']}/256  clipL {m['clip_low_pct']:.0f}%  clipH {m['clip_high_pct']:.0f}%  "
             f"lumaShift {m['mean_luma_shift']:+.2f}  sat x{m['saturation_ratio']:.2f}  contrast x{m['contrast_ratio']:.2f}",
             "approximate model - not engine-accurate"]
    compose_sheet(sc.name[:90], [("reference", scene), ("modelled result", after)], lines).save(out_path)
    return {"metrics": m, "findings": metric_findings(sc, m, rules, cal), "image": out_path, "simulated": effect in FX}
