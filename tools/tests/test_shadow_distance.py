#!/usr/bin/env python3
"""Scene-aware shadow distance kernels and driver (aee-workshop-copy item 6).

The kernels are pure: no missionNamespace, no GVAR or EGVAR, no engine
command.  These tests run the REAL SQF through the SQF lite interpreter and
cross-check it against a Python mirror of the same spec, so a constant change
in the SQF fails here until the mirror is re-synced.

The values are re-derived from Adaptive Shadows (Workshop 3792830104).  The
mod publishes no licence, so this is a re-implementation, not copied code.
The sample pattern and the scene thresholds are UNSOURCED heuristics.

MUTATION PROOF (executed by hand at commit time):
  - force the coherent-neighbour test false in fnc_shadowClassifyScene.sqf ->
    ``test_open_scene_selects_open`` changes its scene; restore -> OK.

Run: python3 -m unittest tools.tests.test_shadow_distance -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))

from sqf_lite import run_sqf  # noqa: E402

OPTICS = REPO / "addons" / "optics"
VISION = OPTICS / "functions" / "vision"
PATTERN = VISION / "fnc_shadowSamplePattern.sqf"
CLASSIFY = VISION / "fnc_shadowClassifyScene.sqf"
TARGET = VISION / "fnc_shadowTargetDistance.sqf"
SMOOTH = VISION / "fnc_shadowSmoothDistance.sqf"
GOVERNOR = VISION / "fnc_shadowFpsGovernor.sqf"
STABILIZE = VISION / "fnc_shadowStabilizeDepth.sqf"
DRIVER = VISION / "fnc_calculateViewDistance.sqf"
PREP = OPTICS / "XEH_PREP.hpp"
INIT_SETTINGS = OPTICS / "initSettings.inc.sqf"
STRINGTABLE = OPTICS / "stringtable.xml"
CONFIG_DOCS = REPO / "docs" / "wiki" / "chapters" / "configuration.qmd"


# ─── Python mirror of the classification spec ────────────────────────────────


def mirror_pattern(count: int, optics: bool) -> list[list[float]]:
    base = [
        [0.50, 0.50, 2.00],
        [0.32, 0.50, 1.25],
        [0.68, 0.50, 1.25],
        [0.50, 0.34, 1.20],
        [0.50, 0.66, 1.10],
        [0.32, 0.34, 1.00],
        [0.68, 0.34, 1.00],
        [0.32, 0.66, 0.95],
        [0.68, 0.66, 0.95],
        [0.14, 0.50, 0.80],
        [0.86, 0.50, 0.80],
        [0.50, 0.18, 0.80],
        [0.50, 0.82, 0.70],
        [0.14, 0.34, 0.70],
        [0.86, 0.34, 0.70],
        [0.14, 0.66, 0.65],
        [0.86, 0.66, 0.65],
        [0.32, 0.18, 0.65],
        [0.68, 0.18, 0.65],
        [0.32, 0.82, 0.60],
        [0.68, 0.82, 0.60],
        [0.08, 0.20, 0.55],
        [0.92, 0.20, 0.55],
        [0.08, 0.80, 0.50],
        [0.92, 0.80, 0.50],
    ]
    n = round(max(5, min(count, len(base))))
    out = []
    for x, y, w in base[:n]:
        if optics:
            x = 0.5 + (x - 0.5) * 0.52
            y = 0.5 + (y - 0.5) * 0.52
        out.append([x, y, w])
    return out


def _weighted_percentile(
    values: list[list[float]], fraction: float, default: float
) -> float:
    if not values:
        return default
    ordered = sorted(values, key=lambda pair: pair[0])
    total = sum(max(w, 0) for _, w in ordered)
    if total <= 0:
        return default
    threshold = total * max(0.0, min(1.0, fraction))
    acc = 0.0
    result = ordered[-1][0]
    selected = False
    for d, w in ordered:
        if not selected:
            acc += max(w, 0)
            if acc >= threshold:
                result = d
                selected = True
    return result


def mirror_classify(
    samples, fallback, context, effective_max, opening_sensitivity=12, far_influence=75
):
    if not samples:
        return [fallback, "UNKNOWN", fallback, fallback, 0, 0, 0]
    near_pairs = []
    total_dir = 0.0
    obj_w = 0.0
    terr_w = 0.0
    for d, w, sx, sy, kind in samples:
        aw = max(w, 0)
        if kind == 1 and sy > 0.62:
            aw *= 0.30
        if kind != 3:
            total_dir += aw
        if kind in (0, 1):
            near_pairs.append([max(d, 0), aw])
            if kind == 0:
                obj_w += aw
            else:
                terr_w += aw
    near = _weighted_percentile(near_pairs, 0.50, fallback)
    base = _weighted_percentile(near_pairs, 0.65, near)
    far_thr = min(max(near * 2.3, 25), max(effective_max, 25))
    far_cand = []
    for d, w, sx, sy, kind in samples:
        aw = max(w, 0)
        if kind == 1 and sy > 0.62:
            aw *= 0.30
        if kind == 2 or (kind in (0, 1) and d >= far_thr):
            far_cand.append([d, aw, sx, sy, kind])
    far_pairs = []
    coh = 0.0
    center = 0.0
    for i, c in enumerate(far_cand):
        d, w, sx, sy, _kind = c
        has = False
        for j, o in enumerate(far_cand):
            if j != i:
                dx = o[2] - sx
                dy = o[3] - sy
                if dx * dx + dy * dy <= 0.09:
                    has = True
        if has:
            far_pairs.append([d, w])
            coh += w
            if 0.24 <= sx <= 0.76 and 0.24 <= sy <= 0.76:
                center += w
    opening = min(coh / total_dir, 1) if total_dir > 0 else 0
    far = _weighted_percentile(far_pairs, 0.75, base)
    obj_cov = obj_w / total_dir if total_dir > 0 else 0
    terr_cov = terr_w / total_dir if total_dir > 0 else 0
    ctx = context if len(context) >= 5 else [False, 0, 0, 12, 0]
    hcap = max(ctx[4] - 1, 1)
    ctx_score = (0.45 if ctx[0] else 0) + 0.55 * min(ctx[2] / hcap, 1)
    near_factor = 1 - min(near / 40, 1)
    screen_interior = obj_cov * (0.55 + 0.45 * near_factor) * (1 - opening)
    interior = min(max(ctx_score, screen_interior * 0.80), 1)
    sens = min(max(opening_sensitivity / 100, 0.03), 0.50)
    fi = min(max(far_influence / 100, 0), 1)
    scene = "NEAR"
    if interior >= 0.62:
        if opening >= sens:
            scene = "OPENING"
        elif center > 0 and far >= near * 1.8:
            scene = "CORRIDOR"
        else:
            scene = "INTERIOR"
    else:
        if opening >= 0.45:
            scene = "OPEN"
        elif obj_cov >= 0.40 and opening >= sens:
            scene = "URBAN"
        elif opening >= sens:
            scene = "MIXED"
    depth = base
    if far_pairs and (opening >= sens or scene == "CORRIDOR"):
        cov_factor = min(opening / 0.55, 1)
        blend = cov_factor * fi
        if scene == "CORRIDOR":
            blend = max(blend, 0.35 * fi)
        depth = base + (far - base) * blend
    depth = min(max(depth, 0), max(effective_max, 0))
    return [depth, scene, near, far, opening, interior, terr_cov]


# ─── Harness wrappers ────────────────────────────────────────────────────────


def pattern(count: int = 13, optics: bool = False):
    return run_sqf(PATTERN, [count, optics])


def classify(
    samples,
    fallback=0,
    context=None,
    effective_max=0,
    opening_sensitivity=12,
    far_scene_influence=75,
):
    if context is None:
        context = [False, 0, 0, 12, 0]
    return run_sqf(
        CLASSIFY,
        [
            samples,
            fallback,
            context,
            effective_max,
            opening_sensitivity,
            far_scene_influence,
        ],
    )


def target(
    depth=0,
    effective_min=0,
    effective_max=500,
    turn_level=0,
    scene_state="OUTSIDE",
    speed=0,
    in_vehicle=False,
    optics=False,
    margins=None,
):
    if margins is None:
        margins = [12, 0.6, 1.25, 0, 0]
    return run_sqf(
        TARGET,
        [
            depth,
            effective_min,
            effective_max,
            turn_level,
            scene_state,
            speed,
            in_vehicle,
            optics,
            margins,
        ],
    )


def smooth(
    target_value=0, current=0, delta_time=0.1, increase=2000, decrease=1000, fast=False
):
    return run_sqf(
        SMOOTH, [target_value, current, delta_time, increase, decrease, fast]
    )


def governor(
    fps_smooth=60,
    fps_raw=60,
    target_fps=0,
    deadband=3,
    ceiling=500,
    effective_min=0,
    effective_max=500,
    delta_time=0.1,
    smoothing_time=0.5,
):
    return run_sqf(
        GOVERNOR,
        [
            fps_smooth,
            fps_raw,
            target_fps,
            deadband,
            ceiling,
            effective_min,
            effective_max,
            delta_time,
            smoothing_time,
        ],
    )


def stabilize(
    raw_depth=0,
    scene="NEAR",
    now=0,
    interior=0,
    opening=0,
    sensitivity=12,
    decrease_delay=0.3,
    state=None,
):
    if state is None:
        state = ["OUTSIDE", 0, 0, 0, "NEAR", "", -1, 0]
    return run_sqf(
        STABILIZE,
        [raw_depth, scene, now, interior, opening, sensitivity, decrease_delay, state],
    )


def sky_samples(count: int = 9, distance: float = 200.0):
    points = pattern(count, False)
    return [[distance, p[2], p[0], p[1], 2] for p in points]


def live_source(path: Path) -> str:
    """Source with comments stripped, so a commented-out line cannot satisfy
    a contract assertion."""
    text = path.read_text(encoding="utf-8")
    text = text.replace("/*", "\n/*")
    lines = []
    in_block = False
    for line in text.splitlines():
        out = []
        i = 0
        while i < len(line):
            if in_block:
                end = line.find("*/", i)
                if end == -1:
                    break
                in_block = False
                i = end + 2
                continue
            start = line.find("/*", i)
            comment = line.find("//", i)
            if start != -1 and (comment == -1 or start < comment):
                out.append(line[i:start])
                in_block = True
                i = start + 2
                continue
            if comment != -1:
                out.append(line[i:comment])
                break
            out.append(line[i:])
            break
        lines.append("".join(out))
    return "\n".join(lines)


class TestShadowSamplePattern(unittest.TestCase):
    def test_pattern_has_25_unique_points(self) -> None:
        got = pattern(25, False)
        self.assertEqual(len(got), 25)
        points = {(round(p[0], 6), round(p[1], 6)) for p in got}
        self.assertEqual(len(points), 25)

    def test_requested_count_is_clamped_to_5_25(self) -> None:
        self.assertEqual(len(pattern(1, False)), 5)
        self.assertEqual(len(pattern(100, False)), 25)
        self.assertEqual(len(pattern(13, False)), 13)
        self.assertEqual(len(pattern(13, False)), len(mirror_pattern(13, False)))

    def test_optics_contracts_toward_the_centre(self) -> None:
        plain = pattern(25, False)
        optics = pattern(25, True)
        for a, b in zip(plain, optics):
            # The centre point is invariant; every other point moves in.
            self.assertLessEqual(abs(b[0] - 0.5), abs(a[0] - 0.5))
            self.assertLessEqual(abs(b[1] - 0.5), abs(a[1] - 0.5))
            self.assertAlmostEqual(b[0], 0.5 + (a[0] - 0.5) * 0.52, places=9)
            self.assertAlmostEqual(b[1], 0.5 + (a[1] - 0.5) * 0.52, places=9)
            self.assertEqual(b[2], a[2])

    def test_mirror_matches_the_pattern(self) -> None:
        for optics in (False, True):
            for count in (5, 13, 25):
                with self.subTest(optics=optics, count=count):
                    self.assertEqual(
                        pattern(count, optics), mirror_pattern(count, optics)
                    )


class TestShadowClassifyScene(unittest.TestCase):
    def test_empty_samples_return_the_fallback(self) -> None:
        got = classify([], 42, effective_max=500)
        self.assertEqual(got, [42, "UNKNOWN", 42, 42, 0, 0, 0])

    def test_open_scene_selects_open(self) -> None:
        got = classify(
            sky_samples(9, 500), context=[False, 0, 0, 12, 0], effective_max=500
        )
        self.assertEqual(got[1], "OPEN")
        self.assertEqual(
            got[0],
            mirror_classify(sky_samples(9, 500), 0, [False, 0, 0, 12, 0], 500)[0],
        )

    def test_enclosed_context_selects_interior(self) -> None:
        samples = [
            [30, 1.0, 0.50, 0.50, 0],
            [30, 1.0, 0.10, 0.90, 0],
        ]
        got = classify(samples, context=[True, 8, 8, 3, 9], effective_max=500)
        self.assertEqual(got[1], "INTERIOR")
        self.assertGreaterEqual(got[5], 0.62)
        self.assertLess(got[4], 0.12)

    def test_depth_is_clamped_to_the_effective_max(self) -> None:
        for cap in (50, 120, 500):
            with self.subTest(cap=cap):
                got = classify(sky_samples(9, 1000), effective_max=cap)
                self.assertLessEqual(got[0], cap)
                self.assertGreaterEqual(got[0], 0)
        self.assertEqual(classify(sky_samples(9, 1000), effective_max=0)[0], 0)

    def test_mirror_matches_sqf_over_a_sweep(self) -> None:
        sweeps = [
            (sky_samples(13, 120), 0, [False, 0, 0, 12, 0], 200),
            (sky_samples(25, 800), 0, [True, 8, 8, 3, 9], 1000),
            (
                [[15, 1.0, 0.5, 0.5, 0], [40, 0.8, 0.32, 0.5, 1]],
                9,
                [False, 2, 1, 12, 3],
                300,
            ),
            (
                [
                    [120, 1.0, 0.50, 0.50, 0],
                    [150, 0.9, 0.68, 0.34, 1],
                    [60, 0.7, 0.14, 0.50, 0],
                    [900, 0.5, 0.86, 0.66, 2],
                ],
                7,
                [True, 6, 5, 10, 8],
                1000,
            ),
            ([], 5, [False, 0, 0, 12, 0], 500),
        ]
        for samples, fallback, context, cap in sweeps:
            with self.subTest(samples=len(samples), cap=cap):
                got = classify(samples, fallback, context, cap)
                want = mirror_classify(samples, fallback, context, cap)
                self.assertEqual(got[1], want[1])
                for i in (0, 2, 3, 4, 5, 6):
                    self.assertAlmostEqual(got[i], want[i], places=9)

    def test_kernel_is_pure(self) -> None:
        for path in (CLASSIFY, PATTERN):
            text = live_source(path)
            for token in (
                "missionNamespace",
                "GVAR(",
                "EGVAR(",
                "screenToWorldDirection",
                "lineIntersectsSurfaces",
                "getShadowDistance",
            ):
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, text)

    def test_headers_carry_the_source_marking(self) -> None:
        for path in (CLASSIFY, PATTERN):
            text = path.read_text(encoding="utf-8")
            self.assertIn("3792830104", text)
            self.assertIn("no licence", text)
            self.assertIn("No mod content is copied", text)
            self.assertIn("UNSOURCED", text)

    def test_prep_entries_exist(self) -> None:
        prep = PREP.read_text(encoding="utf-8")
        for entry in (
            "PREPS(vision,shadowSamplePattern)",
            "PREPS(vision,shadowClassifyScene)",
            "PREPS(vision,shadowTargetDistance)",
            "PREPS(vision,shadowSmoothDistance)",
            "PREPS(vision,shadowFpsGovernor)",
            "PREPS(vision,shadowStabilizeDepth)",
        ):
            with self.subTest(entry=entry):
                self.assertIn(entry, prep)


class TestShadowTargetDistance(unittest.TestCase):
    def test_margin_adds_to_depth(self) -> None:
        self.assertAlmostEqual(target(200, 0, 500, margins=[12, 0, 0, 0, 0]), 212)

    def test_enclosed_scales_the_margins(self) -> None:
        outside = target(
            200, 0, 500, turn_level=1, scene_state="OUTSIDE", margins=[12, 0, 0, 100, 0]
        )
        enclosed = target(
            200,
            0,
            500,
            turn_level=1,
            scene_state="ENCLOSED",
            margins=[12, 0, 0, 100, 0],
        )
        self.assertAlmostEqual(outside, 312)
        # 12 + (100 * 1 * 0.25) = 37
        self.assertAlmostEqual(enclosed, 237)

    def test_movement_vehicle_and_optics_margins(self) -> None:
        # speed 10, movement 0.6 -> 6; vehicle 1.25 -> 12.5; optics 30.
        got = target(
            0,
            0,
            500,
            speed=10,
            in_vehicle=True,
            optics=True,
            margins=[12, 0.6, 1.25, 0, 30],
        )
        self.assertAlmostEqual(got, 12 + 6 + 12.5 + 30)

    def test_clamped_to_min_and_max(self) -> None:
        self.assertAlmostEqual(target(10, 100, 500, margins=[12, 0, 0, 0, 0]), 100)
        self.assertAlmostEqual(target(900, 0, 500, margins=[12, 0, 0, 0, 0]), 500)
        self.assertEqual(target(200, 0, 0, margins=[12, 0, 0, 0, 0]), 0)


class TestShadowSmoothDistance(unittest.TestCase):
    def test_increase_and_decrease_are_rate_limited(self) -> None:
        # increase 2000 m/s over 0.1 s = 200 m
        self.assertAlmostEqual(smooth(1000, 0, 0.1, 2000, 1000), 200)
        # decrease 1000 m/s over 0.1 s = 100 m
        self.assertAlmostEqual(smooth(0, 1000, 0.1, 2000, 1000), 900)
        # fast decrease multiplies the decrease by 1.35 -> 135 m
        self.assertAlmostEqual(smooth(0, 1000, 0.1, 2000, 1000, True), 865)

    def test_close_target_snaps(self) -> None:
        self.assertAlmostEqual(smooth(1000, 999.995, 0.1), 1000)

    def test_step_never_overshoots(self) -> None:
        self.assertAlmostEqual(smooth(5, 0, 1.0, 2000, 1000), 5)


class TestShadowFpsGovernor(unittest.TestCase):
    def test_governor_lowers_the_ceiling_below_target_fps(self) -> None:
        smooth_fps, ceiling = governor(60, 20, 60, 3, 500, 0, 500, 0.1, 0.5)
        self.assertLess(smooth_fps, 60)
        self.assertLess(ceiling, 500)
        self.assertGreaterEqual(ceiling, 0)

    def test_governor_recovers_above_target_fps(self) -> None:
        _, ceiling = governor(60, 120, 60, 3, 200, 0, 500, 0.1, 0.5)
        # recovery 120 m/s over 0.1 s = 12 m
        self.assertAlmostEqual(ceiling, 212)

    def test_governor_off_returns_the_effective_max(self) -> None:
        _, ceiling = governor(60, 120, 0, 3, 200, 0, 500, 0.1, 0.5)
        self.assertEqual(ceiling, 500)

    def test_governor_never_goes_below_the_minimum(self) -> None:
        _, ceiling = governor(60, 1, 60, 3, 50, 50, 500, 1.0, 0.5)
        self.assertGreaterEqual(ceiling, 50)


class TestShadowStabilizeDepth(unittest.TestCase):
    def test_first_call_holds_the_raw_depth(self) -> None:
        depth, state, fast, _ = stabilize(120, "NEAR", 0, 0, 0)
        self.assertAlmostEqual(depth, 120)
        self.assertEqual(state, "OUTSIDE")
        self.assertFalse(fast)

    def test_enclosed_needs_two_entries(self) -> None:
        depth, state, fast, st = stabilize(20, "INTERIOR", 0, 0.9, 0.0)
        self.assertEqual(state, "ENTERING")
        self.assertFalse(fast)
        depth, state, fast, st = stabilize(20, "INTERIOR", 0.1, 0.9, 0.0, state=st)
        self.assertEqual(state, "ENCLOSED")
        self.assertTrue(fast)
        self.assertAlmostEqual(depth, 20)

    def test_state_round_trips(self) -> None:
        _, _, _, st = stabilize(100, "OPEN", 0, 0, 1.0)
        self.assertEqual(len(st), 8)
        self.assertEqual(st[0], "OUTSIDE")


class TestShadowKernelPurityAndMarking(unittest.TestCase):
    def test_kernels_are_pure(self) -> None:
        for path in (TARGET, SMOOTH, GOVERNOR, STABILIZE):
            text = live_source(path)
            for token in (
                "missionNamespace",
                "GVAR(",
                "EGVAR(",
                "diag_fps",
                "getShadowDistance",
                "setVariable",
            ):
                with self.subTest(path=path.name, token=token):
                    self.assertNotIn(token, text)

    def test_headers_carry_the_source_marking(self) -> None:
        for path in (TARGET, SMOOTH, GOVERNOR, STABILIZE):
            text = path.read_text(encoding="utf-8")
            self.assertIn("3792830104", text)
            self.assertIn("no licence", text)
            self.assertIn("No mod content is copied", text)
            self.assertIn("UNSOURCED", text)


class TestShadowDriverContract(unittest.TestCase):
    def test_driver_publishes_the_shadow_state_above_the_interface_exit(self) -> None:
        live = live_source(DRIVER)
        exit_idx = live.index("if (!hasInterface) exitWith")
        for name in ("shadowTarget", "shadowScene", "shadowCoverage"):
            marker = f"missionNamespace setVariable [QGVAR({name})"
            with self.subTest(name=name):
                self.assertIn(marker, live)
                self.assertLess(
                    live.index(marker),
                    exit_idx,
                    f"{name} is published below the interface exit",
                )

    def test_driver_never_calls_set_view_distance_from_the_shadow_path(self) -> None:
        live = live_source(DRIVER)
        exit_idx = live.index("if (!hasInterface) exitWith")
        # Every setViewDistance call is the terrain ramp, below the exit.  The
        # shadow path (above the exit) owns only setObjectViewDistance.
        self.assertGreater(live.index("setViewDistance"), exit_idx)

    def test_driver_calls_the_shadow_kernels(self) -> None:
        live = live_source(DRIVER)
        for entry in (
            "FUNC(shadowSamplePattern)",
            "FUNC(shadowClassifyScene)",
            "FUNC(shadowStabilizeDepth)",
            "FUNC(shadowTargetDistance)",
            "FUNC(shadowSmoothDistance)",
            "FUNC(shadowFpsGovernor)",
        ):
            with self.subTest(entry=entry):
                self.assertIn(entry, live)

    def test_driver_clamps_the_shadow_target_to_the_object_target(self) -> None:
        live = live_source(DRIVER)
        self.assertIn("_targetDistance = _targetDistance min _objTarget", live)
        self.assertIn(
            "_shadowTarget = ((_candidate min _ceilingNew) max 0) min _objTarget", live
        )

    def test_driver_reads_the_settings_not_constants(self) -> None:
        live = live_source(DRIVER)
        for name in (
            "shadowAdaptiveEnabled",
            "shadowMinDistance",
            "shadowMaxDistance",
            "shadowSampleCount",
            "shadowUpdateInterval",
            "shadowOpeningSensitivity",
            "shadowFarSceneInfluence",
            "shadowMovementProtection",
            "shadowCameraTurnProtection",
            "shadowOpticsProtection",
            "shadowTargetFPS",
        ):
            with self.subTest(name=name):
                self.assertIn(f"QGVAR({name})", live)

    def test_driver_holds_the_last_value_when_the_map_is_open(self) -> None:
        live = live_source(DRIVER)
        self.assertIn("visibleMap", live)

    def test_driver_applies_the_shadow_target_on_its_own_trigger(self) -> None:
        """C2: the shadow target must reach the engine outside the object
        deadband block.  The object deadband is 200 m, so if the only apply
        site sits inside the ``_newObj != _objCurrent`` block the scene-aware
        value is inert in steady state.  An independent apply site is
        required."""
        live = live_source(DRIVER)
        start = live.index("if (_newObj != _objCurrent) then {")
        open_brace = live.index("{", start)
        depth = 0
        end = None
        for i in range(open_brace, len(live)):
            char = live[i]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        self.assertIsNotNone(end, "the object deadband block is not closed")
        assert end is not None
        outside = live[:start] + live[end + 1 :]
        # The independent apply writes the second element only.
        self.assertIn("round _shadowTarget", outside)
        self.assertIn("setObjectViewDistance", outside)


SHADOW_SETTINGS = (
    ("shadowAdaptiveEnabled", "CHECKBOX", "true"),
    ("shadowMinDistance", "SLIDER", "0,500,50,0"),
    ("shadowMaxDistance", "SLIDER", "25,2000,500,0"),
    ("shadowSampleCount", "SLIDER", "5,25,13,0"),
    ("shadowUpdateInterval", "SLIDER", "0.10,2,0.10,2"),
    ("shadowOpeningSensitivity", "SLIDER", "3,50,12,0"),
    ("shadowFarSceneInfluence", "SLIDER", "0,100,75,0"),
    ("shadowMovementProtection", "SLIDER", "0,10,0.6,2"),
    ("shadowCameraTurnProtection", "SLIDER", "0,500,0,0"),
    ("shadowOpticsProtection", "SLIDER", "0,500,0,0"),
    ("shadowTargetFPS", "SLIDER", "0,240,0,0"),
)


class TestShadowSettings(unittest.TestCase):
    def test_settings_register_in_the_shadows_group(self) -> None:
        live = live_source(INIT_SETTINGS)
        for name, kind, args in SHADOW_SETTINGS:
            entry = f'AEE_SETTING_{kind}({name},"AEE Optics","Shadows",{args})'
            with self.subTest(name=name):
                self.assertIn(entry, live)

    def test_stringtable_carries_the_keys(self) -> None:
        text = STRINGTABLE.read_text(encoding="utf-8")
        for name, _kind, _args in SHADOW_SETTINGS:
            for suffix in ("Name", "Description"):
                key = f"STR_AEE_Optics_{name}_{suffix}"
                with self.subTest(key=key):
                    self.assertIn(key, text)

    def test_configuration_docs_are_regenerated(self) -> None:
        doc = CONFIG_DOCS.read_text(encoding="utf-8")
        for name, _kind, _args in SHADOW_SETTINGS:
            with self.subTest(name=name):
                self.assertIn(f"aee_optics_{name}", doc)

    def test_no_new_top_level_category(self) -> None:
        live = live_source(INIT_SETTINGS)
        for name, kind, args in SHADOW_SETTINGS:
            entry = f'AEE_SETTING_{kind}({name},"AEE Optics","Shadows",{args})'
            with self.subTest(name=name):
                self.assertIn(entry, live)


if __name__ == "__main__":
    unittest.main()
