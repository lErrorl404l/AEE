#!/usr/bin/env python3
"""Per-optic thermal config generation (aee-thermal-realism T11).

Locks the generated CfgWeapons block to the device corpus and the authored
class bindings. The generated header is the oracle: a stale or missing block
fails --check, and a bound optic with no held corpus figure emits no
declaration.

Run: python3 -m unittest tools.tests.test_thermal_optics_config -v
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation import gen_thermal_optics as gen  # noqa: E402

GENERATED = REPO / "addons" / "thermal" / "generated" / "ThermalOptics.hpp"


class TestGeneratedHeader(unittest.TestCase):
    def test_check_is_green_on_disk(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(REPO / "tools/validation/gen_thermal_optics.py"),
                "--check",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_header_file_exists(self) -> None:
        self.assertTrue(GENERATED.is_file(), "the generated header is missing")

    def test_bound_vanilla_optics_are_declared(self) -> None:
        text = gen.render()
        for class_name in ("optic_Nightstalker", "optic_tws", "optic_tws_mg"):
            self.assertIn(f"class {class_name}", text)

    def test_verified_path_is_recorded(self) -> None:
        text = gen.render()
        self.assertIn("ItemInfo >> OpticsModes", text)
        self.assertIn("CfgWeapons", text)

    def test_thermal_mode_is_the_declared_pair(self) -> None:
        text = gen.render()
        self.assertIn("thermalMode[] = {0, 1};", text)

    def test_noise_is_derived_from_netd(self) -> None:
        text = gen.render()
        # pas13_base holds netd_c 0.05; envg_thermal holds netd_c 0.04.
        self.assertIn("thermalNoise[] = {0.05};", text)
        self.assertIn("thermalNoise[] = {0.04};", text)

    def test_resolution_is_derived_from_the_pixel_pair(self) -> None:
        text = gen.render()
        self.assertIn("thermalResolution[] = {640, 480};", text)

    def test_declared_constant_is_marked(self) -> None:
        text = gen.render()
        self.assertIn("DECLARED", text)


class TestFailClosed(unittest.TestCase):
    def test_binding_without_a_corpus_figure_emits_nothing(self) -> None:
        entries = gen.load_thermal(gen.DEFAULT_DATA)
        # The ECOTI corpus row holds no netd_c, so it fails closed.
        binding = gen.Binding(
            game_class="test_ecoti",
            catalogue_id="ecoti",
            optic_mode="X",
            identity_source="fixture",
            identity_evidence="fixture",
            grade="authored",
        )
        self.assertIsNone(gen.build_declaration(binding, entries))

    def test_binding_without_a_corpus_row_emits_nothing(self) -> None:
        entries = gen.load_thermal(gen.DEFAULT_DATA)
        binding = gen.Binding(
            game_class="test_missing",
            catalogue_id="no_such_device",
            optic_mode="X",
            identity_source="fixture",
            identity_evidence="fixture",
            grade="authored",
        )
        self.assertIsNone(gen.build_declaration(binding, entries))

    def test_held_row_emits_a_declaration(self) -> None:
        entries = gen.load_thermal(gen.DEFAULT_DATA)
        binding = gen.Binding(
            game_class="test_pas13",
            catalogue_id="pas13_base",
            optic_mode="TWS",
            identity_source="fixture",
            identity_evidence="fixture",
            grade="authored",
        )
        block = gen.build_declaration(binding, entries)
        self.assertIsNotNone(block)
        assert block is not None
        self.assertIn("class test_pas13", block)
        self.assertIn("class TWS", block)


class TestBindings(unittest.TestCase):
    def test_bindings_are_unique_and_resolve(self) -> None:
        entries = gen.load_thermal(gen.DEFAULT_DATA)
        bindings, errors = gen.load_bindings(gen.DEFAULT_BINDINGS)
        self.assertEqual(errors, [])
        classes = [b.game_class for b in bindings]
        self.assertEqual(len(classes), len(set(classes)))
        for binding in bindings:
            self.assertIn(binding.catalogue_id, entries)
            self.assertNotEqual(gen.build_declaration(binding, entries), None)


if __name__ == "__main__":
    unittest.main()
