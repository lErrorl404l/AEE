#!/usr/bin/env python3
"""Contract test: AEE's public extension surface matches the documented one.

ADR-027 makes the `aee_*` surface a stable contract. This test scans the
repository for the addon PBOs, the callable functions, the `aee_core_*` state
variables and the AEE-authored config classes, and asserts that
`docs/wiki/research/extension-contract.md` documents exactly that set. A mod
that consumes AEE gets a surface that cannot drift from the doc.

Run: python3 -m unittest tools.tests.test_extension_contract
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import gen_extension_contract as gec  # noqa: E402


class TestExtensionContract(unittest.TestCase):
    def test_anchors_exist(self):
        for name, source in {**gec.ANCHOR_CLASSES, **gec.ANCHOR_ENGINE_CLASSES}.items():
            self.assertTrue(
                gec.class_exists(source, name),
                f"anchor class {name} is not declared in {source}",
            )

    def test_audit_clean(self):
        self.assertEqual(gec.audit(), [])

    def test_doc_block_is_current(self):
        doc = gec.DOC.read_text(encoding="utf-8")
        present = gec.current_block(doc)
        self.assertIsNotNone(
            present, "extension-contract.md is missing the generated block"
        )
        self.assertEqual(
            present,
            gec.build_block(),
            "extension-contract.md is stale: run tools/gen_extension_contract.py",
        )

    def test_documented_functions_equal_the_code(self):
        functions = gec.public_functions()
        doc = gec.DOC.read_text(encoding="utf-8")
        for name in functions:
            self.assertIn(f"`{name}`", doc, f"{name} is not documented")
        # No phantom documentation: every documented aee_*_fnc_ name is real.
        import re

        documented = set(re.findall(r"aee_[A-Za-z0-9_]+_fnc_[A-Za-z0-9_]+", doc))
        self.assertEqual(documented - set(functions), set())

    def test_documented_core_state_equal_the_code(self):
        state = gec.public_core_state()
        doc = gec.DOC.read_text(encoding="utf-8")
        self.assertTrue(state, "core state scan is empty")
        for name in state:
            self.assertIn(f"`{name}`", doc, f"{name} is not documented")

    def test_documented_addons_equal_the_code(self):
        doc = gec.DOC.read_text(encoding="utf-8")
        for component in gec.addon_components():
            self.assertIn(f"`aee_{component}`", doc)

    def test_resolver_registry_template_present(self):
        # The physiology resolver registries are the template the contract
        # generalises. Both registry variable names must appear in core code
        # (the read side) and in compat_ace3 (the write side).
        core = (
            ROOT
            / "addons"
            / "physiology"
            / "functions"
            / "clothing"
            / "fnc_getInventoryLoad.sqf"
        )
        core_mass = (
            ROOT
            / "addons"
            / "physiology"
            / "functions"
            / "clothing"
            / "fnc_getItemMass.sqf"
        )
        compat = ROOT / "addons" / "compat_ace3" / "XEH_preInit.sqf"
        self.assertIn("massResolvers", core.read_text(encoding="utf-8"))
        self.assertIn("categoryResolvers", core_mass.read_text(encoding="utf-8"))
        compat_text = compat.read_text(encoding="utf-8")
        self.assertIn("aee_physiology_massResolvers", compat_text)
        self.assertIn("aee_physiology_categoryResolvers", compat_text)

    def test_class_exists_rejects_a_missing_class(self):
        # Negative control: the class check is not vacuously true.
        self.assertFalse(
            gec.class_exists("addons/optics/config.cpp", "AEE_NotARealClass")
        )


if __name__ == "__main__":
    unittest.main()
