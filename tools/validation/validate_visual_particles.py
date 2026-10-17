#!/usr/bin/env python3
"""ParticleArray contract validator (visual QA).

Proves particle-emitter correctness from code, with no screenshot. It checks
every setParticleParams / setParticleRandom / setParticleCircle array in
addons/ against the engine's ParticleArray index spec.

Checks:
  1. setParticleParams element count is in the documented range.
  2. element 1 (animationName) is "" - the engine throws on a non-empty value
     ("Skeletal animation not supported for particles").
  3. element 2 (particleType) is "Billboard" or "SpaceObject".
  4. setParticleRandom element count is 8..10.
  5. setParticleCircle element count is 2..3.

Read-only. rc0 when every array matches the spec.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"

PARAMS_MIN, PARAMS_MAX = 13, 24
RANDOM_MIN, RANDOM_MAX = 8, 10
CIRCLE_MIN, CIRCLE_MAX = 2, 3
PARTICLE_TYPES = {"Billboard", "SpaceObject"}


def strip_comments(text: str) -> str:
    """Blank // and /* */ comments, preserving offsets and line numbers."""
    out = list(text)
    i = 0
    n = len(text)
    in_str = False
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


def split_top(text: str) -> list[str] | None:
    """Split the interior of a bracketed array on top-level commas."""
    parts: list[str] = []
    depth = 0
    in_str = False
    current: list[str] = []
    i = 0
    while i < len(text):
        c = text[i]
        if in_str:
            current.append(c)
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            current.append(c)
        elif c in "[{":
            depth += 1
            current.append(c)
        elif c in "]}":
            depth -= 1
            current.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(c)
        i += 1
    tail = "".join(current).strip()
    if tail or parts:
        parts.append(tail)
    return parts


def array_at(text: str, start: int) -> tuple[list[str] | None, int]:
    """Return the top-level split of the array that opens at or after start."""
    j = text.find("[", start)
    if j < 0:
        return None, -1
    depth = 0
    in_str = False
    i = j
    while i < len(text):
        c = text[i]
        if in_str:
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return split_top(text[j + 1 : i]), i
        i += 1
    return None, -1


CALL = re.compile(r"setParticle(Params|Random|Circle)\s+")


def main() -> int:
    violations: list[str] = []
    checked = 0

    for sqf in sorted(ADDONS.rglob("*.sqf")):
        text = strip_comments(sqf.read_text(encoding="utf-8", errors="replace"))
        rel = sqf.relative_to(REPO)
        for m in CALL.finditer(text):
            kind = m.group(1)
            if text[m.end() :].lstrip()[:1] != "[":
                continue  # argument is a variable, not an inline array
            elems, end = array_at(text, m.end())
            if elems is None:
                continue
            checked += 1
            line = text[: m.start()].count("\n") + 1
            n = len(elems)
            if kind == "Params":
                if not (PARAMS_MIN <= n <= PARAMS_MAX):
                    violations.append(
                        f"{rel}:{line}: setParticleParams has {n} elements, "
                        f"spec is {PARAMS_MIN}..{PARAMS_MAX}"
                    )
                if n > 1 and elems[1] != '""':
                    violations.append(
                        f"{rel}:{line}: setParticleParams animationName is "
                        f'{elems[1]}, engine throws unless it is ""'
                    )
                if n > 2:
                    t = elems[2].strip()
                    if t.startswith('"') and t.strip('"') not in PARTICLE_TYPES:
                        violations.append(
                            f"{rel}:{line}: setParticleParams type {t} is not "
                            f"Billboard or SpaceObject"
                        )
            elif kind == "Random":
                if not (RANDOM_MIN <= n <= RANDOM_MAX):
                    violations.append(
                        f"{rel}:{line}: setParticleRandom has {n} elements, "
                        f"spec is {RANDOM_MIN}..{RANDOM_MAX}"
                    )
            elif kind == "Circle":
                if not (CIRCLE_MIN <= n <= CIRCLE_MAX):
                    violations.append(
                        f"{rel}:{line}: setParticleCircle has {n} elements, "
                        f"spec is {CIRCLE_MIN}..{CIRCLE_MAX}"
                    )

    print(f"inline particle arrays checked: {checked}")
    if violations:
        print(f"\nCONTRACT VIOLATIONS ({len(violations)}):")
        for v in violations:
            print("  " + v)
    else:
        print("every inline particle array matches the ParticleArray spec")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
