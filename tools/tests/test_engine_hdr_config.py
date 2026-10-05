#!/usr/bin/env python3
"""Engine HDR config contract (aee-workshop-copy T1/T2, addendum 2).

The anchor must live in the WORLD CLASS CHAIN.  A direct ``CfgWorlds`` child is
an unreferenced sibling and inert; the engine reads ``HDRNewPars``/``DOFPars``/
``DayLighting`` through ``CfgWorlds >> DefaultWorld >> CAWorld >> <World>:CAWorld``.
These tests parse ``config.cpp`` and assert the chain structure, the shared
values, and that every world carries the SAME block (the engine's structural
requirement, not per-map tuning).  The live oracle is the P84 Docker probe,
which reads the RESOLVED world config.

MUTATION PROOF (executed by hand at commit time): change one per-world
``bloomScale`` -> ``test_per_world_blocks_carry_the_shared_values`` fails;
restore -> OK.

Run: python3 -m unittest tools.tests.test_engine_hdr_config -v
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

CONFIG = Path(__file__).parents[2] / "addons" / "environmental" / "config.cpp"
SRC = CONFIG.read_text(encoding="utf-8")

# The worlds whose config redeclares HDRNewPars (vanilla class chain).
WORLDS = ("Stratis", "Altis", "Malden", "Tanoa", "Enoch")


def _code_only(src: str) -> str:
    """Strip block and line comments so assertions test code, not prose."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", src)


def _class_body(src: str, name: str) -> str:
    """Return the body of the first ``class <name>[: base] { ... }`` block."""
    match = re.search(rf"\bclass\s+{re.escape(name)}\b[^{{]*\{{", src)
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


def _normalise(body: str) -> str:
    return re.sub(r"\s+", " ", _code_only(body)).strip()


CFG_WORLDS = _class_body(SRC, "CfgWorlds")
CA_WORLD = _class_body(CFG_WORLDS, "CAWorld")

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


class TestAnchorIsInTheWorldChain(unittest.TestCase):
    def test_anchor_is_in_the_world_chain(self) -> None:
        cfg = _code_only(CFG_WORLDS)
        self.assertIn("class DefaultWorld;", cfg, "DefaultWorld must be declared")
        self.assertRegex(
            cfg,
            r"class\s+CAWorld\s*:\s*DefaultWorld",
            "CAWorld must chain from DefaultWorld",
        )
        for world in WORLDS:
            self.assertRegex(
                cfg,
                rf"class\s+{world}\s*:\s*CAWorld",
                f"{world} must chain from CAWorld",
            )
        # No inert direct child: every anchor class must use the explicit base.
        for name in (
            "HDRNewPars",
            "DOFPars",
            "DayLightingBrightAlmost",
            "DayLightingRainy",
        ):
            self.assertIsNone(
                re.search(rf"\bclass\s+{name}\s*\{{", cfg),
                f"class {name} must not be a direct CfgWorlds child",
            )

    def test_required_addons_anchor_the_load_order(self) -> None:
        # A3_Data_F_Decade_Loadorder is the base-game load-order anchor.  The
        # per-map names were dropped: the engine warns on A3_Map_Tanoa when the
        # Apex map is not loaded, and a warning fails the run gate.
        self.assertIn('"A3_Data_F_Decade_Loadorder"', SRC)

    def test_ca_world_hdr_inherits(self) -> None:
        self.assertRegex(CA_WORLD, r"class\s+HDRNewPars\s*:\s*HDRNewPars\s*\{")
        self.assertRegex(CA_WORLD, r"class\s+DOFPars\s*:\s*DOFPars\s*\{")

    def test_per_world_blocks_carry_the_shared_values(self) -> None:
        ca_hdr = _normalise(_class_body(CA_WORLD, "HDRNewPars"))
        self.assertTrue(ca_hdr, "CAWorld HDRNewPars missing")
        ca_bright = _normalise(_class_body(CA_WORLD, "DayLightingBrightAlmost"))
        ca_rainy = _normalise(_class_body(CA_WORLD, "DayLightingRainy"))
        for world in WORLDS:
            with self.subTest(world=world):
                body = _class_body(CFG_WORLDS, world)
                self.assertTrue(body, f"{world} block missing")
                self.assertEqual(
                    _normalise(_class_body(body, "HDRNewPars")),
                    ca_hdr,
                    f"{world} HDRNewPars differs from CAWorld",
                )
                self.assertEqual(
                    _normalise(_class_body(body, "DayLightingBrightAlmost")),
                    ca_bright,
                    f"{world} DayLightingBrightAlmost differs from CAWorld",
                )
                self.assertEqual(
                    _normalise(_class_body(body, "DayLightingRainy")),
                    ca_rainy,
                    f"{world} DayLightingRainy differs from CAWorld",
                )

    def test_every_world_sets_star_emissivity_40(self) -> None:
        ca_light = _class_body(CA_WORLD, "Lighting")
        self.assertAlmostEqual(_number(ca_light, "starEmissivity"), 40.0, places=5)
        for world in WORLDS:
            light = _class_body(_class_body(CFG_WORLDS, world), "Lighting")
            self.assertAlmostEqual(
                _number(light, "starEmissivity"),
                40.0,
                places=5,
                msg=f"{world} Lighting.starEmissivity must be 40",
            )

    def test_default_lighting_reopen_is_40(self) -> None:
        light = _class_body(CFG_WORLDS, "DefaultLighting")
        self.assertAlmostEqual(_number(light, "starEmissivity"), 40.0, places=5)


class TestEngineHdrKeys(unittest.TestCase):
    def setUp(self) -> None:
        self.hdr = _class_body(CA_WORLD, "HDRNewPars")

    def test_hdr_block_exists(self) -> None:
        self.assertTrue(self.hdr, "CAWorld HDRNewPars block missing")

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
        dof = _class_body(CA_WORLD, "DOFPars")
        self.assertAlmostEqual(_number(dof, "focusDistance"), 12.0, places=5)
        self.assertAlmostEqual(_number(dof, "blur"), 0.6, places=5)
        self.assertAlmostEqual(_number(dof, "farOnly"), 1.0, places=5)

    def test_deep_night_and_full_night_arrays(self) -> None:
        bright = _class_body(CA_WORLD, "DayLightingBrightAlmost")
        rainy = _class_body(CA_WORLD, "DayLightingRainy")
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
