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


if __name__ == "__main__":
    unittest.main()
