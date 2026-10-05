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
PREP = OPTICS / "XEH_PREP.hpp"


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
        self.assertIn("PREPS(vision,shadowSamplePattern)", prep)
        self.assertIn("PREPS(vision,shadowClassifyScene)", prep)


if __name__ == "__main__":
    unittest.main()
