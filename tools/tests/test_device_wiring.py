#!/usr/bin/env python3
"""Device consumer wiring tests (issue #215).

Locks the three device classifiers into their consumers - the NVG tube
model, the thermal contrast noise floor, and the optic knowledge layer.
A consumer that stops reading the device library fails this gate.

Run: python3 -m unittest tools/tests/test_device_wiring.py
"""

import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]


class TestNvgWiring(unittest.TestCase):
    FNC = (REPO / "addons/nightvision/functions/fnc_applyNVGTubeModel.sqf").read_text(
        encoding="utf-8"
    )

    def test_device_classifier_is_authority(self):
        # The classifier sets tier/sensitivity/tubeCount; the model must
        # not re-derive them from a stale classname ladder.
        self.assertIn("call FUNC(getNvgDeviceProperties)", self.FNC)
        self.assertIn("private _tier = _dev select 0", self.FNC)
        self.assertIn("private _sensitivity = _dev select 1", self.FNC)
        self.assertIn("private _tubeCount = _dev select 4", self.FNC)

    def test_resolution_scales_mtf(self):
        # The device's lp/mm resolution scales the MTF (64 lp/mm anchor).
        self.assertIn("private _resLpmm = _dev select 2", self.FNC)
        self.assertIn("_resLpmm > 0", self.FNC)

    def test_per_tier_constants_key_off_tier(self):
        # The per-tier constants follow the classifier's generation.
        self.assertIn("switch (_tier) do", self.FNC)
        self.assertIn('case "PVS31"', self.FNC)
        self.assertIn('case "GEN3"', self.FNC)
        self.assertIn('case "GEN2"', self.FNC)


class TestThermalWiring(unittest.TestCase):
    FNC = (
        REPO / "addons/thermal/functions/sensor/fnc_calculateThermalContrast.sqf"
    ).read_text(encoding="utf-8")

    def test_netd_from_device(self):
        # The noise floor reads the device NETD (0.025 cooled / 0.05
        # uncooled).
        self.assertIn("getThermalDeviceProperties", self.FNC)
        self.assertIn("private _netd = _dev select 0", self.FNC)

    def test_resolution_scales_noise(self):
        # A low-res detector adds spatial noise (640x480 reference).
        self.assertIn("private _resX = _dev select 1", self.FNC)
        self.assertIn("640 / (_resX max 1)", self.FNC)


class TestOpticKnowledgeLayer(unittest.TestCase):
    FNC = (
        REPO / "addons/optics/functions/sensor/fnc_getOpticProperties.sqf"
    ).read_text(encoding="utf-8")

    def test_classifier_researched(self):
        # The optic classifier holds the researched sight physics.
        for kw in (
            "acog",
            "rco",
            "specterdr",
            "pso",
            "atacr",
            "compm",
            "eotech",
            "susat",
        ):
            self.assertIn(f'"{kw}"', self.FNC, f"optic keyword {kw} missing")


if __name__ == "__main__":
    unittest.main()
