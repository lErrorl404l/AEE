#!/usr/bin/env python3
"""Validate data/symbology/nato_catalogue.json and its committed sources.

Rejects a non-symbol catalogue entry, so the article images, war maps and unit
insignia that the first pull admitted cannot re-enter the catalogue.  Also
proves every entry carries a source URL and an open licence, that its source
SVG is committed under data/symbology/sources/svg, and that every symbol entry
has its committed 64 px render under data/symbology/sources/render.

Run: python3 tools/validation/validate_symbology_catalogue.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
CATALOGUE = ROOT / "data" / "symbology" / "nato_catalogue.json"
DROPPED = ROOT / "data" / "symbology" / "dropped.json"
SOURCES = ROOT / "data" / "symbology" / "sources"
SVG_ROOT = SOURCES / "svg"
RENDER_ROOT = SOURCES / "render"

sys.path.insert(0, str(ROOT / "tools"))
import gen_symbology_catalogue as gen  # noqa: E402

AFFIL = {"Friend", "Hostile", "Neutral", "Unknown"}
DIM = {"Land", "Air/Space", "Sea Surface", "Subsurface", "Installation", "Equipment"}
KIND = {"symbol", "echelon"}
# The uploader licences the catalogue admits.  The symbol design is a standard;
# the tag is the licence on the uploader's own SVG trace.
OPEN_LICENCE = {
    "CC BY-SA 4.0",
    "CC BY-SA 2.5",
    "CC BY 2.5",
    "CC BY 2.0",
    "CC0",
    "Public domain",
}


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
        if e.get("license") not in OPEN_LICENCE:
            errors.append(f"{name}: licence {e.get('license')!r} is not recorded")
        svg = SVG_ROOT / str(e.get("dir", "")) / str(e.get("file", ""))
        if not svg.is_file():
            errors.append(f"{name}: source SVG is not committed")
    seen: set[str] = set()
    for entry in gen.symbol_entries():
        marker = gen.marker_name(entry, seen)
        if not (RENDER_ROOT / f"{marker}.png").is_file():
            errors.append(f"{marker}: committed render is missing")
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
    print(
        f"validate_symbology_catalogue: PASS ({len(entries)} entries, "
        f"{len(gen.symbol_entries())} committed renders)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
