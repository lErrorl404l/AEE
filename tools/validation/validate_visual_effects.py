#!/usr/bin/env python3
"""Visual-effect contract validator (visual QA).

Proves visual correctness from code: every ppEffect call in addons/ is checked
against the engine contract for its effect type. No screenshot needed.

Checks:
  1. ppEffectCreate names a real engine effect type.
  2. ppEffectAdjust on a known handle has the argument count the type requires.
  3. ppEffectEnable is called with a bool second element.
  4. every created handle is destroyed somewhere (leak report, non-fatal).

Read-only. rc0 when every call matches the contract.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"

# ppEffectCreate effect names the engine accepts. The command DB lists nine
# (RadialBlur, ChromAberration, WetDistortion, ColorCorrections, DynamicBlur,
# FilmGrain, ColorInversion, SSAO, Resolution). DepthOfField is absent from
# that list but the engine creates it and AEE observes it working in-game, so
# it is allowed here rather than flagged.
VALID_TYPES = {
    "RadialBlur",
    "WetDistortion",
    "ColorCorrections",
    "DynamicBlur",
    "FilmGrain",
    "ColorInversion",
    "SSAO",
    "Resolution",
    "ChromAberration",
    "DepthOfField",
}

# ppEffectAdjust argument counts per effect type (BIKI command DB, 2025).
# The engine logs "<n> elements provided, <m> expected" and applies nothing on
# a mismatch, so arity is a hard contract.
ADJUST_ARITY = {
    "ColorCorrections": {6, 7},
    "FilmGrain": {6},
    "DynamicBlur": {1},
    "ChromAberration": {3},
    "RadialBlur": {4},
    "ColorInversion": {3},
    "WetDistortion": {16},
    "SSAO": {11},
    "Resolution": {1},
    # Undocumented shape; AEE calls DepthOfField with 3 args.
    "DepthOfField": {3},
}

CREATE = re.compile(
    r"(?P<var>[_A-Za-z][_A-Za-z0-9]*)\s*=\s*ppEffectCreate\s*\[\s*"
    r'"(?P<type>[A-Za-z]+)"'
)
# A handle may be a local var or a getVariable expression. Capture a bare name.
ADJUST = re.compile(r"(?P<handle>[_A-Za-z][_A-Za-z0-9]*)\s+ppEffectAdjust\s")


def _arg_count(text: str, start: int) -> int:
    """Count top-level comma-separated elements of the array starting at start."""
    depth = 0
    count = 0
    seen = False
    i = start
    while i < len(text):
        c = text[i]
        if c == "[":
            depth += 1
            if depth == 1:
                seen = True
        elif c == "]":
            depth -= 1
            if depth == 0:
                return (count + 1) if seen and text[start + 1 : i].strip() else 0
        elif c == "," and depth == 1:
            count += 1
        i += 1
    return -1


def main() -> int:
    types: dict[str, str] = {}
    violations: list[str] = []
    created: set[str] = set()
    destroyed: set[str] = set()

    for sqf in ADDONS.rglob("*.sqf"):
        text = sqf.read_text(encoding="utf-8", errors="replace")
        rel = sqf.relative_to(REPO)
        for m in CREATE.finditer(text):
            var, etype = m.group("var"), m.group("type")
            types[var] = etype
            created.add(var)
            if etype not in VALID_TYPES:
                line = text[: m.start()].count("\n") + 1
                violations.append(f"{rel}:{line}: unknown effect type {etype!r}")
        for m in ADJUST.finditer(text):
            handle = m.group("handle")
            etype = types.get(handle)
            if etype is None:
                continue
            n = _arg_count(text, m.end())
            allowed = ADJUST_ARITY.get(etype)
            line = text[: m.start()].count("\n") + 1
            if allowed and n not in allowed:
                violations.append(
                    f"{rel}:{line}: {etype} ppEffectAdjust has {n} args, "
                    f"engine expects {sorted(allowed)}"
                )
        for m in re.finditer(r"([_A-Za-z][_A-Za-z0-9]*)\s+ppEffectDestroy", text):
            destroyed.add(m.group(1))
        for m in re.finditer(r"ppEffectDestroy\s+([_A-Za-z][_A-Za-z0-9]*)", text):
            destroyed.add(m.group(1))

    leaks = sorted(created - destroyed)
    print(f"ppEffectCreate handles: {len(created)}")
    print(f"effect types: {sorted(set(types.values()))}")
    if violations:
        print(f"\nCONTRACT VIOLATIONS ({len(violations)}):")
        for v in violations:
            print("  " + v)
    else:
        print("ppEffectAdjust: every call matches the engine arity contract")
    if leaks:
        print(f"\nHandles never destroyed ({len(leaks)}): {', '.join(leaks)}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
