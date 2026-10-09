#!/usr/bin/env python3
"""Fusion display regression guards (operator report 2026-10-03).

Two full-view artefacts shipped ON by default and dominated the fusion view:

  1. The fusion FOV frame drew its four bars at the safe-zone edge whenever the
     thermal channel half-angle equalled half the NVG field (ENVG-B ratio 1),
     so the operator saw a border around the WHOLE view instead of an inset.
  2. The fusion HUD "glass" control painted a translucent red-orange panel over
     the NVG image, so the NVG looked washed brown instead of the correct green
     phosphor.  The panel is restored as the source box's four EDGES, which
     cannot wash the image.

These tests would have caught both.  They scan the display config for a
non-zero-alpha background over (nearly) the full safe zone, and they prove the
frame driver discards the display at the field edge by executing the pure
geometry and visibility kernels.

Run: python3 -m unittest tools.tests.test_fusion_display_guard -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO))

from sqf_lite import run_sqf  # noqa: E402

THERMAL = REPO / "addons" / "thermal_display"
RSC = THERMAL / "RscTitles.hpp"
SCRIPT_COMPONENT = THERMAL / "script_component.hpp"
FUSION = THERMAL / "functions" / "fusion"
PREP = THERMAL / "XEH_PREP.hpp"
FRAME_GEOMETRY = FUSION / "fnc_fusionFrameGeometry.sqf"
FRAME_VISIBLE = FUSION / "fnc_fusionFrameVisible.sqf"
FRAME_DRIVER = FUSION / "fnc_updateFusionFrame.sqf"
HUD = THERMAL / "functions" / "hud"

RSC_SRC = RSC.read_text(encoding="utf-8")
SCRIPT_COMPONENT_SRC = SCRIPT_COMPONENT.read_text(encoding="utf-8")
PREP_SRC = PREP.read_text(encoding="utf-8")
FRAME_DRIVER_SRC = FRAME_DRIVER.read_text(encoding="utf-8")
BOOT_SRC = (HUD / "fnc_hudTapeBoot.sqf").read_text(encoding="utf-8")
BOX_DRIVER_SRC = (HUD / "fnc_hudBoxDraw.sqf").read_text(encoding="utf-8")

# A control at or above these bounds, with a non-zero background alpha, is a
# full-view tint.  0.9 tolerates a one-pixel frame around a full-screen panel.
FULL_X = 0.05
FULL_Y = 0.05
FULL_W = 0.90
FULL_H = 0.90


def code_only(src: str) -> str:
    """Strip block and line comments so assertions test code, not prose."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", src)


def class_bodies(src: str) -> list[tuple[str, str]]:
    """Return (name, body) for every `class <name> { ... }` block."""
    code = code_only(src)
    bodies: list[tuple[str, str]] = []
    for match in re.finditer(r"class\s+([\w()]+)", code):
        brace = code.find("{", match.end())
        if brace == -1:
            continue
        depth = 0
        end = -1
        for i in range(brace, len(code)):
            char = code[i]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end != -1:
            bodies.append((match.group(1), code[brace + 1 : end]))
    return bodies


def background_alpha(body: str) -> float | None:
    match = re.search(r"colorBackground\[\]\s*=\s*\{([^}]*)\}", body)
    if not match:
        return None
    parts = [p.strip() for p in match.group(1).split(",")]
    try:
        return float(parts[3])
    except (IndexError, ValueError):
        return None


def geometry(body: str) -> dict[str, float]:
    props: dict[str, float] = {}
    for key in ("x", "y", "w", "h"):
        # Digits only: a quoted safeZoneX/safeZoneW is not a literal fraction.
        match = re.search(rf"(?<![\w.]){key}\s*=\s*([0-9.]+)\s*;", body)
        if match:
            props[key] = float(match.group(1))
    return props


def frame_ratio(half_angle_deg: float, nvg_field_deg: float) -> float:
    return run_sqf(FRAME_GEOMETRY, [half_angle_deg, nvg_field_deg], {})


def frame_visible(ratio: float, min_inset: float) -> bool:
    return bool(run_sqf(FRAME_VISIBLE, [ratio, min_inset], {}))


def min_inset() -> float:
    match = re.search(
        r"#define\s+FUSION_FRAME_MIN_INSET\s+([0-9.]+)", SCRIPT_COMPONENT_SRC
    )
    assert match, "FUSION_FRAME_MIN_INSET is not defined in script_component.hpp"
    return float(match.group(1))


