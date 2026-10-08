#!/usr/bin/env python3
"""Validate the MIL-STD-2525 taxonomy marker layer.

Rejects a taxonomy entry whose marker is not registered, whose asset is
missing, or whose name prefix does not encode its affiliation and dimension.

Run: python3 tools/validation/validate_symbology_taxonomy.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
TAXONOMY = ROOT / "data" / "symbology" / "app6_taxonomy.json"
CONFIG = ROOT / "addons" / "optics" / "config_taxonomy.hpp"
MARKERS = ROOT / "addons" / "optics" / "data" / "markers"

AFFIL_LETTER = {"Friend": "F", "Hostile": "H", "Neutral": "N", "Unknown": "U"}
DIM_LETTER = {
    "Land": "L",
    "Air/Space": "A",
    "Space": "P",
    "Sea Surface": "S",
    "Subsurface": "U",
    "Installation": "I",
    "Equipment": "E",
}


def main() -> int:
    if not TAXONOMY.exists():
        print("validate_symbology_taxonomy: taxonomy missing")
        return 1
    config = CONFIG.read_text(encoding="utf-8")
    entries = json.loads(TAXONOMY.read_text(encoding="utf-8"))["entries"]
    errors: list[str] = []
    seen: set[str] = set()
    for e in entries:
        marker = e.get("marker", "?")
        if marker in seen:
            errors.append(f"{marker}: duplicate marker")
        seen.add(marker)
        if f"class {marker}: AEE_MarkerBase {{" not in config:
            errors.append(f"{marker}: not registered in config_taxonomy.hpp")
        if not (MARKERS / f"{marker}.paa").is_file():
            errors.append(f"{marker}: asset missing")
        prefix = marker.split("_")[1] if "_" in marker else ""
        want = AFFIL_LETTER.get(e.get("affil", ""), "?") + DIM_LETTER.get(
            e.get("dim", ""), "?"
        )
        if prefix != want:
            errors.append(f"{marker}: prefix {prefix!r} must encode {want!r}")
        if len(e.get("sidc", "")) != 15:
            errors.append(f"{marker}: SIDC {e.get('sidc')!r} is not 15 characters")
    if errors:
        print(f"validate_symbology_taxonomy: FAIL ({len(errors)})")
        for line in errors[:40]:
            print(f"  {line}")
        return 1
    print(f"validate_symbology_taxonomy: PASS ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
