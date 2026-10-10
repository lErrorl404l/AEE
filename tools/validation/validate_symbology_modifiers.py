#!/usr/bin/env python3
"""Validate the AEE mission-task, modifier and echelon marker registration.

Fails if any registered asset is missing, or any marker name in
addons/symbology/config_modifiers.hpp is not listed in data/symbology/modifiers.json
(and the reverse).  The two files are generated together, so a mismatch means the
tree is stale or hand-edited.

Run: python3 tools/validation/validate_symbology_modifiers.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
CONFIG = ROOT / "addons" / "optics" / "config_modifiers.hpp"
JSON = ROOT / "data" / "symbology" / "modifiers.json"
MARKERS = ROOT / "addons" / "optics" / "data" / "markers"
ADDON_PREFIX = "\\z\\aee\\addons\\optics\\data\\markers\\"
PREFIX = {"mission_task": "AEE_MT_", "modifier": "AEE_MOD_", "echelon": "AEE_Ech_"}
KIND = set(PREFIX)


def parse_config() -> dict[str, str]:
    text = CONFIG.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for m in re.finditer(
        r"class (\w+): AEE_MarkerBase \{\s*"
        r'name = "[^"]*";\s*'
        r'icon = "([^"]+)";\s*'
        r'texture = "([^"]+)";',
        text,
    ):
        found[m.group(1)] = m.group(2)
    return found


def main() -> int:
    errors: list[str] = []
    if not JSON.exists():
        print("validate_symbology_modifiers: modifiers.json missing")
        return 1
    if not CONFIG.exists():
        print("validate_symbology_modifiers: config_modifiers.hpp missing")
        return 1

    doc = json.loads(JSON.read_text(encoding="utf-8"))
    markers = doc.get("markers", [])
    config = parse_config()

    names = {m["name"] for m in markers}
    if len(names) != len(markers):
        errors.append("duplicate marker name in modifiers.json")

    for m in markers:
        name = m["name"]
        if m.get("kind") not in KIND:
            errors.append(f"{name}: unknown kind {m.get('kind')!r}")
        else:
            if not name.startswith(PREFIX[m["kind"]]):
                errors.append(f"{name}: wrong prefix for kind {m['kind']}")
        if not m.get("source", "").strip():
            errors.append(f"{name}: no geometry source citation")
        if name not in config:
            errors.append(f"{name}: not registered in config_modifiers.hpp")
            continue
        icon = config[name]
        if not icon.startswith(ADDON_PREFIX):
            errors.append(f"{name}: icon path is outside the addon prefix")
        asset = MARKERS / icon.replace("\\", "/").rsplit("/", 1)[-1]
        if not asset.is_file():
            errors.append(f"{name}: registered asset {asset.name} is missing")

    for cls in config:
        if cls not in names:
            errors.append(f"{cls}: registered in config but not in modifiers.json")

    for e in doc.get("unavailable", []):
        if not e.get("reason", "").strip():
            errors.append(f"{e.get('name')}: unavailable without a reason")
        if e.get("name") in config:
            errors.append(f"{e.get('name')}: unavailable but registered")
        if (MARKERS / f"{e.get('name')}.paa").exists():
            errors.append(f"{e.get('name')}: unavailable but has an asset")

    if errors:
        print(f"validate_symbology_modifiers: FAIL ({len(errors)})")
        for line in errors[:40]:
            print(f"  {line}")
        return 1
    print(
        f"validate_symbology_modifiers: PASS ({len(markers)} markers, "
        f"{len(doc.get('unavailable', []))} unavailable)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
