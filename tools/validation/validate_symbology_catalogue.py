#!/usr/bin/env python3
"""Validate data/symbology/nato_catalogue.json.

Rejects a non-symbol catalogue entry, so the article images, war maps and unit
insignia that the first pull admitted cannot re-enter the catalogue.

Run: python3 tools/validation/validate_symbology_catalogue.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
CATALOGUE = ROOT / "data" / "symbology" / "nato_catalogue.json"
DROPPED = ROOT / "data" / "symbology" / "dropped.json"
PULL = Path("/tmp/opencode/nato-symbols")

AFFIL = {"Friend", "Hostile", "Neutral", "Unknown"}
DIM = {"Land", "Air/Space", "Sea Surface", "Subsurface", "Installation", "Equipment"}
KIND = {"symbol", "echelon"}


def main() -> int:
    if not CATALOGUE.exists():
        print("validate_symbology_catalogue: catalogue missing")
        return 1
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    entries = data["entries"]
    errors: list[str] = []
    for e in entries:
        name = e.get("file", "?")
        if e.get("kind", "symbol") not in KIND:
            errors.append(f"{name}: unknown kind {e.get('kind')!r}")
        if e.get("kind", "symbol") == "symbol":
            if e.get("affil") not in AFFIL:
                errors.append(f"{name}: affiliation {e.get('affil')!r} not resolved")
            if e.get("dim") not in DIM:
                errors.append(f"{name}: dimension {e.get('dim')!r} not resolved")
        if not e.get("url"):
            errors.append(f"{name}: no source url (attribution is required)")
    if not DROPPED.exists():
        errors.append("dropped.json missing: the drop reasons are not recorded")
    else:
        for d in json.loads(DROPPED.read_text(encoding="utf-8")):
            if not d.get("reason"):
                errors.append(f"{d.get('title')}: dropped without a reason")
    if errors:
        print(f"validate_symbology_catalogue: FAIL ({len(errors)})")
        for line in errors[:40]:
            print(f"  {line}")
        return 1
    print(f"validate_symbology_catalogue: PASS ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
