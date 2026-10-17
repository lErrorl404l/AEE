"""Offline map preview: draws a synthetic map from a map control's colours and a terrain's Grid class, then
measures how visible the grid lines and grid numbers are - as configured, and after the mod's post-process stack.

What is modelled, and how much to trust it
------------------------------------------
* The map control's own colours (colorBackground, colorSea, colorForest, colorCountlines, colorRoads,
  colorGrid, colorGridMap) are real config values. The land / sea / forest backdrops are composites of them.
* The satellite texture depends on the terrain, so two stand-in swatches (dark, bright) are used. Assumption.
* The grid numbers are drawn in the colour of colorGrid. Assumption (the wiki does not say which colour the
  numbers use).
* WHETHER POST-PROCESS IS APPLIED TO THE MAP SCREEN IS NOT DOCUMENTED. Findings that need that are info only until
  the calibration file says `pp_on_map: true`. `map-pp` sets it from two screenshots.
"""
from __future__ import annotations

import os
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import mapcfg, sim
from .catalog import RULES, cap

W, H = 480, 270
BAND_NAMES = ["land (colorBackground)", "sea (colorSea)", "forest (colorForest)", "satellite, dark (assumed)", "satellite, bright (assumed)"]
CONFIGURED = (0, 1, 2)   # bands built from the mod's own colours; the others are stand-ins


def _rgba(v, default) -> list[float]:
    if isinstance(v, list) and len(v) >= 3 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v[:3]):
        a = float(v[3]) if len(v) > 3 and isinstance(v[3], (int, float)) and not isinstance(v[3], bool) else 1.0
        return [float(x) for x in v[:3]] + [a]
    return list(default)


def _over(base: np.ndarray, rgba: list[float]) -> np.ndarray:
    a = float(np.clip(rgba[3], 0, 1))
    return base * (1 - a) + np.array(rgba[:3], np.float32) * a


