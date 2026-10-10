#!/usr/bin/env python3
"""Generate the AEE APP-6 mission-task graphics, modifier glyphs and echelon overlays.

This generator draws MIL-STD-2525D symbology geometry as 64 px black-on-transparent
masks, converts each mask to a .paa with `hemtt utils paa convert`, and registers one
CfgMarkers child per marker in addons/optics/config_modifiers.hpp.

The overlay is BLACK: APP-6 draws the modifiers, mission tasks and echelon ticks in
black over the affiliation-coloured frame.  The engine tint is neutral, so the
overlay supplies its own colour.

Three marker groups are produced:

  * mission tasks  -- AEE_MT_<Name>, the TABLE H-XXIV mission task symbols plus the
    FM 3-90 Appendix B mission-task graphics that the standard defines.  A task with
    no graphic in MIL-STD-2525D or FM 3-90 is NOT invented; it is recorded in
    data/symbology/modifiers.json under "unavailable" with the reason.
  * modifiers      -- AEE_MOD_<Name>, the amplifier glyphs (strength, feint/dummy,
    task-force bracket, HQ staff line, installation bar, planned-status frames).
  * echelon        -- AEE_Ech_<Name>, the unit-size ladder.

Echelon layering rule.  AEE layers the echelon; it does not bake the echelon into
every frame .paa.  Each echelon tick is drawn in the TOP band of a taller 64 x 128
canvas, and the area below the tick band is transparent.  AEE places the echelon
marker at the same map position as the frame marker and the frame marker underneath,
so the ticks sit above the frame.  The echelon is affiliation-neutral (side = 2).
The canvas is 64 x 128 (not 64 x 96) because Arma and hemtt require power-of-two
texture dimensions; 64 x 96 is rejected by `hemtt utils paa convert`.

Geometry sources: MIL-STD-2525D (10 June 2014), Appendix H draw rules, and FM 3-90
Appendix B figures.  MIL-STD-2525 is a US Government work (public domain).  The
drawn geometry here is AEE's own work, GPL-2.0-or-later.

Run:  python3 tools/gen_symbology_modifiers.py
      python3 tools/gen_symbology_modifiers.py --check
      python3 tools/gen_symbology_modifiers.py --table
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from symbology_categories import modifier_category
from typing import Any, Callable

ROOT = Path(__file__).parents[1]
MARKERS_OUT = ROOT / "addons" / "symbology" / "data" / "markers"
CONFIG_OUT = ROOT / "addons" / "symbology" / "config_modifiers.hpp"
JSON_OUT = ROOT / "data" / "symbology" / "modifiers.json"
ADDON_PREFIX = "\\z\\aee\\addons\\symbology\\data\\markers"

LICENSE = "GPL-2.0-or-later"
GEOMETRY_LICENSE = (
    "AEE own work, GPL-2.0-or-later; the symbol geometry is MIL-STD-2525 "
    "(US Government work, public domain)"
)

SIZE = 64
ECH_W, ECH_H = 64, 128
TOP_BAND = 30  # echelon ticks live in y = 0 .. TOP_BAND; below is transparent
SCALE = 4  # supersample factor for smooth strokes

INK = (0, 0, 0, 255)
CLEAR = (0, 0, 0, 0)


class Mask:
    """A black-on-transparent drawing surface in final-pixel coordinates."""

    def __init__(self, w: int = SIZE, h: int = SIZE) -> None:
        from PIL import Image, ImageDraw

        self.w, self.h = w, h
        self.img = Image.new("RGBA", (w * SCALE, h * SCALE), CLEAR)
        self.d = ImageDraw.Draw(self.img)

    def _p(self, p: tuple[float, float]) -> tuple[float, float]:
        return (p[0] * SCALE, p[1] * SCALE)

    def line(
        self, a: tuple[float, float], b: tuple[float, float], width: float = 2.6
    ) -> None:
        self.d.line([self._p(a), self._p(b)], fill=INK, width=round(width * SCALE))

    def poly(self, pts: list[tuple[float, float]], width: float = 2.6) -> None:
        self.d.line(
            [self._p(p) for p in pts],
            fill=INK,
            width=round(width * SCALE),
            joint="curve",
        )

    def filled(self, pts: list[tuple[float, float]]) -> None:
        self.d.polygon([self._p(p) for p in pts], fill=INK)

    def bar(
        self,
        center: tuple[float, float],
        direction: tuple[float, float],
        length: float,
        width: float = 2.6,
    ) -> None:
        dx, dy = direction
        n = math.hypot(dx, dy) or 1.0
        px, py = -dy / n, dx / n
        h = length / 2
        self.line(
            (center[0] - px * h, center[1] - py * h),
            (center[0] + px * h, center[1] + py * h),
            width,
        )

    def arrowhead(
        self,
        tip: tuple[float, float],
        direction: tuple[float, float],
        head: float = 9.0,
        width: float = 8.5,
    ) -> None:
        dx, dy = direction
        n = math.hypot(dx, dy) or 1.0
        ux, uy = dx / n, dy / n
        bx, by = tip[0] - ux * head, tip[1] - uy * head
        px, py = -uy, ux
        self.filled(
            [
                tip,
                (bx + px * width / 2, by + py * width / 2),
                (bx - px * width / 2, by - py * width / 2),
            ]
        )

    def arrow(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        width: float = 2.6,
        head: float = 9.0,
    ) -> None:
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy) or 1.0
        ux, uy = dx / n, dy / n
        self.line(a, (b[0] - ux * head * 0.85, b[1] - uy * head * 0.85), width)
        self.arrowhead(b, (ux, uy), head, head * 0.95)

    def arc_pts(
        self, cx: float, cy: float, r: float, a0: float, a1: float, n: int = 48
    ) -> list[tuple[float, float]]:
        return [
            (
                cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)),
            )
            for i in range(n + 1)
        ]

    def arc(
        self, cx: float, cy: float, r: float, a0: float, a1: float, width: float = 2.6
    ) -> None:
        self.poly(self.arc_pts(cx, cy, r, a0, a1), width)

    def dashed_path(
        self,
        pts: list[tuple[float, float]],
        dash: float = 6.0,
        gap: float = 4.0,
        width: float = 2.6,
        closed: bool = False,
    ) -> None:
        seq = pts + [pts[0]] if closed else pts
        carry = 0.0
        drawing = True
        for i in range(len(seq) - 1):
            (x0, y0), (x1, y1) = seq[i], seq[i + 1]
            seg = math.hypot(x1 - x0, y1 - y0)
            t = 0.0
            while t < seg:
                step = (dash if drawing else gap) - carry
                t2 = min(t + step, seg)
                if drawing:
                    self.line(
                        (x0 + (x1 - x0) * t / seg, y0 + (y1 - y0) * t / seg),
                        (x0 + (x1 - x0) * t2 / seg, y0 + (y1 - y0) * t2 / seg),
                        width,
                    )
                carry = (t2 - t) if (t2 - t) < step else 0.0
                if t2 - t >= step:
                    carry = 0.0
                    drawing = not drawing
                t = t2
        # A closed path alternates cleanly; callers pass explicit points otherwise.

    def dash(
        self,
        a: tuple[float, float],
        b: tuple[float, float],
        dash: float = 6.0,
        gap: float = 4.0,
        width: float = 2.6,
    ) -> None:
        self.dashed_path([a, b], dash, gap, width)

    def dashed_arc(
        self,
        cx: float,
        cy: float,
        r: float,
        a0: float,
        a1: float,
        dash: float = 6.0,
        gap: float = 4.0,
        width: float = 2.6,
    ) -> None:
        self.dashed_path(self.arc_pts(cx, cy, r, a0, a1), dash, gap, width)

    def dashed_closed(
        self,
        pts: list[tuple[float, float]],
        dash: float = 6.0,
        gap: float = 4.0,
        width: float = 2.6,
    ) -> None:
        closed = pts + [pts[0]]
        self.dashed_path(closed, dash, gap, width)

    def dot(self, cx: float, cy: float, r: float = 4.5) -> None:
        self.d.ellipse([self._p((cx - r, cy - r)), self._p((cx + r, cy + r))], fill=INK)

    def ticks(
        self,
        cx: float,
        cy: float,
        r: float,
        count: int,
        a0: float,
        a1: float,
        length: float = 6.0,
        inward: bool = True,
        width: float = 2.4,
    ) -> None:
        for i in range(count):
            a = math.radians(a0 + (a1 - a0) * i / max(count - 1, 1))
            ux, uy = math.cos(a), math.sin(a)
            s = (cx + ux * r, cy + uy * r)
            e = (
                cx + ux * (r + (-length if inward else length)),
                cy + uy * (r + (-length if inward else length)),
            )
            self.line(s, e, width)

    def finish(self):
        from PIL import Image

        return self.img.resize((self.w, self.h), Image.LANCZOS)


# ---------------------------------------------------------------------------
# Mission-task geometry (enemy is up; MIL-STD-2525D TABLE H-XXIV draw rules).
# ---------------------------------------------------------------------------


def _mt_block(m: Mask) -> None:
    # Horizontal block line with a perpendicular tick from its midpoint (340100).
    m.line((10, 38), (54, 38))
    m.line((32, 38), (32, 14))


def _mt_breach(m: Mask) -> None:
    # Two arms enclosing the breach, opening at the top (340200).
    m.line((18, 16), (18, 48))
    m.line((46, 16), (46, 48))
    m.line((18, 48), (46, 48))


def _mt_bypass(m: Mask) -> None:
    # Arms on both sides of the bypassed item (340300).
    m.arrow((20, 50), (20, 16))
    m.arrow((44, 50), (44, 16))
    m.line((20, 50), (44, 50))


def _mt_canalize(m: Mask) -> None:
    # Arms converging to the narrow zone (340400).
    m.line((14, 16), (26, 48))
    m.line((50, 16), (38, 48))
    m.line((26, 48), (38, 48))


def _mt_clear(m: Mask) -> None:
    # Three arrows joined by the limit-of-advance bar (340500).
    m.line((12, 20), (52, 20))
    for x in (18, 32, 46):
        m.arrow((x, 48), (x, 22), head=8)


def _mt_counterattack(m: Mask) -> None:
    # Arrow pointing toward the enemy (340600).
    m.poly([(14, 50), (14, 30), (44, 30)], width=2.8)
    m.arrowhead((44, 30), (1, 0))


def _mt_counterattack_by_fire(m: Mask) -> None:
    # Arrow with the firing bar at its base (340700).
    m.poly([(18, 50), (18, 30), (44, 30)], width=2.8)
    m.arrowhead((44, 30), (1, 0))
    m.line((10, 50), (26, 50), width=2.4)


def _mt_delay(m: Mask) -> None:
    # Arrow with a 180 degree arc at the base (340800).
    m.line((32, 46), (32, 16))
    m.arrowhead((32, 16), (0, -1))
    m.arc(32, 46, 12, 0, 180)


def _mt_destroy(m: Mask) -> None:
    # Dashed crossing lines (340900).
    m.dash((12, 12), (52, 52))
    m.dash((52, 12), (12, 52))


def _mt_disrupt(m: Mask) -> None:
    # Baseline with parallel arrows of varying length (341000).
    m.line((16, 14), (16, 50))
    m.arrow((16, 22), (50, 22), head=8)
    m.arrow((16, 34), (40, 34), head=8)
    m.arrow((16, 44), (40, 44), head=8)


def _mt_fix(m: Mask) -> None:
    # Zigzag arrow (341100).
    m.poly([(10, 34), (17, 22), (26, 42), (35, 22), (44, 42), (52, 34)], width=2.8)
    m.arrowhead((52, 34), (1, 0), head=8)


def _mt_follow_assume(m: Mask) -> None:
    # Plain arrow (341200).
    m.arrow((32, 52), (32, 14))


def _mt_follow_support(m: Mask) -> None:
    # Arrow with a support bar at its base (341300).
    m.arrow((32, 52), (32, 14))
    m.line((18, 52), (46, 52), width=2.4)


def _mt_interdict(m: Mask) -> None:
    # Two arrows with 45 degree angular separation (341400).
    m.arrow((16, 48), (48, 16), head=8)
    m.arrow((48, 48), (16, 16), head=8)


def _mt_isolate(m: Mask) -> None:
    # Circle with a 30 degree opening and inward tics (341500).
    m.arc(32, 32, 20, 210, -30 + 360, width=2.8)
    m.ticks(32, 32, 20, 9, 240, 480, length=6, inward=True)


def _mt_neutralize(m: Mask) -> None:
    # Two lines crossing the target (341600).
    m.line((14, 14), (50, 50))
    m.line((50, 14), (14, 50))


def _mt_occupy(m: Mask) -> None:
    # Circle with an opening crossed by the occupying force (341700).
    m.arc(32, 32, 20, 210, 330, width=2.8)
    m.arrow((22, 44), (30, 36), head=8)


def _mt_penetrate(m: Mask) -> None:
    # Vertical line with an arrow from its midpoint (341800).
    m.line((24, 14), (24, 50))
    m.arrow((24, 32), (52, 32))


def _mt_relief_in_place(m: Mask) -> None:
    # Two arrows connected by a smooth curve (341900).
    m.arrow((16, 46), (12, 18))
    m.arrow((48, 46), (52, 18))
    m.arc(32, 46, 16, 0, 180, width=2.4)


def _mt_retire(m: Mask) -> None:
    # Arrow pointing away with a 180 degree arc at the base (342000).
    m.line((32, 16), (32, 46))
    m.arrowhead((32, 46), (0, 1))
    m.arc(32, 16, 12, 180, 360)


def _mt_secure(m: Mask) -> None:
    # Circle with an opening and an arrow (342100).
    m.arc(32, 32, 20, 210, 330, width=2.8)
    m.ticks(32, 32, 20, 7, 240, 300, length=5, inward=True)
    m.arrow((22, 44), (32, 34), head=8)


def _mt_security_cover(m: Mask) -> None:
    # Security arc with an arrow at each end (342201).
    m.arc(32, 40, 22, 200, 340, width=2.8)
    m.arrowhead(
        (32 + 22 * math.cos(math.radians(200)), 40 + 22 * math.sin(math.radians(200))),
        (-1, 0.4),
        head=8,
    )
    m.arrowhead(
        (32 + 22 * math.cos(math.radians(340)), 40 + 22 * math.sin(math.radians(340))),
        (1, 0.4),
        head=8,
    )


def _mt_security_guard(m: Mask) -> None:
    # Security arc with a centred arrow (342202).
    m.arc(32, 40, 22, 200, 340, width=2.8)
    m.arrow((32, 44), (32, 26), head=8)


def _mt_security_screen(m: Mask) -> None:
    # Straight security line with a centred arrow (342203).
    m.line((10, 40), (54, 40), width=2.8)
    m.arrow((32, 40), (32, 24), head=8)


def _mt_seize(m: Mask) -> None:
    # Looped arrow to the objective (342300).
    m.arc(18, 20, 8, 0, 360, width=2.6)
    m.poly([(24, 28), (36, 34), (46, 44)], width=2.6)
    m.arrowhead((49, 47), (1, 1), head=9)


def _mt_withdraw(m: Mask) -> None:
    # Arrow pointing rearward with a 180 degree arc at the base (342400).
    m.line((44, 18), (18, 44))
    m.arrowhead((14, 48), (-1, 1), head=9)
    m.arc(50, 12, 9, 180, 360, width=2.4)


def _mt_under_pressure(m: Mask) -> None:
    # Withdraw arrow crossed by the pressure bar (342500).
    m.arrow((12, 40), (52, 40))
    m.bar((32, 40), (1, 0), 26, width=2.6)


def _mt_attack_by_fire(m: Mask) -> None:
    # Arrow to the target, base at the firing position (FM 3-90 B-2 / 152000).
    m.poly([(14, 52), (24, 40), (40, 40), (50, 52)], width=2.6)
    m.arrow((32, 40), (32, 12))


def _mt_ambush(m: Mask) -> None:
    # Arrow with a curved back side over the ambush position (141700).
    m.arc(32, 44, 18, 20, 160, width=2.8)
    m.arrow((32, 44), (32, 12))


def _mt_contain(m: Mask) -> None:
    # Semicircle dome with tics and an arrow (FM 3-90 B-18 / 151204).
    m.arc(32, 42, 20, 180, 360, width=2.8)
    m.ticks(32, 42, 20, 9, 190, 350, length=6, inward=False)
    m.arrow((32, 42), (32, 58), head=8)


def _mt_retain(m: Mask) -> None:
    # Circle with an opening and inward tics (FM 3-90 B-10 / 151205).
    m.arc(32, 32, 20, 210, 330, width=2.8)
    m.ticks(32, 32, 20, 11, 240, 480, length=6, inward=True)


def _mt_support_by_fire(m: Mask) -> None:
    # Two diverging arrows from the firing position (FM 3-90 B-13 / 152100).
    m.arrow((32, 54), (10, 14))
    m.arrow((32, 54), (54, 14))


def _mt_turn(m: Mask) -> None:
    # Rounded 90 degree turn arrow (270504 / FM 3-90 B-27).
    m.poly([(16, 52), (16, 32), (20, 24), (30, 20), (48, 20)], width=2.8)
    m.arrowhead((50, 20), (1, 0), head=9)


# ---------------------------------------------------------------------------
# Modifier geometry (fields D, F, S, AB, AC and status).
# ---------------------------------------------------------------------------


def _mod_strength_reinforced(m: Mask) -> None:
    m.line((32, 14), (32, 50))
    m.line((14, 32), (50, 32))


def _mod_strength_reduced(m: Mask) -> None:
    m.line((14, 32), (50, 32))


def _mod_strength_both(m: Mask) -> None:
    m.line((32, 8), (32, 32))
    m.line((18, 20), (46, 20))
    m.line((14, 44), (50, 44))


def _mod_feint_dummy(m: Mask) -> None:
    # Dashed inverted V (field AB, 2525D 5.3.6.4).
    m.dash((12, 46), (32, 20))
    m.dash((52, 46), (32, 20))


def _mod_task_force_bracket(m: Mask) -> None:
    # Standalone task-force bracket (field D, 2525D 5.3.6.3).
    m.line((18, 12), (18, 52))
    m.line((18, 12), (42, 12))
    m.line((18, 52), (42, 52))


def _mod_hq_staff(m: Mask) -> None:
    # HQ staff line descending from the frame's lower left (field S).
    m.line((22, 18), (22, 54))


def _mod_installation(m: Mask) -> None:
    # Filled bar that sits atop the frame (field AC, 2525D 5.3.6.2).
    m.filled([(16, 12), (48, 12), (48, 20), (16, 20)])


def _mod_planned_friend(m: Mask) -> None:
    m.dashed_closed([(10, 20), (54, 20), (54, 48), (10, 48)])


def _mod_planned_hostile(m: Mask) -> None:
    m.dashed_closed([(32, 8), (56, 32), (32, 56), (8, 32)])


def _mod_planned_neutral(m: Mask) -> None:
    m.dashed_closed([(12, 12), (52, 12), (52, 52), (12, 52)])


def _mod_planned_unknown(m: Mask) -> None:
    for cx, cy in ((20, 20), (44, 20), (20, 44), (44, 44)):
        m.dashed_arc(cx, cy, 15, 0, 360, dash=5, gap=4)


# ---------------------------------------------------------------------------
# Echelon geometry (ticks in the TOP band of a 64 x 96 canvas).
# ---------------------------------------------------------------------------


def _ech_team(m: Mask) -> None:
    m.arc(32, 15, 10, 0, 360, width=2.6)
    m.line((25, 22), (39, 8), width=2.6)


def _dots(m: Mask, xs: list[float]) -> None:
    for x in xs:
        m.dot(x, 15, 4.5)


def _ticks(m: Mask, n: int) -> None:
    xs = _spaced(n, 16, 48)
    for x in xs:
        m.line((x, 5), (x, 25), width=2.8)


def _spaced(n: int, lo: float, hi: float) -> list[float]:
    if n == 1:
        return [(lo + hi) / 2]
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]


def _exes(m: Mask, n: int) -> None:
    xs = _spaced(n, 10, 54)
    s = 6.5 if n <= 3 else 5.0
    for x in xs:
        m.line((x - s, 15 - s), (x + s, 15 + s), width=2.6)
        m.line((x + s, 15 - s), (x - s, 15 + s), width=2.6)


# ---------------------------------------------------------------------------
# Marker registry.
# ---------------------------------------------------------------------------

Draw = Callable[[Mask], None]

# (name, kind, title, description, source, draw)
SPECS: list[tuple[str, str, str, str, str, Draw]] = [
    # ---- mission tasks: TABLE H-XXIV --------------------------------
    (
        "AEE_MT_Block",
        "mission_task",
        "Block",
        "Line perpendicular to the avenue of approach, with a tick from its midpoint.",
        "MIL-STD-2525D TABLE H-XXIV code 340100",
        _mt_block,
    ),
    (
        "AEE_MT_Breach",
        "mission_task",
        "Breach",
        "Two arms enclosing the breach location, opening toward the enemy.",
        "MIL-STD-2525D TABLE H-XXIV code 340200",
        _mt_breach,
    ),
    (
        "AEE_MT_Bypass",
        "mission_task",
        "Bypass",
        "Arms on both sides of the bypassed item.",
        "MIL-STD-2525D TABLE H-XXIV code 340300",
        _mt_bypass,
    ),
    (
        "AEE_MT_Canalize",
        "mission_task",
        "Canalize",
        "Arms converging to restrict the enemy to a narrow zone.",
        "MIL-STD-2525D TABLE H-XXIV code 340400",
        _mt_canalize,
    ),
    (
        "AEE_MT_Clear",
        "mission_task",
        "Clear",
        "Arrows joined by the limit-of-advance bar.",
        "MIL-STD-2525D TABLE H-XXIV code 340500",
        _mt_clear,
    ),
    (
        "AEE_MT_Counterattack",
        "mission_task",
        "Counterattack",
        "Arrow toward the enemy.",
        "MIL-STD-2525D TABLE H-XXIV code 340600",
        _mt_counterattack,
    ),
    (
        "AEE_MT_Counterattack_by_Fire",
        "mission_task",
        "Counterattack by Fire",
        "Counterattack arrow with the firing bar at its base.",
        "MIL-STD-2525D TABLE H-XXIV code 340700",
        _mt_counterattack_by_fire,
    ),
    (
        "AEE_MT_Delay",
        "mission_task",
        "Delay",
        "Arrow with a 180 degree arc at the base.",
        "MIL-STD-2525D TABLE H-XXIV code 340800",
        _mt_delay,
    ),
    (
        "AEE_MT_Destroy",
        "mission_task",
        "Destroy",
        "Dashed crossing lines over the target.",
        "MIL-STD-2525D TABLE H-XXIV code 340900",
        _mt_destroy,
    ),
    (
        "AEE_MT_Disrupt",
        "mission_task",
        "Disrupt",
        "Baseline with parallel arrows of varying length.",
        "MIL-STD-2525D TABLE H-XXIV code 341000",
        _mt_disrupt,
    ),
    (
        "AEE_MT_Fix",
        "mission_task",
        "Fix",
        "Zigzag arrow holding the enemy in place.",
        "MIL-STD-2525D TABLE H-XXIV code 341100",
        _mt_fix,
    ),
    (
        "AEE_MT_Follow_and_Assume",
        "mission_task",
        "Follow and Assume",
        "Arrow following the lead force.",
        "MIL-STD-2525D TABLE H-XXIV code 341200",
        _mt_follow_assume,
    ),
    (
        "AEE_MT_Follow_and_Support",
        "mission_task",
        "Follow and Support",
        "Arrow with a support bar at its base.",
        "MIL-STD-2525D TABLE H-XXIV code 341300",
        _mt_follow_support,
    ),
    (
        "AEE_MT_Interdict",
        "mission_task",
        "Interdict",
        "Two arrows with 45 degree angular separation.",
        "MIL-STD-2525D TABLE H-XXIV code 341400",
        _mt_interdict,
    ),
    (
        "AEE_MT_Isolate",
        "mission_task",
        "Isolate",
        "Circle with a 30 degree opening and inward tics.",
        "MIL-STD-2525D TABLE H-XXIV code 341500",
        _mt_isolate,
    ),
    (
        "AEE_MT_Neutralize",
        "mission_task",
        "Neutralize",
        "Two lines crossing the target.",
        "MIL-STD-2525D TABLE H-XXIV code 341600",
        _mt_neutralize,
    ),
    (
        "AEE_MT_Occupy",
        "mission_task",
        "Occupy",
        "Circle with an opening crossed by the occupying force.",
        "MIL-STD-2525D TABLE H-XXIV code 341700",
        _mt_occupy,
    ),
    (
        "AEE_MT_Penetrate",
        "mission_task",
        "Penetrate",
        "Vertical line with an arrow from its midpoint.",
        "MIL-STD-2525D TABLE H-XXIV code 341800",
        _mt_penetrate,
    ),
    (
        "AEE_MT_Relief_in_Place",
        "mission_task",
        "Relief in Place",
        "Two arrows connected by a smooth curve.",
        "MIL-STD-2525D TABLE H-XXIV code 341900",
        _mt_relief_in_place,
    ),
    (
        "AEE_MT_Retire",
        "mission_task",
        "Retire",
        "Arrow pointing away with a 180 degree arc at the base.",
        "MIL-STD-2525D TABLE H-XXIV code 342000",
        _mt_retire,
    ),
    (
        "AEE_MT_Secure",
        "mission_task",
        "Secure",
        "Circle with an opening and an arrow, tics on the perimeter.",
        "MIL-STD-2525D TABLE H-XXIV code 342100",
        _mt_secure,
    ),
    (
        "AEE_MT_Security_Cover",
        "mission_task",
        "Security Cover",
        "Security arc with an arrow at each end.",
        "MIL-STD-2525D TABLE H-XXIV code 342201",
        _mt_security_cover,
    ),
    (
        "AEE_MT_Security_Guard",
        "mission_task",
        "Security Guard",
        "Security arc with a centred arrow.",
        "MIL-STD-2525D TABLE H-XXIV code 342202",
        _mt_security_guard,
    ),
    (
        "AEE_MT_Security_Screen",
        "mission_task",
        "Security Screen",
        "Straight security line with a centred arrow.",
        "MIL-STD-2525D TABLE H-XXIV code 342203",
        _mt_security_screen,
    ),
    (
        "AEE_MT_Seize",
        "mission_task",
        "Seize",
        "Looped arrow to the objective.",
        "MIL-STD-2525D TABLE H-XXIV code 342300",
        _mt_seize,
    ),
    (
        "AEE_MT_Withdraw",
        "mission_task",
        "Withdraw",
        "Arrow pointing rearward with a 180 degree arc at the base.",
        "MIL-STD-2525D TABLE H-XXIV code 342400",
        _mt_withdraw,
    ),
    (
        "AEE_MT_Under_Pressure",
        "mission_task",
        "Under Pressure",
        "Withdraw arrow crossed by the pressure bar.",
        "MIL-STD-2525D TABLE H-XXIV code 342500",
        _mt_under_pressure,
    ),
    # ---- mission tasks: FM 3-90 additions that the standard draws ----
    (
        "AEE_MT_Attack_by_Fire",
        "mission_task",
        "Attack by Fire",
        "Arrow to the target with the base at the firing position.",
        "FM 3-90 figure B-2; MIL-STD-2525D code 152000",
        _mt_attack_by_fire,
    ),
    (
        "AEE_MT_Ambush",
        "mission_task",
        "Ambush",
        "Arrow with a curved back side over the ambush position.",
        "MIL-STD-2525D TABLE H-XII code 141700",
        _mt_ambush,
    ),
    (
        "AEE_MT_Contain",
        "mission_task",
        "Contain",
        "Semicircle enclosing the enemy with tics and an arrow.",
        "FM 3-90 figure B-18; MIL-STD-2525D code 151204",
        _mt_contain,
    ),
    (
        "AEE_MT_Retain",
        "mission_task",
        "Retain",
        "Circle with an opening and inward tics.",
        "FM 3-90 figure B-10; MIL-STD-2525D code 151205",
        _mt_retain,
    ),
    (
        "AEE_MT_Support_by_Fire",
        "mission_task",
        "Support by Fire",
        "Two diverging arrows from the firing position.",
        "FM 3-90 figure B-13; MIL-STD-2525D code 152100",
        _mt_support_by_fire,
    ),
    (
        "AEE_MT_Turn",
        "mission_task",
        "Turn",
        "Rounded 90 degree turn arrow.",
        "MIL-STD-2525D TABLE H-XIX code 270504; FM 3-90 figure B-27",
        _mt_turn,
    ),
    # ---- modifiers ---------------------------------------------------
    (
        "AEE_MOD_Strength_Reinforced",
        "modifier",
        "Strength Reinforced",
        "Reinforced amplifier, a plus sign in the right-hand column.",
        "MIL-STD-2525D Table VII field F",
        _mod_strength_reinforced,
    ),
    (
        "AEE_MOD_Strength_Reduced",
        "modifier",
        "Strength Reduced",
        "Reduced amplifier, a minus sign in the right-hand column.",
        "MIL-STD-2525D Table VII field F",
        _mod_strength_reduced,
    ),
    (
        "AEE_MOD_Strength_Both",
        "modifier",
        "Strength Both",
        "Reinforced and reduced amplifier.",
        "MIL-STD-2525D Table VII field F",
        _mod_strength_both,
    ),
    (
        "AEE_MOD_Feint_Dummy",
        "modifier",
        "Feint Dummy",
        "Dashed inverted V above the frame.",
        "MIL-STD-2525D 5.3.6.4 field AB",
        _mod_feint_dummy,
    ),
    (
        "AEE_MOD_Task_Force_Bracket",
        "modifier",
        "Task Force Bracket",
        "Standalone task-force bracket above the frame.",
        "MIL-STD-2525D 5.3.6.3 field D",
        _mod_task_force_bracket,
    ),
    (
        "AEE_MOD_HQ_Staff",
        "modifier",
        "HQ Staff",
        "Staff line descending from the frame's lower left.",
        "MIL-STD-2525D 5.3.6.5 field S",
        _mod_hq_staff,
    ),
    (
        "AEE_MOD_Installation",
        "modifier",
        "Installation",
        "Filled bar that sits atop the frame.",
        "MIL-STD-2525D 5.3.6.2 field AC",
        _mod_installation,
    ),
    (
        "AEE_MOD_Planned_Friend",
        "modifier",
        "Planned Friend",
        "Planned status: dashed friendly rectangle.",
        "MIL-STD-2525D 5.3.6 status; APP-6C frame grammar",
        _mod_planned_friend,
    ),
    (
        "AEE_MOD_Planned_Hostile",
        "modifier",
        "Planned Hostile",
        "Planned status: dashed hostile diamond.",
        "MIL-STD-2525D 5.3.6 status; APP-6C frame grammar",
        _mod_planned_hostile,
    ),
    (
        "AEE_MOD_Planned_Neutral",
        "modifier",
        "Planned Neutral",
        "Planned status: dashed neutral square.",
        "MIL-STD-2525D 5.3.6 status; APP-6C frame grammar",
        _mod_planned_neutral,
    ),
    (
        "AEE_MOD_Planned_Unknown",
        "modifier",
        "Planned Unknown",
        "Planned status: dashed unknown quatrefoil.",
        "MIL-STD-2525D 5.3.6 status; APP-6C frame grammar",
        _mod_planned_unknown,
    ),
    # ---- echelon overlays (ticks in the top band of a 64 x 96 canvas) --
    (
        "AEE_Ech_Team",
        "echelon",
        "Team",
        "Team or crew: circle with a slash.",
        "MIL-STD-2525D Table D-III",
        _ech_team,
    ),
    (
        "AEE_Ech_Squad",
        "echelon",
        "Squad",
        "Squad: one dot.",
        "MIL-STD-2525D Table D-III",
        lambda m: _dots(m, [32]),
    ),
    (
        "AEE_Ech_Section",
        "echelon",
        "Section",
        "Section: two dots.",
        "MIL-STD-2525D Table D-III",
        lambda m: _dots(m, [24, 40]),
    ),
    (
        "AEE_Ech_Platoon",
        "echelon",
        "Platoon",
        "Platoon: three dots.",
        "MIL-STD-2525D Table D-III",
        lambda m: _dots(m, [16, 32, 48]),
    ),
    (
        "AEE_Ech_Company",
        "echelon",
        "Company",
        "Company or battery: one tick.",
        "MIL-STD-2525D Table D-III",
        lambda m: _ticks(m, 1),
    ),
    (
        "AEE_Ech_Battalion",
        "echelon",
        "Battalion",
        "Battalion or squadron: two ticks.",
        "MIL-STD-2525D Table D-III",
        lambda m: _ticks(m, 2),
    ),
    (
        "AEE_Ech_Regiment",
        "echelon",
        "Regiment",
        "Regiment or group: three ticks.",
        "MIL-STD-2525D Table D-III",
        lambda m: _ticks(m, 3),
    ),
    (
        "AEE_Ech_Brigade",
        "echelon",
        "Brigade",
        "Brigade: one X.",
        "MIL-STD-2525D Table D-III",
        lambda m: _exes(m, 1),
    ),
    (
        "AEE_Ech_Division",
        "echelon",
        "Division",
        "Division: two X.",
        "MIL-STD-2525D Table D-III",
        lambda m: _exes(m, 2),
    ),
    (
        "AEE_Ech_Corps",
        "echelon",
        "Corps",
        "Corps: three X.",
        "MIL-STD-2525D Table D-III",
        lambda m: _exes(m, 3),
    ),
    (
        "AEE_Ech_Army",
        "echelon",
        "Army",
        "Army: four X.",
        "MIL-STD-2525D Table D-III",
        lambda m: _exes(m, 4),
    ),
    (
        "AEE_Ech_Army_Group",
        "echelon",
        "Army Group",
        "Army group: five X.",
        "MIL-STD-2525D Table D-III",
        lambda m: _exes(m, 5),
    ),
    (
        "AEE_Ech_Region",
        "echelon",
        "Region",
        "Region or theatre: six X.",
        "MIL-STD-2525D Table D-III",
        lambda m: _exes(m, 6),
    ),
]

# The complete canonical mission-task list the standard defines, including the
# tasks with no drawable graphic.  It drives the "no invented task" check.
STANDARD_MISSION_TASKS = [
    "Mission_Tasks",
    "Block",
    "Breach",
    "Bypass",
    "Canalize",
    "Clear",
    "Counterattack",
    "Counterattack_by_Fire",
    "Delay",
    "Destroy",
    "Disrupt",
    "Fix",
    "Follow_and_Assume",
    "Follow_and_Support",
    "Interdict",
    "Isolate",
    "Neutralize",
    "Occupy",
    "Penetrate",
    "Relief_in_Place",
    "Retire",
    "Secure",
    "Security_Cover",
    "Security_Guard",
    "Security_Screen",
    "Seize",
    "Withdraw",
    "Under_Pressure",
    "Attack_by_Fire",
    "Ambush",
    "Contain",
    "Escort",
    "Exfiltrate",
    "Pursuit",
    "Reduce",
    "Retain",
    "Suppress",
    "Support_by_Fire",
    "Turn",
]

# Mission tasks the standard does not draw.  A shape is NOT invented for these;
# each carries the reason it cannot be drawn.
UNAVAILABLE: list[dict[str, str]] = [
    {
        "name": "AEE_MT_Mission_Tasks",
        "kind": "mission_task",
        "title": "Mission Tasks (base)",
        "source": "MIL-STD-2525D TABLE H-XXIV code 340000",
        "reason": "The base symbol has no template and no draw rule (both are N/A "
        "in the standard). It is a category header, not a graphic.",
    },
    {
        "name": "AEE_MT_Escort",
        "kind": "mission_task",
        "title": "Escort",
        "source": "MIL-STD-2525D code 110132; FM 3-90 Appendix B",
        "reason": "Code 110132 is an entity subtype of a fixed-wing aircraft (role), "
        "not a mission-task graphic. FM 3-90 Appendix B does not list "
        "Escort. No standard graphic exists.",
    },
    {
        "name": "AEE_MT_Exfiltrate",
        "kind": "mission_task",
        "title": "Exfiltrate",
        "source": "FM 3-90 Appendix B",
        "reason": "FM 3-90 Appendix B defines Exfiltrate but gives no tactical "
        "mission graphic, and MIL-STD-2525D has no mission-task symbol "
        "for it.",
    },
    {
        "name": "AEE_MT_Pursuit",
        "kind": "mission_task",
        "title": "Pursuit",
        "source": "FM 3-90 Appendix B",
        "reason": "Absent from MIL-STD-2525D and FM 3-90 Appendix B. No standard "
        "graphic exists.",
    },
    {
        "name": "AEE_MT_Reduce",
        "kind": "mission_task",
        "title": "Reduce",
        "source": "FM 3-90 Appendix B",
        "reason": "FM 3-90 Appendix B states 'No tactical mission graphic.'",
    },
    {
        "name": "AEE_MT_Suppress",
        "kind": "mission_task",
        "title": "Suppress",
        "source": "FM 3-90 Appendix B",
        "reason": "No mission-task graphic in MIL-STD-2525D or FM 3-90; the only "
        "'Suppress' entry (Suppression of Enemy Air Defense, 110130) is "
        "a different symbol.",
    },
]


def markers() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name, kind, title, desc, source, _draw in SPECS:
        out.append(
            {
                "name": name,
                "kind": kind,
                "title": title,
                "description": desc,
                "source": source,
                "side": 2,
            }
        )
    return out


def render(marker: dict[str, Any], draw: Draw) -> Any:
    if marker["kind"] == "echelon":
        m = Mask(ECH_W, ECH_H)
    else:
        m = Mask(SIZE, SIZE)
    draw(m)
    return m.finish()


def convert(tga: Path, paa: Path) -> None:
    hemtt = shutil.which("hemtt")
    if hemtt is None:
        raise SystemExit("gen_symbology_modifiers: hemtt not found on PATH")
    paa.unlink(missing_ok=True)
    result = subprocess.run(
        [hemtt, "utils", "paa", "convert", str(tga), str(paa)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"paa convert failed for {paa.name}\n{result.stderr}")


def display_name(marker: dict[str, Any]) -> str:
    prefix = {
        "mission_task": "AEE Mission Task",
        "modifier": "AEE Modifier",
        "echelon": "AEE Echelon",
    }[marker["kind"]]
    return f"{prefix} {marker['title']}"


def render_config(markers_: list[dict[str, Any]]) -> str:
    lines = [
        "// Generated by tools/gen_symbology_modifiers.py.  Do not edit by hand.",
        "// The AEE APP-6 mission-task graphics, amplifier modifiers and echelon",
        "// overlays.  Each icon is a real .paa under data/markers.  markerClass and",
        "// size/shadow come from AEE_MarkerBase in config.cpp.",
        "//",
        "// Geometry source: MIL-STD-2525D (US Government work, public domain) and",
        "// FM 3-90 Appendix B.  The drawn geometry is AEE own work,",
        "// SPDX-License-Identifier: GPL-2.0-or-later.",
        "//",
        "// AEE layers the echelon: the AEE_Ech_* textures carry the ticks in the top",
        "// band of a 64 x 128 canvas, so they sit above a frame marker placed at the",
        "// same position.",
        "",
    ]
    for marker in markers_:
        name = marker["name"]
        icon = f"{ADDON_PREFIX}\\{name}.paa"
        lines += [
            f"    class {name}: AEE_MarkerBase {{",
            f'        name = "{display_name(marker)}";',
            f'        icon = "{icon}";',
            f'        texture = "{icon}";',
            f"        side = {marker['side']};",
            f'        markerClass = "{modifier_category(marker["kind"])}";',
            "        scope = 2;",
            "    };",
        ]
    return "\n".join(lines) + "\n"


def render_json(markers_: list[dict[str, Any]]) -> str:
    doc = {
        "generated_by": "tools/gen_symbology_modifiers.py",
        "license": LICENSE,
        "geometry_license": GEOMETRY_LICENSE,
        "echelon_layering": (
            "AEE layers the echelon at runtime; it is not baked into the frame "
            ".paa. Each AEE_Ech_* texture is 64 x 128 with the ticks in the top "
            "band and transparent below, so it sits above a frame marker placed "
            "at the same position. The canvas is 64 x 128 (not 64 x 96) because "
            "Arma and hemtt require power-of-two texture dimensions."
        ),
        "counts": {
            "mission_task": sum(1 for x in markers_ if x["kind"] == "mission_task"),
            "modifier": sum(1 for x in markers_ if x["kind"] == "modifier"),
            "echelon": sum(1 for x in markers_ if x["kind"] == "echelon"),
        },
        "markers": markers_,
        "unavailable": UNAVAILABLE,
    }
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def build() -> int:
    MARKERS_OUT.mkdir(parents=True, exist_ok=True)
    markers_ = markers()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for (name, kind, title, desc, source, draw), marker in zip(SPECS, markers_):
            tga = tmp_dir / f"{name}.tga"
            render(marker, draw).save(tga)
            convert(tga, MARKERS_OUT / f"{name}.paa")
    CONFIG_OUT.write_text(render_config(markers_), encoding="utf-8")
    JSON_OUT.write_text(render_json(markers_), encoding="utf-8")
    print(
        f"symbology modifiers: {len(markers_)} markers written "
        f"({len(UNAVAILABLE)} mission tasks unavailable)"
    )
    return 0


def check() -> int:
    markers_ = markers()
    stale: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for (name, kind, title, desc, source, draw), marker in zip(SPECS, markers_):
            committed = MARKERS_OUT / f"{name}.paa"
            if not committed.is_file():
                stale.append(f"{name}.paa is missing")
                continue
            tga = tmp_dir / f"{name}.tga"
            render(marker, draw).save(tga)
            fresh = tmp_dir / f"{name}.paa"
            convert(tga, fresh)
            if committed.read_bytes() != fresh.read_bytes():
                stale.append(f"{name}.paa is stale")
    if CONFIG_OUT.read_text(encoding="utf-8") != render_config(markers_):
        stale.append("config_modifiers.hpp is stale")
    if JSON_OUT.read_text(encoding="utf-8") != render_json(markers_):
        stale.append("modifiers.json is stale")
    if stale:
        print(f"symbology modifiers: FAIL ({len(stale)})")
        for line in stale:
            print(f"  {line}")
        return 1
    print(f"symbology modifiers: {len(markers_)} markers fresh")
    return 0


def table() -> int:
    for marker in markers():
        print(
            f"{marker['name']}\t{marker['kind']}\t{marker['source']}\t"
            f"{marker['description']}"
        )
    for entry in UNAVAILABLE:
        print(f"{entry['name']}\t{entry['kind']}\tUNAVAILABLE\t{entry['reason']}")
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check()
    if "--table" in argv:
        return table()
    return build()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
