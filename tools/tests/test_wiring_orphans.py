#!/usr/bin/env python3
"""Orphan wiring tests (issue #170, #215).

Locks three functions that had no production caller into the consumers that
now use them, so a consumer that stops calling its function fails this gate:

- optics/fnc_getOpticProperties feeds the thermal spatial kernel's day-optic
  magnification (thermal/fnc_applySelectionThermal.sqf).
- armour/fnc_deriveProtection feeds the penetration gate
  (armour/fnc_penetrationGate.sqf).
- nightvision/fnc_getDeviceData feeds the optic corpus route
  (optics/fnc_getOpticProperties.sqf).

Run: python3 -m unittest tools.tests.test_wiring_orphans -v
"""

from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]


def _read(*parts: str) -> str:
    return REPO.joinpath(*parts).read_text(encoding="utf-8")


class TestOpticPropertiesWiring(unittest.TestCase):
    PAINT = _read(
        "addons", "thermal", "functions", "display", "fnc_applySelectionThermal.sqf"
    )

    def test_the_paint_reads_the_optic(self):
        self.assertIn("call EFUNC(optics,getOpticProperties)", self.PAINT)

    def test_the_optic_magnification_feeds_the_spatial_kernel(self):
        self.assertIn(
            "[_angle, _resX, _mag, 0, _netdC, _contrast, _tBgC] "
            "call FUNC(resolveThermalTarget)",
            self.PAINT,
        )


class TestDeriveProtectionWiring(unittest.TestCase):
    GATE = _read("addons", "armour", "functions", "fnc_penetrationGate.sqf")
    KERNEL = _read("addons", "armour", "functions", "fnc_calculatePenetration.sqf")

    def test_the_gate_reads_the_derivation(self):
        # The derivation lives in the shared kernel; the gate reads it.
        self.assertIn("([_unit] call FUNC(deriveProtection)) select 1", self.KERNEL)
        self.assertIn("calculatePenetration", self.GATE)

    def test_the_derivation_prefers_the_table(self):
        deriv = _read("addons", "armour", "functions", "fnc_deriveProtection.sqf")
        self.assertIn("call FUNC(getVehicleArmour)", deriv)


class TestDeviceDataWiring(unittest.TestCase):
    OPTIC = _read(
        "addons", "optics", "functions", "sensor", "fnc_getOpticProperties.sqf"
    )

    def test_the_optic_classifier_reads_the_corpus(self):
        self.assertIn("call EFUNC(nightvision,getDeviceData)", self.OPTIC)
        self.assertIn('[_optic, "optic"]', self.OPTIC)

    def test_a_corpus_figure_overrides_the_fallback(self):
        self.assertIn("_fallback set [0, _mag];", self.OPTIC)

    def test_the_lookup_consumes_the_matcher(self):
        data = _read("addons", "nightvision", "functions", "fnc_getDeviceData.sqf")
        self.assertIn("call FUNC(getDeviceMatch)", data)


if __name__ == "__main__":
    unittest.main()
