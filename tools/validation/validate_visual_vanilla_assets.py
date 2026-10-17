#!/usr/bin/env python3
"""Vanilla-asset provenance validator (visual QA).

Cross-checks the mod against the game's own PBOs. Every \\A3\\... asset a
config or script references must exist in an installed game PBO. A missing
asset is a silent visual failure: the engine draws nothing (icons, particles,
materials).

The game's PBO file tables are indexed once and cached at
.opencode/cache/vanilla-assets.json. Rebuild with --reindex.

Set A3_GAME to the Arma 3 root if it is not at the default Steam path.
Read-only. rc0 when every referenced vanilla asset resolves (or the game is
not installed, in which case the check is skipped).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
CACHE = REPO / ".opencode" / "cache" / "vanilla-assets.json"
DEFAULT_GAME = "/ext/SteamLibrary/steamapps/common/Arma 3"
A3_REF = re.compile(r'"\\(A3\\[^"]*)"')
CONFIG_GLOBS = ("*.sqf", "*.hpp", "*.cpp", "*.inc")
# a texture/model reference may omit the extension
EXT_CANDIDATES = ("", ".paa", ".p3d", ".rvmat", ".ogv")


def game_root() -> Path | None:
    root = Path(os.environ.get("A3_GAME", DEFAULT_GAME))
    return root if root.is_dir() else None


def list_pbo(pbo: Path) -> tuple[str, set[str]]:
    """Return (prefix, entries) for one PBO via extractpbo -L."""
    try:
        out = subprocess.run(
            ["extractpbo", "-L", "-P", str(pbo)],
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return "", set()
    prefix = ""
    entries: set[str] = set()
    for line in out.splitlines():
        if line.startswith("prefix="):
            prefix = (
                line[len("prefix=") :].strip().strip(";").replace("/", "\\").lower()
            )
            continue
        if line.startswith(("Opening", "====", "//<", "prefix=")):
            continue
        name = line.split(":", 1)[0].strip()
        if name and "\\" in name or (name and "." in name):
            entries.add(name.replace("/", "\\").lower())
    return prefix, entries


def build_index(root: Path) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for pbo in sorted(root.rglob("*.pbo")):
        if "workshop" in pbo.parts:
            continue
        prefix, entries = list_pbo(pbo)
        if prefix and entries:
            index.setdefault(prefix, [])
            index[prefix].extend(sorted(entries))
    return index


def load_index(root: Path, reindex: bool) -> dict[str, set[str]]:
    if not reindex and CACHE.is_file():
        raw = json.loads(CACHE.read_text())
        return {k: set(v) for k, v in raw.items()}
    index = build_index(root)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({k: sorted(v) for k, v in index.items()}, indent=0))
    return {k: set(v) for k, v in index.items()}


def resolve(ref: str, index: dict[str, set[str]]) -> bool:
    ref = ref.replace("/", "\\").lower()
    best: tuple[int, set[str]] | None = None
    for prefix, entries in index.items():
        if ref == prefix or ref.startswith(prefix + "\\"):
            if best is None or len(prefix) > best[0]:
                best = (len(prefix), entries)
    if best is None:
        return False
    entries = best[1]
    tail = ref[best[0] + 1 :]
    return any(tail + ext in entries for ext in EXT_CANDIDATES)


def main() -> int:
    reindex = "--reindex" in sys.argv
    root = game_root()
    if root is None:
        print("vanilla-asset provenance: SKIP (game not found; set A3_GAME)")
        return 0

    refs: set[str] = set()
    for path in (p for g in CONFIG_GLOBS for p in ADDONS.rglob(g)):
        for m in A3_REF.finditer(path.read_text(encoding="utf-8", errors="replace")):
            refs.add(m.group(1))

    index = load_index(root, reindex)
    missing = sorted(r for r in refs if not resolve(r, index))

    print(f"vanilla \\A3\\ refs: {len(refs)}; game PBO prefixes indexed: {len(index)}")
    if missing:
        print(f"\nUNRESOLVED VANILLA ASSETS ({len(missing)}):")
        for r in missing:
            print(f"  \\{r}")
    else:
        print("every referenced vanilla asset resolves in an installed game PBO")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
