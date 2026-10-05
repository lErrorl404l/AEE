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


if __name__ == "__main__":
    unittest.main()
