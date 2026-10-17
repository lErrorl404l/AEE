"""Map checks that work on config: the terrain's CfgWorlds >> <world> >> Grid class (grid lines and the
numbers printed on them) and map controls (RscMapControl and everything derived from it).

SOURCES - read this before trusting a finding
---------------------------------------------
The BI wiki documents neither the Grid class nor its properties. What follows comes from community
sources and is tagged `community`:
  * BI Feedback/forum threads "Grid Refrence to World Position" (Moricky's and Killzone_Kid's
    BIS_fnc_gridToPos) - the conversion  posX = offsetX + stepX * gridX ;  posY = mapSize - offsetY - stepY * gridY
  * The PMC Editing Wiki real-world-data tutorial and the BI forum terrain-config examples (VR, Kunduz,
    abc_sample) - the usual layout: offsetX 0, offsetY = mapSize, negative stepY, several ZoomN classes
    with ascending zoomMax and one fewer digit per zoom level.
The label arithmetic below is the inverse of that conversion. It is NOT read from the engine, so the
findings say "by the community formula". Which zoom class `mapGridPosition` itself uses is undocumented.

From the BI wiki (CfgWorlds Config Reference, CT_MAP_MAIN): mapSize, gridNumbersOverLines, mapArea[]
(apparently unused), and the list of map-control properties.
"""
from __future__ import annotations

import difflib
import math
import re
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .config_cpp import CfgClass
from .sqf import UNKNOWN

if TYPE_CHECKING:  # pragma: no cover
    from .analyze import Analyzer

ZOOM_RE = re.compile(r"^zoom\d*$", re.I)
ZOOM_PROPS = ("zoomMax", "format", "formatX", "formatY", "stepX", "stepY")


