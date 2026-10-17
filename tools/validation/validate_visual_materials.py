#!/usr/bin/env python3
"""Material and hidden-selection validator (visual QA).

Proves two material contracts from code, with no screenshot:

  1. every .rvmat declares a PixelShaderID and a VertexShaderID, and any
     texture = "path" that is a real path (not a procedural #(rgb,...))
     resolves for a \\z\\aee\\... path.
  2. hiddenSelections[] and hiddenSelectionsTextures[] in the same class have
     the same element count. The engine paints by index, so a mismatch
     textures the wrong selection.

Read-only. rc0 when every material and selection list is consistent.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
AEE_PREFIX = "\\z\\aee\\addons\\"

TEXTURE = re.compile(r'\btexture\s*=\s*"([^"]*)"')
PIXEL = re.compile(r"\bPixelShaderID\s*=")
VERTEX = re.compile(r"\bVertexShaderID\s*=")
HSEL = re.compile(r"\bhiddenSelections\s*\[\]\s*=\s*\{(.*?)\}", re.DOTALL)
HTEX = re.compile(r"\bhiddenSelectionsTextures\s*\[\]\s*=\s*\{(.*?)\}", re.DOTALL)
CLASS = re.compile(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)")


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


def elems(body: str) -> list[str]:
    return [e.strip() for e in body.split(",") if e.strip()]


def main() -> int:
    problems: list[str] = []
    rvmats = 0

    for path in sorted(ADDONS.rglob("*.rvmat")):
        rvmats += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(REPO)
        if not PIXEL.search(text) or not VERTEX.search(text):
            problems.append(f"{rel}: missing PixelShaderID or VertexShaderID")
        for m in TEXTURE.finditer(text):
            tex = m.group(1)
            if tex.startswith("#") or not tex:
                continue
            if tex.startswith(AEE_PREFIX):
                sub = tex[len(AEE_PREFIX) :].replace("\\", "/")
                if not (REPO / "addons" / sub).is_file():
                    problems.append(f"{rel}: texture not found: {tex}")

    sel = 0
    for path in sorted(p for g in ("*.hpp", "*.cpp") for p in ADDONS.rglob(g)):
        text = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        rel = path.relative_to(REPO)
        for hs, ht in zip(HSEL.finditer(text), HTEX.finditer(text)):
            sel += 1
            name = ""
            for cm in CLASS.finditer(text[: hs.start()]):
                name = cm.group(1)
            hn, tn = len(elems(hs.group(1))), len(elems(ht.group(1)))
            if hn != tn:
                line = text[: hs.start()].count("\n") + 1
                problems.append(
                    f"{rel}:{line}: class {name}: {hn} hiddenSelections vs "
                    f"{tn} hiddenSelectionsTextures"
                )

    print(f"rvmat files: {rvmats}; hiddenSelections pairs: {sel}")
    if problems:
        print(f"\nPROBLEMS ({len(problems)}):")
        for p in problems[:60]:
            print("  " + p)
    else:
        print("every material declares shaders and every selection list aligns")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
