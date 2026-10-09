#!/usr/bin/env python3
"""The dev visual workbench holds its surface.

A source contract over the dev project (``tools/dev-harness/addons/dev``):

  1. four CBA keybinds register under the ``AEE Dev`` category, each with a
     handler that calls a named dev function;
  2. no shipped ``addons/*/initSettings.inc.sqf`` gains a dev setting, so the
     workbench stays out of the shipped settings taxonomy.

The visual parts (a screenshot, a rendered verdict) are a manual ceiling: a
dedicated server renders nothing, so they are never asserted here.

Run: python3 -m unittest tools.tests.test_dev_workbench
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "tools" / "dev-harness" / "addons" / "dev"
POST = DEV / "XEH_postInit.sqf"
PRE = DEV / "XEH_preInit.sqf"
FUNCS = DEV / "functions"

CATEGORY = "AEE Dev"

# keybind action name -> the dev function its handler must call.
KEYBINDS = {
    "DevReapplyVisual": "aee_dev_fnc_devReapplyVisual",
    "DevScreenshot": "aee_dev_fnc_devScreenshot",
    "DevDump": "aee_dev_fnc_devDumpAll",
    "DevOverlayToggle": "aee_dev_fnc_devOverlayToggle",
}

REAPPLY = FUNCS / "fnc_devReapplyVisual.sqf"
SCREENSHOT = FUNCS / "fnc_devScreenshot.sqf"

ADDONS = ROOT / "addons"


def _code_only(text: str) -> str:
    """Blank ``//`` and ``/* */`` comments so a prose word is not a code hit."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def _keybind_blocks(text: str) -> dict[str, str]:
    """One slice of source per action, from its name to its addKeybind call."""
    blocks: dict[str, str] = {}
    for name in KEYBINDS:
        start = text.find(f'"{name}"')
        if start == -1:
            continue
        end = text.find("CBA_fnc_addKeybind", start)
        end = len(text) if end == -1 else end
        blocks[name] = text[start:end]
    return blocks


class TestWorkbenchKeybinds(unittest.TestCase):
    def test_the_category_is_the_dev_category(self):
        self.assertIn(f'"{CATEGORY}"', POST.read_text(encoding="utf-8"))

    def test_all_four_keybinds_are_registered(self):
        text = POST.read_text(encoding="utf-8")
        for name in KEYBINDS:
            self.assertIn(f'"{name}"', text, name)

    def test_every_keybind_resolves_a_handler_function(self):
        code = _code_only(POST.read_text(encoding="utf-8"))
        blocks = _keybind_blocks(code)
        self.assertEqual(set(blocks), set(KEYBINDS))
        for name, fn in KEYBINDS.items():
            self.assertIn(f"call {fn}", blocks[name], name)

    def test_the_dev_category_is_not_a_shipped_setting(self):
        shipped = sorted((ROOT / "addons").glob("*/initSettings.inc.sqf"))
        self.assertTrue(shipped)
        for path in shipped:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(f'"{CATEGORY}"', text, str(path))
            self.assertNotIn("aee_dev_", text, str(path))


class TestRuntimeReapply(unittest.TestCase):
    """The re-apply re-runs the pipeline through the core registry."""

    def test_the_reapply_is_compiled(self):
        self.assertIn("fnc_devReapplyVisual", PRE.read_text(encoding="utf-8"))

    def test_the_reapply_releases_each_scope_through_the_registry(self):
        code = _code_only(REAPPLY.read_text(encoding="utf-8"))
        for scope in ("optics", "nightvision", "thermal"):
            self.assertIn(f'["{scope}", ""] call aee_core_fnc_destroyPPEffect', code)

    def test_the_reapply_has_no_raw_effect_create(self):
        # The only "ppEffectCreate" allowed is the owning function NAME
        # (aee_optics_fnc_ppEffectCreate). A raw engine call is refused.
        code = _code_only(REAPPLY.read_text(encoding="utf-8"))
        raw = re.findall(r"(?<!fnc_)ppEffectCreate", code)
        self.assertEqual(raw, [])

    def test_the_reapply_covers_the_five_named_paths(self):
        code = _code_only(REAPPLY.read_text(encoding="utf-8"))
        for fn in (
            "aee_optics_fnc_ppEffectCreate",
            "aee_optics_fnc_applyBaseGrade",
            "aee_optics_fnc_applyWeatherGrain",
            "aee_nightvision_fnc_applyNightGrain",
            "aee_thermal_fnc_createThermalPPEffects",
        ):
            self.assertIn(f"call {fn}", code, fn)

    def test_the_apply_paths_route_through_the_registry_create(self):
        # The paths the re-apply re-runs create through the core registry, not
        # a raw ppEffectCreate of their own. The thermal choke point is the
        # documented exception (it owns the engine create for its eight
        # effects), so it is not part of this check.
        for rel in (
            "optics/functions/vision/fnc_ppEffectCreate.sqf",
            "optics/functions/grade/fnc_applyBaseGrade.sqf",
            "optics/functions/vision/fnc_applyWeatherGrain.sqf",
            "nightvision/functions/fnc_applyNightGrain.sqf",
        ):
            text = (ADDONS / rel).read_text(encoding="utf-8")
            self.assertIn("createPPEffect", text, rel)


class TestScreenshot(unittest.TestCase):
    """The labelled screenshot pairs the image with the AEE state."""

    def test_the_screenshot_is_compiled(self):
        self.assertIn("fnc_devScreenshot", PRE.read_text(encoding="utf-8"))

    def test_the_screenshot_command_takes_a_labelled_name(self):
        code = _code_only(SCREENSHOT.read_text(encoding="utf-8"))
        self.assertIn("screenshot ", code)
        self.assertIn('"aee_%1_%2"', code)

    def test_a_paired_state_line_names_the_file(self):
        code = _code_only(SCREENSHOT.read_text(encoding="utf-8"))
        # The state (the core dump) is emitted with the file name.
        self.assertIn("aee_core_fnc_dumpState", code)
        self.assertIn("%1.png", code)
        self.assertIn("diag_log", code)

    def test_no_gate_references_the_image_file(self):
        gates = [ROOT / "tools" / "run_tests.py"]
        gates += [
            p
            for p in sorted((ROOT / "tools" / "tests").glob("*.py"))
            if p.name != "test_dev_workbench.py"
        ]
        for path in gates:
            text = path.read_text(encoding="utf-8", errors="replace")
            self.assertNotIn("devScreenshot", text, str(path))
            self.assertNotIn("aee_manual", text, str(path))


if __name__ == "__main__":
    unittest.main()
