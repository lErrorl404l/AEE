#!/usr/bin/env python3
"""CfgMarkers schema validator (visual QA).

Proves map-symbol correctness from code, with no screenshot. It checks the
mod's marker config against the engine contract:

  1. every icon = "path" resolves to a real .paa file. A \\z\\aee\\addons\\...
     path maps into the repo; a \\a3\\ path is vanilla (not checked here).
  2. every markerClass = "X" names a class the mod declares. An undefined
     group puts the symbol in no picker category.
  3. no class uses markerType as a field - markerType is an SQF command, and
     the engine ignores it as a config field.

Read-only. rc0 when every icon resolves and every markerClass is declared.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"

CONFIG_GLOBS = ("*.hpp", "*.cpp", "*.inc", "*.sqf")
AEE_PREFIX = "\\z\\aee\\addons\\"
A3_PREFIX = "\\a3\\"

ICON = re.compile(r'\bicon\s*=\s*"([^"]*)"')
MARKER_CLASS = re.compile(r'\bmarkerClass\s*=\s*"([^"]*)"')
CLASS_DECL = re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)")
FIELD_MARKER_TYPE = re.compile(r"^\s*markerType\s*=", re.MULTILINE)


def strip_comments(text: str) -> str:
    out = list(text)
    i, n, in_str = 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            if c == '"':
                in_str = False
            i += 1
        elif c == '"':
            in_str = True
            i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            while i < n and not (text[i] == "*" and i + 1 < n and text[i + 1] == "/"):
                if text[i] != "\n":
                    out[i] = " "
                i += 1
            for _ in range(2):
                if i < n:
                    out[i] = " "
                    i += 1
        else:
            i += 1
    return "".join(out)


def main() -> int:
    declared: set[str] = set()
    marker_classes: list[tuple[str, str, int]] = []
    icons: list[tuple[str, str, int]] = []
    bad_field: list[str] = []

    for path in sorted(p for g in CONFIG_GLOBS for p in ADDONS.rglob(g)):
        text = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        rel = path.relative_to(REPO)
        for m in CLASS_DECL.finditer(text):
            declared.add(m.group(1))
        if FIELD_MARKER_TYPE.search(text):
            line = text[: FIELD_MARKER_TYPE.search(text).start()].count("\n") + 1
            bad_field.append(f"{rel}:{line}: markerType used as a config field")
        for m in MARKER_CLASS.finditer(text):
            marker_classes.append(
                (str(rel), m.group(1), text[: m.start()].count("\n") + 1)
            )
        for m in ICON.finditer(text):
            icons.append((str(rel), m.group(1), text[: m.start()].count("\n") + 1))

    missing_icons: list[str] = []
    for rel, icon, line in icons:
        if icon.startswith(AEE_PREFIX):
            sub = icon[len(AEE_PREFIX) :].replace("\\", "/")
            if not sub.lower().endswith(".paa"):
                sub += ".paa"
            target = REPO / "addons" / sub
            if not target.is_file():
                missing_icons.append(f"{rel}:{line}: icon not found: {icon}")

    unresolved = sorted({(c, n) for c, n, _ in marker_classes if n not in declared})
    unresolved_rows = [
        f"{c}:{ln}: markerClass {n!r} is never declared as a class"
        for c, n, ln in marker_classes
        if n not in declared
    ]

    print(
        f"icon fields: {len(icons)} ({sum(1 for _, i, _ in icons if i.startswith(AEE_PREFIX))} aee-local)"
    )
    print(
        f"markerClass references: {len(marker_classes)} ({len(unresolved)} distinct unresolved)"
    )
    print(f"classes declared in addons: {len(declared)}")

    ok = True
    for label, rows in (
        ("BAD CONFIG FIELD", bad_field),
        ("MISSING ICON", missing_icons),
        ("UNDECLARED markerClass", unresolved_rows),
    ):
        if rows:
            ok = False
            print(f"\n{label} ({len(rows)}):")
            for r in rows[:40]:
                print("  " + r)
            if len(rows) > 40:
                print(f"  ... {len(rows) - 40} more")
    if ok:
        print("every marker icon resolves and every markerClass is declared")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
