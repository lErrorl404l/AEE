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
    PAINT = (
        REPO / "addons/thermal/functions/display/fnc_applySelectionThermal.sqf"
    ).read_text(encoding="utf-8")
    RESOLVER = (
        REPO / "addons/thermal/functions/sensor/fnc_getThermalDeviceProperties.sqf"
    ).read_text(encoding="utf-8")

    def test_netd_from_device(self):
        # The selection caller resolves the device NETD (0.025 cooled /
        # 0.05 uncooled) for the resolution threshold; no range-squared noise
        # floor double-counts the path transmission.
        self.assertIn("getThermalDeviceProperties", self.PAINT)
        self.assertNotIn("calculateThermalNoise", self.PAINT)
        self.assertFalse(
            (
                REPO / "addons/thermal/functions/solver/fnc_calculateThermalNoise.sqf"
            ).exists()
        )

    def test_the_device_slot_is_read_from_a_unit_not_a_vehicle(self):
        # Same root cause as the optics layer (issue #261): primaryWeaponItems
        # takes a soldier, and the caller passes `vehicle _viewer`.  The old
        # read always came back empty, so every mounted thermal sight fell
        # back to the default device row.
        self.assertIn("primaryWeaponItems _unit", self.RESOLVER)
        self.assertNotIn("primaryWeaponItems _weapon", self.RESOLVER)

    def test_the_caller_reads_the_viewers_own_weapon_slot(self):
        # The caller resolves its per-optic cache key from the same slot, so
        # it must pass the viewer and not the viewer's vehicle.
        self.assertIn("primaryWeaponItems _viewer", self.PAINT)
        self.assertNotIn("primaryWeaponItems _wp", self.PAINT)


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

    def test_the_optic_slot_is_read_from_a_unit_not_a_vehicle(self):
        # primaryWeaponItems takes a soldier, and the caller passes
        # `vehicle _viewer`.  The old read always came back empty, so every
        # mounted optic fell back to the 4x32 default (issue #261).
        self.assertIn("primaryWeaponItems _unit", self.FNC)
        self.assertNotIn("primaryWeaponItems _weapon", self.FNC)
        self.assertIn("hmd _unit", self.FNC)


if __name__ == "__main__":
    unittest.main()
