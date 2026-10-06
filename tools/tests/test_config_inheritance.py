#!/usr/bin/env python3
"""Config inheritance contract: an override must keep the vanilla base.

A config class that re-opens a vanilla class must name the vanilla parent.  A
re-open without a base clears the parent, so the engine logs
"Updating base class '<parent>'->''" and the class loses every field it
inherited.  The engine core and the vanilla weapon config are the source of
the parent names:

  dta/bin.pbo config.bin (engine core):
    CfgWorlds/DefaultLighting          (no base)
    CfgWorlds/DefaultWorld/HDRNewPars  (no base)
    CfgWorlds/DefaultWorld/DOFPars     (no base)
    CfgWorlds/DefaultWorld/DayLightingBrightAlmost (no base)
  weapons_f.pbo acc/config.bin:
    CfgWeapons/optic_Nightstalker: ItemCore
    CfgWeapons/optic_tws: ItemCore
    CfgWeapons/optic_tws_mg: ItemCore
    each class ItemInfo: InventoryOpticsItem_Base_F

A class whose vanilla base is empty must be re-opened without a base: naming
one rebases it and the engine logs "Updating base class ''->'<name>'".

MUTATION PROOF (executed by hand at commit time): drop ": ItemCore" from the
generator emitter -> test_generated_optics_name_their_parent fails; restore ->
OK.  Add a file-root "class HDRNewPars;" -> test_no_file_root_declaration
fails; restore -> OK.

Run: python3 -m unittest tools.tests.test_config_inheritance -v
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation import gen_thermal_optics as gen  # noqa: E402

ENV_CONFIG = REPO / "addons" / "environmental" / "config.cpp"
GENERATED = REPO / "addons" / "thermal" / "generated" / "ThermalOptics.hpp"

ENV_SRC = ENV_CONFIG.read_text(encoding="utf-8")
GEN_SRC = GENERATED.read_text(encoding="utf-8")

# The vanilla base of each class AEE re-opens.  A re-open must carry it.
OPTIC_BASES = {
    "optic_Nightstalker": "ItemCore",
    "optic_tws": "ItemCore",
    "optic_tws_mg": "ItemCore",
}
ITEM_INFO_BASE = "InventoryOpticsItem_Base_F"
ENV_BASES = {
    "Lighting": "DefaultLighting",
    "DayLightingBrightAlmost": "DayLightingBrightAlmost",
    "DayLightingRainy": "DayLightingRainy",
    "DOFPars": "DOFPars",
}

# Classes whose vanilla base is EMPTY.  They must be re-opened without a base.
EMPTY_BASE = ("HDRNewPars", "DefaultLighting")

# The five classes the original defect declared at the file root.
ROOT_DECL_CLASSES = (
    "HDRNewPars",
    "DOFPars",
    "DayLightingBrightAlmost",
    "DayLightingRainy",
    "DefaultLighting",
)

_CLASS_RE = re.compile(r"\bclass\s+(\w+)\s*(?::\s*(\w+))?\s*\{")


def _code_only(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", src)


def _definitions(src: str) -> list[tuple[str, str | None]]:
    """Return (name, base) for every class definition in ``src``."""
    return [(m.group(1), m.group(2)) for m in _CLASS_RE.finditer(_code_only(src))]


class TestOverridesKeepTheVanillaBase(unittest.TestCase):
    def test_generated_optics_name_their_parent(self) -> None:
        seen = {name: base for name, base in _definitions(GEN_SRC)}
        for name, base in OPTIC_BASES.items():
            with self.subTest(optic=name):
                self.assertEqual(
                    seen.get(name),
                    base,
                    f"class {name} must re-open as `class {name}: {base}`",
                )
        item_infos = [
            base for name, base in _definitions(GEN_SRC) if name == "ItemInfo"
        ]
        self.assertTrue(item_infos, "the generated block declares no ItemInfo")
        for base in item_infos:
            self.assertEqual(
                base,
                ITEM_INFO_BASE,
                f"ItemInfo must re-open as `class ItemInfo: {ITEM_INFO_BASE}`",
            )

    def test_generated_optics_declare_external_parents(self) -> None:
        code = _code_only(GEN_SRC)
        self.assertRegex(code, r"class\s+ItemCore\s*;")
        self.assertRegex(code, r"class\s+InventoryOpticsItem_Base_F\s*;")

    def test_environmental_reopens_name_their_parent(self) -> None:
        seen: dict[str, list[str | None]] = {}
        for name, base in _definitions(ENV_SRC):
            seen.setdefault(name, []).append(base)
        for name, base in ENV_BASES.items():
            with self.subTest(klass=name):
                self.assertTrue(seen.get(name), f"class {name} missing")
                self.assertIn(
                    base,
                    seen[name],
                    f"every class {name} must re-open as `class {name}: {base}`",
                )

    def test_empty_base_classes_are_not_rebased(self) -> None:
        # HDRNewPars, DOFPars and DefaultLighting carry no vanilla base.  A
        # `: Base` on any of them makes the engine log
        # "Updating base class ''->'<name>'".
        for name, base in _definitions(ENV_SRC):
            if name in EMPTY_BASE:
                self.assertIsNone(
                    base,
                    f"class {name} must not be rebased (found `: {base}`)",
                )

    def test_no_file_root_declaration(self) -> None:
        # A file-root forward declaration makes the engine create an empty
        # class and re-parent every map onto it.  A nested declaration merges
        # with the engine's definition at that path.
        code = _code_only(ENV_SRC)
        for name in ROOT_DECL_CLASSES:
            with self.subTest(klass=name):
                self.assertIsNone(
                    re.search(rf"(?m)^class\s+{name}\s*;", code),
                    f"file-root declaration of class {name} re-creates the defect",
                )

    def test_the_generator_is_the_oracle(self) -> None:
        # A generator that drops the parent is a defect even before the file
        # is regenerated.
        seen = {name: base for name, base in _definitions(gen.render())}
        for name, base in OPTIC_BASES.items():
            self.assertEqual(seen.get(name), base, name)


if __name__ == "__main__":
    unittest.main()