def _isnum(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


# ===========================================================================================
# terrain grid
# ===========================================================================================
@dataclass
class Zoom:
    name: str
    line: int
    inherits: str | None
    zoom_max: Any = UNKNOWN
    fmt: Any = UNKNOWN
    fx: Any = UNKNOWN
    fy: Any = UNKNOWN
    sx: Any = UNKNOWN
    sy: Any = UNKNOWN
    present: set = field(default_factory=set)

    @property
    def numeric(self) -> bool:
        return _isnum(self.sx) and _isnum(self.sy) and self.sx != 0 and self.sy != 0


@dataclass
class GridModel:
    world: str
    file: str
    line: int
    map_size: Any = UNKNOWN
    map_size_line: int = 0
    center: Any = UNKNOWN
    center_line: int = 0
    over_lines: Any = UNKNOWN
    over_lines_line: int = 0
    map_area_line: int = 0
    has_grid: bool = False
    grid_line: int = 0
    grid_inherits: str | None = None
    offset_x: Any = UNKNOWN
    offset_y: Any = UNKNOWN
    zooms: list[Zoom] = field(default_factory=list)


def collect_worlds(root: CfgClass) -> list[GridModel]:
    out: list[GridModel] = []
    cw = root.children.get("cfgworlds")
    if cw is None:
        return out
    for w in cw.children.values():
        g = w.children.get("grid")
        has_basics = any(k in w.props for k in ("mapsize", "centerposition", "gridnumbersoverlines", "maparea"))
        if g is None and not has_basics:
            continue
        m = GridModel(world=w.name, file=w.file, line=w.line)
        if "mapsize" in w.props:
            m.map_size, m.map_size_line = w.props["mapsize"]
        if "centerposition" in w.props:
            m.center, m.center_line = w.props["centerposition"]
        if "gridnumbersoverlines" in w.props:
            m.over_lines, m.over_lines_line = w.props["gridnumbersoverlines"]
        if "maparea" in w.props:
            m.map_area_line = w.props["maparea"][1]
        if g is not None:
            m.has_grid = True
            m.grid_line = g.line
            m.grid_inherits = g.parent
            if "offsetx" in g.props:
                m.offset_x = g.props["offsetx"][0]
            if "offsety" in g.props:
                m.offset_y = g.props["offsety"][0]
            for zc in g.children.values():
                if not ZOOM_RE.match(zc.name):
                    continue
                z = Zoom(zc.name, zc.line, zc.parent)
                for key, attr in (("zoommax", "zoom_max"), ("format", "fmt"), ("formatx", "fx"), ("formaty", "fy"), ("stepx", "sx"), ("stepy", "sy")):
                    if key in zc.props:
                        setattr(z, attr, zc.props[key][0])
                        z.present.add(key)
                m.zooms.append(z)
        out.append(m)
    return out


def _merge(models: list[GridModel]) -> list[GridModel]:
    """The same world can be configured in several files: combine what each says."""
    by: dict[str, GridModel] = {}
    for m in models:
        k = m.world.lower()
        if k not in by:
            by[k] = m
            continue
        b = by[k]
        for attr in ("map_size", "center", "over_lines", "offset_x", "offset_y"):
            if getattr(b, attr) is UNKNOWN and getattr(m, attr) is not UNKNOWN:
                setattr(b, attr, getattr(m, attr))
        b.has_grid = b.has_grid or m.has_grid
        if m.zooms and not b.zooms:
            b.zooms = m.zooms
            b.file, b.grid_line = m.file, m.grid_line
    return list(by.values())


def _floor(v: float) -> int:
    return int(math.floor(v + 1e-9))


def label_range(m: GridModel, z: Zoom):
    """(x_lo, x_hi, y_lo, y_hi) grid indices over the whole map by the community formula."""
    ms = float(m.map_size)
    ox = float(m.offset_x) if _isnum(m.offset_x) else 0.0
    oy = float(m.offset_y) if _isnum(m.offset_y) else 0.0
    eps = 1e-6
    xs = [_floor((0 - ox) / z.sx), _floor((ms - eps - ox) / z.sx)]
    # posY = mapSize - offsetY - stepY * gridY   =>   gridY = (mapSize - offsetY - posY) / stepY
    ys = [_floor((ms - oy - 0) / z.sy), _floor((ms - oy - (ms - eps)) / z.sy)]
    return min(xs), max(xs), min(ys), max(ys)


def label_at(m: GridModel, z: Zoom, x: float, y: float) -> tuple[int, int]:
    ox = float(m.offset_x) if _isnum(m.offset_x) else 0.0
    oy = float(m.offset_y) if _isnum(m.offset_y) else 0.0
    return _floor((x - ox) / z.sx), _floor((float(m.map_size) - oy - y) / z.sy)


def digits_of(fmt) -> int | None:
    """Width of a purely numeric label format such as "000"; None for letter / mixed formats."""
    if isinstance(fmt, str) and fmt and set(fmt) == {"0"}:
        return len(fmt)
    return None


def fmt_label(idx: int, fmt) -> str:
    w = digits_of(fmt)
    s = str(abs(idx))
    if w:
        s = s.zfill(w)
    return ("-" if idx < 0 else "") + s


def corner_labels(m: GridModel, z: Zoom) -> dict[str, str]:
    ms = float(m.map_size)
    pts = {"SW": (1.0, 1.0), "SE": (ms - 1, 1.0), "NW": (1.0, ms - 1), "NE": (ms - 1, ms - 1), "centre": (ms / 2, ms / 2)}
    out = {}
    for k, (x, y) in pts.items():
        gx, gy = label_at(m, z, x, y)
        out[k] = f"{fmt_label(gx, z.fx)} {fmt_label(gy, z.fy)}"
    return out


def grid_report(m: GridModel) -> dict:
    """Plain data for the `grid` command and the JSON report."""
    d = {"world": m.world, "file": m.file, "mapSize": m.map_size if _isnum(m.map_size) else None,
         "offsetX": m.offset_x if _isnum(m.offset_x) else None, "offsetY": m.offset_y if _isnum(m.offset_y) else None, "zooms": []}
    for z in m.zooms:
        e = {"name": z.name, "zoomMax": z.zoom_max if _isnum(z.zoom_max) else None, "stepX": z.sx if _isnum(z.sx) else None,
             "stepY": z.sy if _isnum(z.sy) else None, "formatX": z.fx if isinstance(z.fx, str) else None,
             "formatY": z.fy if isinstance(z.fy, str) else None, "inherits": z.inherits}
        if _isnum(m.map_size) and m.map_size > 0 and z.numeric:
            x0, x1, y0, y1 = label_range(m, z)
            e.update({"labelsX": [x0, x1], "labelsY": [y0, y1], "corners": corner_labels(m, z)})
        d["zooms"].append(e)
    return d


def check_grid(an: "Analyzer", m: GridModel) -> None:
    f, W = m.file, m.world
    ms_ok = _isnum(m.map_size) and m.map_size > 0

    # --- world basics -----------------------------------------------------------------------
    if m.map_size is not UNKNOWN and not ms_ok:
        an.add("MAP009", f, m.map_size_line or m.line, f"{W}: mapSize must be a positive number, got {m.map_size!r}")
    if ms_ok and isinstance(m.center, list) and len(m.center) >= 2 and all(_isnum(c) for c in m.center[:2]):
        cx, cy = m.center[0], m.center[1]
        if not (0 <= cx <= m.map_size and 0 <= cy <= m.map_size):
            an.add("MAP009", f, m.center_line or m.line, f"{W}: centerPosition [{cx:g}, {cy:g}] is outside the map (mapSize {m.map_size:g})")
    if m.over_lines is not UNKNOWN and not (m.over_lines in (0, 1) and _isnum(m.over_lines)):
        an.add("MAP009", f, m.over_lines_line or m.line, f"{W}: gridNumbersOverLines should be 0 or 1, got {m.over_lines!r}")
    if m.map_area_line:
        an.add("MAP009", f, m.map_area_line, f"{W}: mapArea[] is set; the wiki notes Arma 3 apparently does not use it [verify required]", sev="info")

    if not m.has_grid:
        return
    if not m.zooms:
        if m.grid_inherits is None:
            an.add("MAP007", f, m.grid_line, f"{W}: Grid class has no ZoomN classes, so no grid lines/numbers are defined")
        return

    # --- per zoom class: required properties ------------------------------------------------
    for z in m.zooms:
        if z.inherits is None:
            miss = [p for p in ZOOM_PROPS if p.lower() not in z.present]
            if miss:
                an.add("MAP007", f, z.line, f"{W} >> Grid >> {z.name}: missing {', '.join(miss)} (community configs always define all of {', '.join(ZOOM_PROPS)})")
        for attr, name in (("fmt", "format"), ("fx", "formatX"), ("fy", "formatY")):
            v = getattr(z, attr)
            if v is not UNKNOWN and not isinstance(v, str):
                an.add("MAP007", f, z.line, f"{W} >> Grid >> {z.name}: {name} should be a string, got {v!r}")
        if z.fmt is not UNKNOWN and isinstance(z.fmt, str) and z.fmt.upper() != "XY":
            an.add("MAP007", f, z.line, f"{W} >> Grid >> {z.name}: format \"{z.fmt}\" - every community example uses \"XY\" (orthogonal grid)", sev="info")
        if _isnum(z.sx) and z.sx <= 0:
            an.add("MAP005", f, z.line, f"{W} >> Grid >> {z.name}: stepX {z.sx:g} must be positive (grid cell width in metres)", sev="error")
        if _isnum(z.sy) and z.sy == 0:
            an.add("MAP005", f, z.line, f"{W} >> Grid >> {z.name}: stepY is 0", sev="error")
        if _isnum(z.sx) and _isnum(z.sy) and z.sx > 0 and abs(z.sy) != z.sx:
            an.add("MAP005", f, z.line, f"{W} >> Grid >> {z.name}: stepX {z.sx:g} and stepY {z.sy:g} differ in size, so grid cells are not square", sev="info")
        if _isnum(z.sy) and z.sy > 0:
            an.add("MAP005", f, z.line, f"{W} >> Grid >> {z.name}: stepY {z.sy:g} is positive: by the community formula the Y numbers then count down from the NORTH edge (the usual layout is offsetY = mapSize with a negative stepY, so numbers rise to the north)", sev="info")
        for attr in ("fx", "fy"):
            v = getattr(z, attr)
            if isinstance(v, str) and len(v) >= 4 and set(v) == {"0"}:
                an.add("MAP008", f, z.line, f"{W} >> Grid >> {z.name}: a {len(v)}-character label format. Community sources disagree: one forum report links a 4-character format on Zoom0 to a crash, the PMC tutorial ships 4 digits on Zoom1 without one. Verify in game", sev="info")
                break

    # --- ordering of zoom levels ----------------------------------------------------------------
    zs = [z for z in m.zooms if _isnum(z.zoom_max)]
    for a, b in zip(zs, zs[1:]):
        if b.zoom_max <= a.zoom_max:
            an.add("MAP003", f, b.line, f"{W} >> Grid: {b.name} (zoomMax {b.zoom_max:g}) comes after {a.name} (zoomMax {a.zoom_max:g}); zoom classes are expected in order of ascending zoomMax, finest first")
    if zs and len(zs) == len([z for z in m.zooms if z.inherits is None]) and max(z.zoom_max for z in zs) < 1:
        last = max(zs, key=lambda z: z.zoom_max)
        an.add("MAP004", f, last.line, f"{W} >> Grid: the largest zoomMax is {last.zoom_max:g}; ctrlMapScale runs up to 1 (fully zoomed out), so the grid may have no class to use at the widest zoom. Community configs end with zoomMax 1 or larger", sev="info")

    if not ms_ok:
        if m.map_size is UNKNOWN:
            an.add("MAP009", f, m.grid_line, f"{W}: mapSize not found in the scanned files (inherited from another config?), so grid number ranges cannot be checked", sev="info")
        return

    # --- label arithmetic ----------------------------------------------------------------------
    if (m.offset_x is not UNKNOWN and not _isnum(m.offset_x)) or (m.offset_y is not UNKNOWN and not _isnum(m.offset_y)):
        return
    for z in m.zooms:
        if not z.numeric:
            continue
        x0, x1, y0, y1 = label_range(m, z)
        c = corner_labels(m, z)
        if x0 < 0 or y0 < 0:
            parts = []
            if x0 < 0:
                parts.append(f"X runs {x0}..{x1}")
            if y0 < 0:
                parts.append(f"Y runs {y0}..{y1}")
            an.add("MAP001", f, z.line, f"{W} >> Grid >> {z.name}: by the community formula the grid numbers go negative over the map ({'; '.join(parts)}; SW corner {c['SW']}, NE corner {c['NE']}). Check offsetX/offsetY (usual: offsetX 0, offsetY = mapSize {m.map_size:g}) and the sign of stepY")
        for axis, hi, fmt in (("X", x1, z.fx), ("Y", y1, z.fy)):
            w = digits_of(fmt)
            if w is not None and len(str(max(abs(hi), 0))) > w:
                an.add("MAP002", f, z.line, f"{W} >> Grid >> {z.name}: the highest {axis} number is {hi} ({len(str(hi))} digits) but format{axis} \"{fmt}\" only has {w}; the number will not fit (the engine's handling of overflow is undocumented). Use a longer format or a larger step")

    # --- consistency between zoom levels -----------------------------------------------------------
    fine_to_coarse = sorted([z for z in m.zooms if z.numeric and _isnum(z.zoom_max)], key=lambda z: z.zoom_max)
    for fz, cz in zip(fine_to_coarse, fine_to_coarse[1:]):
        for axis, sf, sc, ff_, fc in (("X", fz.sx, cz.sx, fz.fx, cz.fx), ("Y", abs(fz.sy), abs(cz.sy), fz.fy, cz.fy)):
            ratio = sc / sf
            if abs(ratio - round(ratio)) > 1e-9 or round(ratio) < 1:
                an.add("MAP006", f, cz.line, f"{W} >> Grid: {cz.name} step{axis} {sc:g} is not a whole multiple of {fz.name} step{axis} {sf:g}; the coarser grid lines then fall between the finer ones and the numbers jump when zooming", sev="warning")
                continue
            r = int(round(ratio))
            wf, wc = digits_of(ff_), digits_of(fc)
            if wf and wc:
                k = round(math.log10(r)) if r > 0 else -1
                if r == 1 or 10 ** k != r or wf - wc != k:
                    an.add("MAP006", f, cz.line, f"{W} >> Grid: going from {fz.name} to {cz.name} the {axis} step grows x{r} while the label shrinks from {wf} to {wc} digits, so the coarse number is not the leading digits of the fine one at the same spot (BI's own grids drop one digit per x10)", sev="info")


# ===========================================================================================
# map controls
# ===========================================================================================
COLOR_PROPS = {
    "colorbackground", "coloroutside", "colortext", "colorinactive", "colorgrid", "colorgridmap", "colornames", "colorsea",
    "colorforest", "colorforestborder", "colorforesttextured", "colorrocks", "colorrocksborder", "colorlevels", "colorcountlines",
    "colormaincountlines", "colorcountlineswater", "colormaincountlineswater", "colorroads", "colorroadsfill", "colormainroads",
    "colormainroadsfill", "colortracks", "colortracksfill", "colortrails", "colortrailsfill", "colorrailway", "colorpowerlines",
    "altitudemapcolorlow", "altitudemapcolormid", "altitudemapcolorhigh",
}
# properties that only a map control has - used to recognise one when `type`/parent are inherited from another file
MAP_ONLY = {
    "colorgrid", "colorgridmap", "colorsea", "colorlevels", "colorcountlines", "colormaincountlines", "colorforest", "colorrocks",
    "scalemin", "scalemax", "scaledefault", "sizeexgrid", "sizeexlevel", "showcountourinterval", "maxsatellitealpha", "ptspersquaresea",
    "ptspersquaretxt", "ptspersquarecln", "ptspersquareexp", "ptspersquarecost", "ptspersquarefor", "ptspersquareforedge",
    "ptspersquareroad", "ptspersquareobj", "alphafadestartscale", "alphafadeendscale", "colormainroads", "colorroads", "colortracks",
}
MAP_KNOWN = COLOR_PROPS | MAP_ONLY | {
    "font", "fontlabel", "fontgrid", "fontunits", "fontnames", "fontinfo", "fontlevel", "runwayfont",
    "sizeex", "sizeexlabel", "sizeexgrid", "sizeexunits", "sizeexnames", "sizeexinfo", "sizeexlevel",
    "ptspersquareforlod1", "ptspersquareforlod2", "ptspersquareroadsimple", "ptspersquaremainroad", "ptspersquaremainroadsimple",
    "ptspersquareobjlod1", "drawobjects", "drawshaded", "shadedsea", "showmarkers", "speedcoefspeed0", "speedcoefspeedmax",
    "stickx", "sticky", "compasspos", "compasssize", "texturecompass", "idcmarkercolor", "idcmarkericon", "textureComboBoxColor".lower(),
    "iconcamera", "iconcameracolor", "iconcamerasize", "moveonedges", "altitudemaprange", "hcollapsed", "ycollapsed",
}
GENERIC = {"idc", "type", "style", "x", "y", "w", "h", "text", "shadow", "access", "show", "fade", "moving", "deletable", "enabled",
           "tooltip", "tooltipcolortext", "tooltipcolorbox", "tooltipcolorshade", "linespacing", "size", "colorforegound", "autofocus"}
MAP_PARENTS = {"rscmapcontrol", "rscmapcontrolempty", "ctrlmap", "ctrlmapempty", "rscmap", "rscmapmain", "ctrlmapmain"}
_CANON_NAMES = (
    "colorBackground colorOutside colorText colorInactive colorGrid colorGridMap colorNames colorSea colorForest colorForestBorder "
    "colorForestTextured colorRocks colorRocksBorder colorLevels colorCountlines colorMainCountlines colorCountlinesWater "
    "colorMainCountlinesWater colorRoads colorRoadsFill colorMainRoads colorMainRoadsFill colorTracks colorTracksFill colorTrails "
    "colorTrailsFill colorRailWay colorPowerLines altitudeMapColorLow altitudeMapColorMid altitudeMapColorHigh scaleMin scaleMax "
    "scaleDefault sizeExGrid sizeExLevel showCountourInterval maxSatelliteAlpha alphaFadeStartScale alphaFadeEndScale "
    "ptsPerSquareSea ptsPerSquareTxt ptsPerSquareCLn ptsPerSquareExp ptsPerSquareCost ptsPerSquareFor ptsPerSquareForEdge ptsPerSquareRoad ptsPerSquareObj"
).split()
CANON = {n.lower(): n for n in _CANON_NAMES}


def _disp(k: str, cls: CfgClass | None = None) -> str:
    if cls is not None and k in cls.names:
        return cls.names[k]
    return CANON.get(k, k)


# the engine's own spelling - `showContourInterval` silently does nothing
SPELLING = {"showcontourinterval": "showCountourInterval"}


def _is_group(cls: CfgClass) -> bool:
    t = cls.props.get("type", (None, 0))[0]
    if t in (15, "CT_CONTROLS_GROUP"):
        return True
    return bool(cls.parent) and "controlsgroup" in cls.parent.lower()


def _is_map(cls: CfgClass) -> bool:
    t = cls.props.get("type", (None, 0))[0]
    if t in (101, "CT_MAP_MAIN"):
        return True
    if cls.parent and cls.parent.lower() in MAP_PARENTS:
        return True
    return sum(1 for k in cls.props if k in MAP_ONLY) >= 2


def collect_map_controls(root: CfgClass) -> list[tuple[CfgClass, list[CfgClass]]]:
    """(map-like class, ancestors) for every class in a config file. A file with top-level map properties
    (an #included fragment such as MapTweaks.hpp) is represented by the root pseudo-class."""
    out = []

    def walk(c: CfgClass, anc: list[CfgClass]):
        if c is not root and _is_map(c):
            out.append((c, anc))
        for ch in c.children.values():
            walk(ch, anc + [c])

    walk(root, [])
    if sum(1 for k in root.props if k in MAP_ONLY) >= 2:
        out.append((root, []))
    return out


def check_map_control(an: "Analyzer", cls: CfgClass, anc: list[CfgClass]) -> dict:
    """Checks one map control; returns the colours/scales it defines (used by the preview)."""
    where = "::".join(cls.path) if cls.path else "(top level of this file)"
    P = cls.props
    style: dict[str, Any] = {}

    for a in anc:
        if _is_group(a) and (cls.props.get("type", (None, 0))[0] in (101, "CT_MAP_MAIN") or (cls.parent or "").lower() in MAP_PARENTS):
            an.add("MAPUI007", cls.file, cls.line, f"{where}: a map control (CT_MAP_MAIN) inside the controls group {a.name}; the wiki says a map control cannot be placed inside a CT_CONTROLS_GROUP. Shipped mods (ACE3) do it for invisible helper controls that only use onDraw; it matters only if this one is meant to be visible")
            break

    for k, (v, ln) in P.items():
        if k in COLOR_PROPS:
            if not isinstance(v, list):
                continue
            style[k] = v
            nums = [x for x in v if _isnum(x)]
            if len(v) != 4:
                an.add("MAPUI001", cls.file, ln, f"{where}: {_disp(k, cls)} has {len(v)} components; colours are RGBA arrays of 4 values")
            bad = [x for x in nums if x < 0 or x > 1]
            if bad:
                an.add("MAPUI001", cls.file, ln, f"{where}: {_disp(k, cls)} component {bad[0]:g} is outside 0..1 (colours are RGBA values from 0 to 1)")
            if k in ("colorgrid", "colorgridmap") and len(v) == 4 and _isnum(v[3]) and v[3] == 0:
                an.add("MAPUI002", cls.file, ln, f"{where}: {_disp(k, cls)} has alpha 0, so the grid lines/labels it colours are invisible", sev="info")
        elif k in ("scalemin", "scalemax", "scaledefault", "sizeexgrid", "maxsatellitealpha"):
            if _isnum(v):
                style[k] = v
        elif k not in MAP_KNOWN and k not in GENERIC and not k.startswith("on") and not k.startswith("tooltip"):
            near = difflib.get_close_matches(k, sorted(MAP_KNOWN), n=1, cutoff=0.86)
            if k in SPELLING:
                an.add("MAPUI004", cls.file, ln, f"{where}: `{_disp(k, cls)}` is not a map property and is ignored; the engine spells it `{SPELLING[k]}` (sic)")
            elif near:
                an.add("MAPUI004", cls.file, ln, f"{where}: `{_disp(k, cls)}` is not a documented map-control property - did you mean `{_disp(near[0])}`? (the wiki list may be incomplete)")

    smin, smax, sdef = (P.get(n, (None, 0))[0] for n in ("scalemin", "scalemax", "scaledefault"))
    if _isnum(smin) and smin <= 0:
        an.add("MAPUI003", cls.file, P["scalemin"][1], f"{where}: scaleMin {smin:g} must be above 0")
    ordered = [(n, P[n.lower()][0], P[n.lower()][1]) for n in ("scaleMin", "scaleDefault", "scaleMax") if n.lower() in P and _isnum(P[n.lower()][0])]
    for (n1, v1, _), (n2, v2, l2) in zip(ordered, ordered[1:]):
        if v1 > v2:
            an.add("MAPUI003", cls.file, l2, f"{where}: {n1} {v1:g} is greater than {n2} {v2:g}; expected scaleMin <= scaleDefault <= scaleMax (ctrlMapScale: 0.001 zoomed in .. 1 zoomed out)")
            break
    g = P.get("sizeexgrid")
    if g and _isnum(g[0]):
        if g[0] <= 0:
            an.add("MAPUI005", cls.file, g[1], f"{where}: sizeExGrid {g[0]:g} - the grid numbers are not drawn", sev="warning")
        elif g[0] < 0.01:
            an.add("MAPUI005", cls.file, g[1], f"{where}: sizeExGrid {g[0]:g} is very small (default 0.02 of the screen height); the grid numbers will be hard to read", sev="info")
    sa = P.get("maxsatellitealpha")
    if sa and _isnum(sa[0]) and (sa[0] < 0 or sa[0] > 1):
        an.add("MAPUI006", cls.file, sa[1], f"{where}: maxSatelliteAlpha {sa[0]:g} is outside 0..1")
    style["_where"] = where
    style["_file"] = cls.file
    style["_line"] = cls.line
    return style
