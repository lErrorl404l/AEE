#!/usr/bin/env python3
"""Engine HDR config contract (aee-workshop-copy T1/T2).

The environmental addon completes the engine HDRNewPars block and sets
starEmissivity on DefaultLighting, the class every world's Lighting inherits.
These tests pin the exact values in addons/environmental/config.cpp.  The live
oracle is the P84 Docker probe, which reads the same keys from the loaded
config.  No mod content is copied: every value is a re-derived numeric
constant.

Run: python3 -m unittest tools.tests.test_engine_hdr_config -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CONFIG = Path(__file__).parents[2] / "addons" / "environmental" / "config.cpp"
SRC = CONFIG.read_text(encoding="utf-8")


def _class_body(src: str, name: str) -> str:
    """Return the body of the first ``class <name> { ... }`` block."""
    match = re.search(rf"class\s+{re.escape(name)}\b[^{{]*\{{", src)
    if not match:
        return ""
    depth = 0
    start = match.end() - 1
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start + 1 : i]
    return ""


def _number(body: str, key: str) -> float | None:
    match = re.search(rf"\b{re.escape(key)}\s*=\s*([0-9.eE+-]+)\s*;", body)
    return float(match.group(1)) if match else None


def _array(body: str, key: str) -> list:
    """Return a ``key[] = {...}`` array as scalars and float tuples."""
    match = re.search(rf"\b{re.escape(key)}\[\]\s*=\s*\{{", body)
    if not match:
        return []
    start = match.end() - 1
    depth = 0
    inner = ""
    for i in range(start, len(body)):
        if body[i] == "{":
            depth += 1
        elif body[i] == "}":
            depth -= 1
            if depth == 0:
                inner = body[start + 1 : i]
                break
    if not inner:
        return []
    elements = []
    token = ""
    depth = 0
    for ch in inner:
        if ch == "{":
            depth += 1
            token += ch
        elif ch == "}":
            depth -= 1
            token += ch
        elif ch == "," and depth == 0:
            elements.append(token.strip())
            token = ""
        else:
            token += ch
    if token.strip():
        elements.append(token.strip())
    parsed: list = []
    for element in elements:
        if element.startswith("{"):
            parsed.append(tuple(float(v) for v in element[1:-1].split(",")))
        else:
            parsed.append(float(element))
    return parsed


BRIGHT_ALMOST_DEEP = [
    -15.0,
    (0.0049, 0.0098, 0.0098),
    (0.0, 0.002, 0.003),
    (0.0, 0.0, 0.0),
    (0.0, 0.0, 0.0),
    (0.0, 0.002, 0.003),
    (0.0, 0.002, 0.003),
    0.0,
]
BRIGHT_ALMOST_FULL = [
    -5.0,
    (0.182, 0.213, 0.25),
    (0.05, 0.111, 0.221),
    (0.039, 0.034, 0.004),
    (0.04, 0.049, 0.072),
    (0.082, 0.128, 0.185),
    (0.283, 0.35, 0.431),
    0.0,
]
RAINY_FULL = [
    -5.0,
    (0.023, 0.023, 0.023),
    (0.02, 0.02, 0.02),
    (0.023, 0.023, 0.023),
    (0.02, 0.02, 0.02),
    (0.0098, 0.0098, 0.02),
    (0.08, 0.059, 0.059),
    0.0,
]


class TestEngineHdrKeys(unittest.TestCase):
    def setUp(self) -> None:
        self.hdr = _class_body(SRC, "HDRNewPars")

    def test_hdr_block_exists(self) -> None:
        self.assertTrue(self.hdr, "HDRNewPars block missing")

    def test_bloom_values(self) -> None:
        expected = {
            "bloomScale": 0.09,
            "bloomExponent": 0.75,
            "bloomLuminanceOffset": 0.4,
            "bloomLuminanceScale": 0.15,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(_number(self.hdr, key), value, places=5, msg=key)

    def test_tonemap_values(self) -> None:
        expected = {
            "tonemapMethod": 1.0,
            "tonemapShoulderStrength": 0.22,
            "tonemapLinearStrength": 0.12,
            "tonemapToeStrength": 0.2,
            "tonemapLinearWhite": 11.2,
            "tonemapExposureBias": 1.0,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(_number(self.hdr, key), value, places=5, msg=key)

    def test_eye_adaptation_and_night_shift_values(self) -> None:
        expected = {
            "eyeAdaptFactorLight": 3.3,
            "eyeAdaptFactorDark": 0.75,
            "nightShiftMaxEffect": 0.6,
            "nightShiftLuminanceScale": 600.0,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(_number(self.hdr, key), value, places=5, msg=key)

    def test_existing_nvg_keys_survive(self) -> None:
        expected = {
            "nvgApertureMin": 7.0,
            "nvgApertureStandard": 7.0,
            "nvgApertureMax": 7.0,
            "nvgStandardAvgLum": 3.0,
            "nvgLightGain": 80.0,
            "nvgTransition": 1.0,
            "nvgTransitionCoefOn": 40.0,
            "nvgTransitionCoefOff": 0.01,
        }
        for key, value in expected.items():
            self.assertAlmostEqual(_number(self.hdr, key), value, places=5, msg=key)

    def test_dof_pars_survive(self) -> None:
        dof = _class_body(SRC, "DOFPars")
        self.assertAlmostEqual(_number(dof, "focusDistance"), 12.0, places=5)
        self.assertAlmostEqual(_number(dof, "blur"), 0.6, places=5)
        self.assertAlmostEqual(_number(dof, "farOnly"), 1.0, places=5)

    def test_star_emissivity_is_40_in_the_inherited_lighting_class(self) -> None:
        lighting = _class_body(SRC, "DefaultLighting")
        self.assertAlmostEqual(
            _number(lighting, "starEmissivity"),
            40.0,
            places=5,
            msg="starEmissivity must sit on DefaultLighting at 40",
        )

    def test_star_emissivity_reaches_each_world_lighting(self) -> None:
        # The engine reads starEmissivity from the world's own Lighting class.
        # The base config only forward-declares DefaultLighting and every
        # official world sets its own, so AEE overrides each world's Lighting
        # with an explicit base.
        worlds = ("CAWorld", "Stratis", "Altis", "VR", "Malden", "Enoch", "Tanoa")
        for world in worlds:
            lighting = _class_body(_class_body(SRC, world), "Lighting")
            self.assertAlmostEqual(
                _number(lighting, "starEmissivity"),
                40.0,
                places=5,
                msg=f"{world}.Lighting.starEmissivity must be 40",
            )

    def test_deep_night_and_full_night_arrays(self) -> None:
        bright = _class_body(SRC, "DayLightingBrightAlmost")
        rainy = _class_body(SRC, "DayLightingRainy")
        self.assertTrue(bright, "DayLightingBrightAlmost block missing")
        self.assertTrue(rainy, "DayLightingRainy block missing")
        bright_deep = _array(bright, "deepNight")
        bright_full = _array(bright, "fullNight")
        rainy_deep = _array(rainy, "deepNight")
        rainy_full = _array(rainy, "fullNight")
        self.assertEqual(len(bright_deep), 8, "deepNight must carry 8 elements")
        self.assertEqual(len(bright_full), 8, "fullNight must carry 8 elements")
        self.assertEqual(bright_deep[0], -15.0)
        self.assertEqual(bright_full[0], -5.0)
        self.assertEqual(bright_deep, BRIGHT_ALMOST_DEEP)
        self.assertEqual(bright_full, BRIGHT_ALMOST_FULL)
        self.assertEqual(rainy_deep, BRIGHT_ALMOST_DEEP)
        self.assertEqual(rainy_full, RAINY_FULL)


if __name__ == "__main__":
    unittest.main()