class TestNoFullViewTint(unittest.TestCase):
    """A HUD control must not wash the sensor image with a background alpha."""

    def test_no_control_covers_the_full_safe_zone_with_alpha(self) -> None:
        offenders: list[str] = []
        for name, body in class_bodies(RSC_SRC):
            alpha = background_alpha(body)
            if alpha is None or alpha <= 0:
                continue
            props = geometry(body)
            if not all(k in props for k in ("x", "y", "w", "h")):
                continue
            if (
                props["x"] <= FULL_X
                and props["y"] <= FULL_Y
                and props["w"] >= FULL_W
                and props["h"] >= FULL_H
            ):
                offenders.append(f"{name} {props} alpha={alpha}")
        self.assertEqual(offenders, [], f"full-view background tint: {offenders}")

    def test_no_fusion_hud_control_washes_the_full_safe_zone(self) -> None:
        # A HUD control may carry a background (the box edges do), but none may
        # span the safe zone: that is the full-view wash the operator rejected.
        body = dict(class_bodies(RSC_SRC)).get("GVAR(fusionHud)")
        self.assertIsNotNone(body, "GVAR(fusionHud) display missing")
        assert body is not None
        for name, control in class_bodies(body):
            alpha = background_alpha(control)
            if alpha is None or alpha <= 0:
                continue
            props = geometry(control)
            if not all(k in props for k in ("x", "y", "w", "h")):
                continue
            self.assertFalse(
                props["x"] <= FULL_X
                and props["y"] <= FULL_Y
                and props["w"] >= FULL_W
                and props["h"] >= FULL_H,
                f"{name} washes the full safe zone: {props} alpha={alpha}",
            )

    def test_the_source_box_edges_are_restored(self) -> None:
        # The source's box is restored as the four EDGE controls at the source
        # idcs, not as a full panel fill.
        code = code_only(RSC_SRC)
        for idc in (910001, 910002, 910003, 910004):
            self.assertIn(f"idc = {idc}", code, f"the box edge {idc} is missing")
        for name in (
            "AEEFusionHudBoxTop",
            "AEEFusionHudBoxBottom",
            "AEEFusionHudBoxLeft",
            "AEEFusionHudBoxRight",
        ):
            self.assertIn(name, code)

    def test_the_box_is_the_source_colour_and_size(self) -> None:
        # config.cpp ecoti_tint colorBackground {0.55, 0.08, 0.05, 0.30} and the
        # source's fn_preInit.sqf boxSize 0.40.
        macro = re.search(
            r"#define\s+FUSION_BOX_COLOR\s+\[([0-9., ]+)\]", SCRIPT_COMPONENT_SRC
        )
        self.assertIsNotNone(macro, "FUSION_BOX_COLOR is not defined")
        assert macro is not None
        parts = [float(x) for x in macro.group(1).split(",")]
        self.assertEqual(parts, [0.55, 0.08, 0.05, 0.30])
        frac = re.search(
            r"#define\s+FUSION_HUD_BOX_FRACTION\s+([0-9.]+)", SCRIPT_COMPONENT_SRC
        )
        self.assertIsNotNone(frac, "FUSION_HUD_BOX_FRACTION is not defined")
        assert frac is not None
        self.assertEqual(float(frac.group(1)), 0.40)

    def test_the_box_driver_sets_all_four_edges(self) -> None:
        code = code_only(BOX_DRIVER_SRC)
        for idc in (910001, 910002, 910003, 910004):
            self.assertIn(f"displayCtrl {idc}", code)

    def test_the_boot_profile_has_no_glass_channel(self) -> None:
        self.assertIn("[_hudK, _infoK]", BOOT_SRC)
        self.assertNotIn("glassA", code_only(BOOT_SRC))
        self.assertNotIn("glassBoost", code_only(BOOT_SRC))


class TestNoFullViewFrame(unittest.TestCase):
    """The FOV frame must vanish when the thermal channel is not inset."""

    def test_envgb_ratio_sits_at_the_field_edge(self) -> None:
        # ENVG-B: 20-degree channel, declared 40-degree device field.
        self.assertAlmostEqual(frame_ratio(20, 40), 1.0, places=6)

    def test_the_frame_is_not_drawn_at_the_field_edge(self) -> None:
        ratio = frame_ratio(20, 40)
        self.assertGreaterEqual(ratio, min_inset())
        self.assertFalse(frame_visible(ratio, min_inset()))

    def test_a_derived_inset_is_drawn(self) -> None:
        # BNVD-FUSED: 17-degree derived channel half-angle.
        ratio = frame_ratio(17, 40)
        self.assertLess(ratio, min_inset())
        self.assertTrue(frame_visible(ratio, min_inset()))

    def test_a_published_inset_is_drawn(self) -> None:
        # ECOTI: published 15-degree circular channel.
        ratio = frame_ratio(15, 40)
        self.assertTrue(frame_visible(ratio, min_inset()))

    def test_an_empty_or_inverted_frame_is_not_drawn(self) -> None:
        self.assertFalse(frame_visible(0.0, min_inset()))
        self.assertFalse(frame_visible(1.0, min_inset()))
        self.assertFalse(frame_visible(0.98, min_inset()))

    def test_the_threshold_is_a_real_inset(self) -> None:
        value = min_inset()
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0)
        self.assertLessEqual(value, 0.97)

    def test_the_driver_consults_both_kernels_before_it_draws(self) -> None:
        code = code_only(FRAME_DRIVER_SRC)
        geometry_call = code.index("call FUNC(fusionFrameGeometry)")
        visible_call = code.index("call FUNC(fusionFrameVisible)")
        draw_call = code.index("ctrlSetPosition")
        teardown = code.index("cutText")
        # Ratio first, visibility next, tear-down on the false branch, draw last.
        self.assertLess(geometry_call, visible_call)
        self.assertLess(visible_call, draw_call)
        self.assertLess(teardown, draw_call)

    def test_the_visibility_kernel_is_prepped(self) -> None:
        for name in ("fusionFrameGeometry", "fusionFrameVisible", "updateFusionFrame"):
            self.assertIn(f"PREPS(fusion,{name});", PREP_SRC)


if __name__ == "__main__":
    unittest.main()
