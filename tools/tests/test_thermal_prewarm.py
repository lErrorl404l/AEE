#!/usr/bin/env python3
"""Thermal post-process pre-warm contract.

The thermal-vision first entry used to create the eight ppEffects on the
entry tick and commit them from a DISABLED state, so the engine built every
enabled chain on the NEXT tick: a measured 907 ms frame hitch (operator RPT
2026-10-08_17-51-36, the worst tick: applyThermalVision 907 ms).  The create
table now lives in fnc_createThermalPPEffects and is built once, off the
entry path, by fnc_warmThermalPPEffects at postInit.

These are source contracts.  They fail if a create returns to the per-entry
driver, if the create table leaves its own function, if the warm is not
wired into the thermal XEH_postInit, or if the exit path destroys a handle
(destroying forces a rebuild on the next entry, which was the hitch).

Run: python3 -m unittest tools.tests.test_thermal_prewarm -v
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_THERMAL = REPO / "addons" / "thermal"
_DISPLAY = REPO / "addons" / "thermal_display" / "functions" / "display"
_DRIVER = _DISPLAY / "fnc_applyThermalVision.sqf"
_CREATE = _DISPLAY / "fnc_createThermalPPEffects.sqf"
_WARM = _DISPLAY / "fnc_warmThermalPPEffects.sqf"
_POSTINIT = REPO / "addons" / "thermal_display" / "XEH_postInit.sqf"
_PREP = REPO / "addons" / "thermal_display" / "XEH_PREP.hpp"

_EFFECTS = (
    "ChromAberration",
    "RadialBlur",
    "DynamicBlur",
    "FilmGrain",
    "ColorCorrections",
    "ColorInversion",
    "WetDistortion",
    "Resolution",
)


def _code(path):
    """The SQF source with its comments stripped."""
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


class TestThermalPrewarmContract(unittest.TestCase):
    """A PP effect is created off the per-entry path, never on it."""

    @classmethod
    def setUpClass(cls):
        cls.driver = _code(_DRIVER)
        cls.create = _code(_CREATE)
        cls.warm = _code(_WARM)
        cls.postinit = _code(_POSTINIT)
        cls.prep = _PREP.read_text(encoding="utf-8")

    def test_driver_creates_no_effect(self):
        # Given the entry path runs every thermal tick, when it created an
        # effect the engine rebuilt the chain on the next commit.  Then the
        # driver must not create.
        self.assertNotIn("ppEffectCreate", self.driver)

    def test_driver_does_not_destroy_a_handle(self):
        # Destroying on exit forces a recreate, and a fresh engine build, on
        # the next entry.  The exit path disables the handles instead.
        self.assertNotIn("ppEffectDestroy", self.driver)

    def test_create_function_owns_the_create_table(self):
        with self.subTest(function="create"):
            self.assertIn("ppEffectCreate", self.create)
        for name in _EFFECTS:
            with self.subTest(effect=name):
                self.assertIn(f'"{name}"', self.create)

    def test_create_is_idempotent(self):
        # It creates only when a handle is missing.
        self.assertIn("getVariable", self.create)
        self.assertRegex(self.create, r"<\s*0")
        self.assertIn("ppEffectCreate", self.create)

    def test_warm_calls_create(self):
        self.assertIn(
            "FUNC(createThermalPPEffects)",
            _WARM.read_text(encoding="utf-8"),
        )

    def test_warm_enables_before_the_commit(self):
        # The engine builds an enabled chain on a commit.  The warm must
        # enable before the commit, or the build is deferred and the fix
        # does nothing.
        self.assertIn("ppEffectEnable true", self.warm)
        commit = self.warm.index("ppEffectCommit 0")
        self.assertLess(self.warm.index("ppEffectEnable true"), commit)
        self.assertIn("CBA_fnc_waitAndExecute", self.warm)

    def test_warm_is_called_from_the_thermal_postinit(self):
        self.assertIn("FUNC(warmThermalPPEffects)", self.postinit)

    def test_driver_clears_the_change_gate_when_it_disables(self):
        # The handles survive an exit (they are disabled, not destroyed), so
        # a stale change-gate entry would skip the re-enable on re-entry.
        # The exit and the ppOn-off paths must clear the cache.
        self.assertIn("setVariable [QGVAR(ppLastParams), createHashMap];", self.driver)

    def test_both_functions_are_registered(self):
        self.assertIn("PREPS(display,createThermalPPEffects);", self.prep)
        self.assertIn("PREPS(display,warmThermalPPEffects);", self.prep)


if __name__ == "__main__":
    unittest.main()
