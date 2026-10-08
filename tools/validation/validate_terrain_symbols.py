#!/usr/bin/env python3
"""Validate the AEE terrain symbol textures and their config registration.

Fails when a referenced symbol has no produced .paa, when a .paa is orphaned
(produced but not referenced), when a config icon path is outside the AEE
prefix, when a config icon path does not resolve to a committed .paa, when a
referenced symbol has no source image or no provenance manifest entry, and
when the manifest entry lacks a source or a licence.

Run: python3 tools/validation/validate_terrain_symbols.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
SOURCE_JSON = ROOT / "data" / "symbology" / "terrain_symbols.json"
MANIFEST_JSON = ROOT / "data" / "symbology" / "terrain_sources.json"
TERRAIN_DIR = ROOT / "addons" / "optics" / "data" / "terrain"
SRC_DIR = TERRAIN_DIR / "src"
CONFIG_FILES = (
    ROOT / "addons" / "optics" / "config_locationtypes.hpp",
    ROOT / "addons" / "optics" / "config_mapicons.hpp",
)
ADDON_PREFIX = "\\z\\aee\\addons\\optics\\data\\terrain\\"


def referenced(doc: dict) -> list[str]:
    out: list[str] = []
    for section in ("locations", "objects"):
        for row in doc.get(section, []):
            symbol = row.get("symbol")
            if symbol and symbol not in out:
                out.append(symbol)
    return out


def main() -> int:
    errors: list[str] = []
    for path in (SOURCE_JSON, MANIFEST_JSON):
        if not path.exists():
            print(f"validate_terrain_symbols: {path.name} missing")
            return 1

    doc = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in manifest.get("entries", [])}
    unavailable = {entry["id"]: entry for entry in manifest.get("unavailable", [])}
    refs = referenced(doc)

    for symbol in refs:
        if symbol not in entries:
            if symbol in unavailable:
                errors.append(f"{symbol}: unreferenced but listed unavailable")
            else:
                errors.append(f"{symbol}: no source manifest entry")
            continue
        entry = entries[symbol]
        if not str(entry.get("source", "")).strip():
            errors.append(f"{symbol}: manifest entry has no source")
        if not str(entry.get("licence", "")).strip():
            errors.append(f"{symbol}: manifest entry has no licence")
        licence = str(entry.get("licence", "")).lower()
        if "public domain" not in licence and "cc by" not in licence:
            errors.append(f"{symbol}: licence is not an open source")
        if not (SRC_DIR / entry.get("file", "")).is_file():
            errors.append(f"{symbol}: source image is missing")
        if not (TERRAIN_DIR / f"{symbol}.paa").is_file():
            errors.append(f"{symbol}: produced texture is missing")

    for orphan in sorted(set(entries) - set(refs)):
        errors.append(f"{orphan}: manifest entry is not referenced")

    produced = (
        {p.stem for p in TERRAIN_DIR.glob("*.paa")} if TERRAIN_DIR.is_dir() else set()
    )
    for orphan in sorted(produced - set(refs)):
        errors.append(f"{orphan}.paa is produced but not referenced")

    config_text = ""
    for path in CONFIG_FILES:
        if not path.exists():
            errors.append(f"{path.name} missing")
            continue
        config_text += path.read_text(encoding="utf-8")

    config_paths = re.findall(r'(?:texture|icon)\s*=\s*"([^"]+)"', config_text)
    for icon in config_paths:
        if not icon.startswith(ADDON_PREFIX):
            errors.append(f"{icon}: icon path is outside the AEE prefix")
            continue
        asset = TERRAIN_DIR / icon.replace("\\", "/").rsplit("/", 1)[-1]
        if not asset.is_file():
            errors.append(f"{icon}: registered asset is missing")

    registered = {
        Path(p.replace("\\", "/")).stem
        for p in config_paths
        if p.startswith(ADDON_PREFIX)
    }
    for symbol in refs:
        if symbol not in registered:
            errors.append(f"{symbol}: referenced but not registered in config")

    if errors:
        print(f"validate_terrain_symbols: FAIL ({len(errors)})")
        for line in errors[:40]:
            print(f"  {line}")
        return 1
    print(
        f"validate_terrain_symbols: PASS ({len(refs)} referenced, "
        f"{len(registered)} registered, {len(produced)} produced, "
        f"{len(unavailable)} unavailable)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
