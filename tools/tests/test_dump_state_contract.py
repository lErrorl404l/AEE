#!/usr/bin/env python3
"""Source contract: every addon that publishes aee_<component>_* state must
expose one state dump.

An addon that writes ``missionNamespace setVariable [QGVAR(...)]`` (or
``[EGVAR(...)]``) publishes state.  Every such addon must either register a
per-module dump (``PREP(dumpState)`` or ``PREPS(group, dumpState)``) in its
``XEH_PREP.hpp``, reuse one of the three consolidated logs
(``fnc_logWildlifeState``, ``fnc_logSkyState``, ``fnc_logAirframeState``), or
sit on the allowlist below with a reason.

Run: python3 -m unittest tools.tests.test_dump_state_contract
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"

# addon -> reason.  An entry here is a deliberate exemption from the dump
# contract.  Empty means every publishing addon must expose a dump.
ALLOWLIST: dict[str, str] = {
    "lib": "infrastructure: the shared kernels hold private caches (PP "
    "registry, geo anchor, engine-handler specs) with no togglable "
    "module and no debug switch",
}

# addon -> the addon whose PREP(dumpState) dumps it.  Core publishes state but
# its consolidated dump moved to diagnostics (step 2 split, ADR-032); the dump
# reads the aee_core_* variables via EGVAR, so core still has one state dump.
HOSTED_DUMPS: dict[str, str] = {
    "core": "diagnostics",
    "eye": "optics",
    "vision": "optics",
    "symbology": "optics",
    "cartography": "optics",
    "hud": "optics",
}

# A state write: missionNamespace setVariable [QGVAR(x), ...] or the EGVAR
# form, optionally inside a format [] for a composed name.
_WRITE = re.compile(
    r"missionNamespace\s+setVariable\s*\[\s*(?:format\s*\[\s*)?Q?(?:E)?GVAR\s*\("
)
_PREP_DUMP = re.compile(r"\bPREPS?\(\s*(?:\w+\s*,\s*)?dumpState\s*\)")
_EXISTING_DUMP = re.compile(r"\b(?:logWildlifeState|logSkyState|logAirframeState)\b")


def _publishing_addons() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted(ADDONS.rglob("*.sqf")):
        addon = path.relative_to(ADDONS).parts[0]
        text = path.read_text(encoding="utf-8", errors="replace")
        if _WRITE.search(text):
            found.setdefault(addon, []).append(str(path.relative_to(REPO)))
    return found


class TestDumpStateContract(unittest.TestCase):
    def test_every_publishing_addon_has_a_state_dump(self):
        missing = []
        for addon, files in sorted(_publishing_addons().items()):
            if addon in ALLOWLIST:
                continue
            host = HOSTED_DUMPS.get(addon, addon)
            prep = ADDONS / host / "XEH_PREP.hpp"
            src = prep.read_text(encoding="utf-8") if prep.exists() else ""
            if _PREP_DUMP.search(src) or _EXISTING_DUMP.search(src):
                continue
            missing.append(
                f"{addon} writes state in {', '.join(files)} but has no PREP(dumpState)"
            )
        self.assertEqual(missing, [], "; ".join(missing))

    def test_the_allowlist_has_a_reason_for_every_entry(self):
        for addon, reason in ALLOWLIST.items():
            self.assertTrue(reason.strip(), f"{addon} allowlist entry has no reason")

    def test_the_three_existing_dumps_are_still_prepped(self):
        for addon, name in (
            ("wildlife", "logWildlifeState"),
            ("environmental", "logSkyState"),
            ("mobility", "logAirframeState"),
        ):
            prep = ADDONS / addon / "XEH_PREP.hpp"
            src = prep.read_text(encoding="utf-8")
            self.assertRegex(src, rf"\b{name}\b")


if __name__ == "__main__":
    unittest.main()