def _lin(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def luminance(rgb: np.ndarray) -> float:
    l = _lin(np.asarray(rgb, np.float32))
    return float(0.2126 * l[..., 0] + 0.7152 * l[..., 1] + 0.0722 * l[..., 2])


def contrast(a: np.ndarray, b: np.ndarray) -> float:
    """WCAG contrast ratio between two RGB colours (1 = identical, 21 = black on white)."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def effective_style(style: dict, defaults: dict) -> tuple[dict, list[str]]:
    """Fill what the mod does not set with the community default RscMapControl values; return (style, assumed names)."""
    out, assumed = {}, []
    for k in ("colorBackground", "colorSea", "colorForest", "colorCountlines", "colorRoads", "colorGrid", "colorGridMap", "colorLevels", "colorOutside"):
        v = style.get(k.lower())
        if v is None and k in defaults:
            assumed.append(k)
        out[k] = _rgba(v, defaults.get(k, {"colorBackground": [0.93, 0.93, 0.93, 1], "colorForest": [0.6, 0.8, 0.2, 0.25],
                                           "colorCountlines": [0.65, 0.53, 0.29, 1], "colorRoads": [0.2, 0.13, 0, 1]}.get(k, [0.5, 0.5, 0.5, 1])))
        if v is None and k not in defaults:
            assumed.append(k)
    sz = style.get("sizeexgrid")
    out["sizeExGrid"] = float(sz) if isinstance(sz, (int, float)) and not isinstance(sz, bool) else float(defaults.get("sizeExGrid", 0.02))
    return out, assumed


def make_map_scene(style: dict, grid_labels: dict | None, rules_ui: dict, grid_key: str = "colorGrid", w: int = W, h: int = H):
    """-> (scene_map, scene_grid, line_mask, label_mask, band_slices).  Images are float32 HxWx3 in 0..1."""
    d = rules_ui.get("map_preview", {})
    sat = d.get("satellite_swatches", {})
    bg = np.array(style["colorBackground"][:3], np.float32)
    n = len(BAND_NAMES)
    swatch = [
        bg,
        _over(bg, style["colorSea"]),
        _over(bg, style["colorForest"]),
        np.array(sat.get("dark", [0.20, 0.26, 0.15]), np.float32),
        np.array(sat.get("bright", [0.72, 0.66, 0.50]), np.float32),
    ]
    scene = np.zeros((h, w, 3), np.float32)
    edges = [round(i * w / n) for i in range(n + 1)]
    slices = []
    for i in range(n):
        scene[:, edges[i]:edges[i + 1]] = swatch[i]
        slices.append((edges[i], edges[i + 1]))
    # contour lines and a road, for realism (not measured)
    im = Image.fromarray((scene * 255).astype(np.uint8))
    dr = ImageDraw.Draw(im, "RGBA")
    cc = tuple(int(x * 255) for x in style["colorCountlines"][:3]) + (int(style["colorCountlines"][3] * 255),)
    for k in range(8):
        y = 20 + k * 32
        pts = [(x, y + 6 * np.sin(x / 23.0 + k)) for x in range(0, w, 6)]
        dr.line(pts, fill=cc, width=1)
    rc = tuple(int(x * 255) for x in style["colorRoads"][:3]) + (int(style["colorRoads"][3] * 255),)
    dr.line([(0, h * 0.8), (w * 0.35, h * 0.55), (w * 0.7, h * 0.62), (w, h * 0.3)], fill=rc, width=2)
    scene_map = np.asarray(im, np.float32) / 255.0

    # grid lines: 8 columns x 4 rows of cells
    gcol = style[grid_key]
    step_x, step_y = w // 8, h // 4
    line_mask = np.zeros((h, w), bool)
    for x in range(step_x // 2, w, step_x):
        line_mask[:, x] = True
    for y in range(step_y // 2, h, step_y):
        line_mask[y, :] = True
    grid = scene_map.copy()
    a = float(np.clip(gcol[3], 0, 1))
    grid[line_mask] = scene_map[line_mask] * (1 - a) + np.array(gcol[:3], np.float32) * a

    # grid numbers
    font = ImageFont.load_default(size=max(8, int(style["sizeExGrid"] * h * 2.2))) if style["sizeExGrid"] > 0 else None
    label_mask = np.zeros((h, w), bool)
    if font is not None:
        lm = Image.new("L", (w, h), 0)
        ld = ImageDraw.Draw(lm)
        labels = grid_labels or {}
        xs = [labels.get("x", lambda i: f"{i:03d}")(i) for i in range(8)]
        ys = [labels.get("y", lambda i: f"{i:03d}")(i) for i in range(4)]
        for i, x in enumerate(range(step_x // 2, w, step_x)):
            ld.text((x + 2, 2), xs[i], fill=255, font=font)
        for j, y in enumerate(range(step_y // 2, h, step_y)):
            ld.text((2, y + 1), ys[j], fill=255, font=font)
        label_mask = np.asarray(lm) > 128
        grid[label_mask & ~line_mask] = scene_map[label_mask & ~line_mask] * (1 - a) + np.array(gcol[:3], np.float32) * a
        # numbers are drawn at full strength of the colour's alpha, but never fainter than the lines
    return scene_map, grid, line_mask & ~label_mask, label_mask & ~line_mask, slices


def band_contrasts(base: np.ndarray, drawn: np.ndarray, mask: np.ndarray, slices) -> list[float | None]:
    out = []
    for x0, x1 in slices:
        m = mask[:, x0:x1]
        if m.sum() < 8:
            out.append(None)
            continue
        a = drawn[:, x0:x1][m].mean(0)
        b = base[:, x0:x1][m].mean(0)
        out.append(float(contrast(a, b)))
    return out


def grid_label_funcs(grid: "mapcfg.GridModel | None", zoom: "mapcfg.Zoom | None"):
    if grid is None or zoom is None or not zoom.numeric or not isinstance(grid.map_size, (int, float)):
        return None, "generic labels"
    ms = float(grid.map_size)
    x0, y0 = label_start = (ms * 0.5, ms * 0.5)
    gx, gy = mapcfg.label_at(grid, zoom, x0, y0)
    sy = 1 if zoom.sy < 0 else -1   # labels rise to the north when stepY is negative; rows are drawn top (north) to bottom

    def fx(i):
        return mapcfg.fmt_label(gx + i, zoom.fx)

    def fy(i):
        return mapcfg.fmt_label(gy + (3 - i) * sy, zoom.fy)

    return {"x": fx, "y": fy}, f"{grid.world} {zoom.name} (step {zoom.sx:g} m) around the map centre"


def pick_zoom(grid: "mapcfg.GridModel | None", which: str | None):
    if grid is None or not grid.zooms:
        return None
    zs = [z for z in grid.zooms if z.numeric]
    if not zs:
        return None
    if which:
        for z in zs:
            if z.name.lower() == which.lower() or z.name.lower() == "zoom" + which:
                return z
    return sorted(zs, key=lambda z: z.zoom_max if isinstance(z.zoom_max, (int, float)) else 1e9)[0]


def evaluate(style: dict, labels, rules, items, cal, out_path: str | None = None, title: str = "map preview"):
    """Render and measure one map style (optionally through a post-process stack). Returns a metrics dict."""
    ui = rules.ui
    thr = ui.get("map_preview", {})
    res: dict[str, Any] = {}
    for key in ("colorGrid", "colorGridMap"):
        sc_map, sc_grid, lines, text, sl = make_map_scene(style, labels, ui, key)
        res[key] = {"lines": band_contrasts(sc_map, sc_grid, lines, sl), "text": band_contrasts(sc_map, sc_grid, text, sl)}
        if items:
            after_map = sim.render_stack(sc_map, items, cal)
            after_grid = sim.render_stack(sc_grid, items, cal)
            res[key]["lines_pp"] = band_contrasts(after_map, after_grid, lines, sl)
            res[key]["text_pp"] = band_contrasts(after_map, after_grid, text, sl)
            if out_path and key == "colorGrid":
                lab = [f"line contrast per backdrop: " + "  ".join(f"{'-' if c is None else f'{c:.2f}'}" for c in res[key]["lines"]) + "  (before)",
                       "                           " + "  ".join(f"{'-' if c is None else f'{c:.2f}'}" for c in res[key]["lines_pp"]) + "  (after post-process)",
                       "backdrops, left to right: " + " | ".join(n.split(" (")[0] for n in BAND_NAMES),
                       "approximate model; the grid number colour and satellite swatches are assumptions"]
                sim.compose_sheet(title, [("as configured", sc_grid), ("through the post-process stack", after_grid)], lab).save(out_path)
        elif out_path and key == "colorGrid":
            lab = [f"line contrast per backdrop: " + "  ".join(f"{'-' if c is None else f'{c:.2f}'}" for c in res[key]["lines"]),
                   "backdrops, left to right: " + " | ".join(n.split(" (")[0] for n in BAND_NAMES)]
            sim.compose_sheet(title, [("as configured", sc_grid)], lab).save(out_path)
    return res


def preview_scenarios(res, rules, cal, out_dir: str | None, limit: int = 3):
    """Run every map style found in the scanned configs. -> (summaries, findings[(rule, sev, msg, prov, origin)])"""
    ui = rules.ui
    thr = ui.get("map_preview", {})
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    defaults = thr.get("default_style", {})
    line_min = thr.get("grid_line_min_contrast", 1.3)
    label_min = thr.get("grid_label_min_contrast", 2.5)
    drop = thr.get("contrast_drop_ratio", 0.6)
    pp_known = cal.get("pp_on_map")
    scs = [s for s in sim.build_scenarios(res, rules) if s.kind == "pp" and not s.name.startswith("optic ")]
    worst = [s for s in scs if s.origin == "*"] or scs[:1]
    scs = (worst + [s for s in scs if s not in worst])[:limit]

    gm = res.grid_models[0] if getattr(res, "grid_models", None) else None
    labels, label_note = grid_label_funcs(gm, pick_zoom(gm, cal.get("map_zoom")))
    summaries, findings = [], []
    seen = set()
    n = 0
    for st in res.map_styles:
        has_grid_color = "colorgrid" in st or "colorgridmap" in st
        if not has_grid_color:
            continue
        key = (st.get("_where"), str(st.get("colorgrid")), str(st.get("colorgridmap")), str(st.get("colorbackground")))
        if key in seen:
            continue
        seen.add(key)
        eff, assumed = effective_style(st, defaults)
        origin = st.get("_file", "")
        where = st.get("_where", "?")
        n += 1
        slug = "".join(ch if ch.isalnum() else "_" for ch in where.split("::")[-1])[:30]
        entry = {"style": where, "assumed": assumed, "labels": label_note, "scenarios": []}
        base = evaluate(eff, labels, rules, None, cal, os.path.join(out_dir, f"map_{n:02d}_{slug}.png") if out_dir else None, f"map preview: {where}")
        entry["configured"] = base
        def names(idx):
            return ", ".join(BAND_NAMES[i].split(" (")[0].replace("satellite, ", "satellite ") for i in idx)

        for gk in ("colorGrid", "colorGridMap"):
            if gk.lower() not in st:
                continue          # not set by this class: nothing of the mod's to judge
            lc = base[gk]["lines"]
            bad_cfg = [i for i in CONFIGURED if lc[i] is not None and lc[i] < line_min]
            bad_sat = [i for i in range(len(lc)) if i not in CONFIGURED and lc[i] is not None and lc[i] < line_min]
            if bad_cfg:
                worst = ", ".join(f"{BAND_NAMES[i].split(' (')[0]} {lc[i]:.2f}:1" for i in bad_cfg)
                findings.append(("MAPSIM001", "warning" if 0 in bad_cfg else "info",
                                 f"[{where}] {gk} grid lines are nearly invisible on the map control's own backdrops ({worst}; below {line_min}:1)", "heuristic", origin))
            elif bad_sat:
                worst = ", ".join(f"{BAND_NAMES[i].split(' (')[0].replace('satellite, ', 'satellite ')} {lc[i]:.2f}:1" for i in bad_sat)
                findings.append(("MAPSIM001", "info",
                                 f"[{where}] {gk} grid lines nearly vanish on the stand-in satellite colours ({worst}; below {line_min}:1) - real terrain imagery will differ", "heuristic", origin))
            tc = base[gk]["text"]
            bad_txt = [i for i in CONFIGURED if tc[i] is not None and tc[i] < label_min]
            if bad_txt:
                worst = ", ".join(f"{BAND_NAMES[i].split(' (')[0]} {tc[i]:.2f}:1" for i in bad_txt)
                findings.append(("MAPSIM001", "info", f"[{where}] grid numbers ({gk}) are hard to read ({worst}; below {label_min}:1)", "heuristic", origin))
        for sc in scs:
            r = evaluate(eff, labels, rules, sc.items, cal, os.path.join(out_dir, f"map_{n:02d}_{slug}_pp_{scs.index(sc)}.png") if out_dir else None,
                         f"map preview through: {sc.name}")
            entry["scenarios"].append({"scenario": sc.name, "metrics": r})
            if pp_known is False or "colorgrid" not in st:
                continue
            before, after = r["colorGrid"]["lines"], r["colorGrid"]["lines_pp"]
            lost = [i for i, (b_, a_) in enumerate(zip(before, after)) if b_ is not None and a_ is not None and a_ < line_min and a_ < b_ * drop and b_ >= line_min]
            if lost:
                detail = ", ".join(f"{BAND_NAMES[i].split(' (')[0].replace('satellite, ', 'satellite ')} {before[i]:.2f} -> {after[i]:.2f}" for i in lost)
                note = "" if pp_known else " If post-process is not applied to the map screen this does not matter - the wiki does not say; `map-pp` decides it from two screenshots."
                findings.append(("MAPSIM002", "warning" if pp_known else "info",
                                 f"[{where} through {sc.name}] modelled grid-line contrast collapses under this post-process stack ({detail}).{note}",
                                 "model", sc.origin if sc.origin not in ("*", "") else origin))
        summaries.append(entry)
    return summaries, findings


def grid_sheet(model: "mapcfg.GridModel", rules, out_path: str, which: str | None = None) -> None:
    """A map-control-style picture of the terrain grid with its real labels around the map centre."""
    zoom = pick_zoom(model, which)
    labels, note = grid_label_funcs(model, zoom)
    eff, _ = effective_style({}, rules.ui.get("map_preview", {}).get("default_style", {}))
    _, grid, _, _, _ = make_map_scene(eff, labels, rules.ui)
    lines = [note, "default RscMapControl colours; backdrops: land | sea | forest | two stand-in satellite swatches"]
    sim.compose_sheet(f"grid preview: {model.world}", [("grid", grid)], lines).save(out_path)
