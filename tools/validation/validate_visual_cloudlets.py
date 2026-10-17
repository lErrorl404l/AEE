#!/usr/bin/env python3
"""CfgCloudlets schema validator (visual QA).

Proves particle-class correctness from code, with no screenshot:

  1. each class CfgCloudlets block forward-declares `class Default;` and does
     not define it with a body. A body shadows the vanilla CfgCloudlets/Default
     that every base-game cloudlet inherits.
  2. every cloudlet class inherits Default.
  3. every field is a known CfgCloudlets field. An unknown field is ignored by
     the engine, so the intended effect silently does not happen.

The valid field set is the union of the documented modern fields and the
legacy fields in the game's Dta/bin.pbo CfgCloudlets block.
Read-only. rc0 when every cloudlet class is well formed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"

# Documented modern fields plus the legacy fields from bin.pbo.
VALID_FIELDS = {
    "particleShape",
    "particleType",
    "interval",
    "lifeTime",
    "moveVelocity",
    "rotationVelocity",
    "weight",
    "volume",
    "rubbing",
    "size",
    "color",
    "animationSpeed",
    "randomDirectionPeriod",
    "randomDirectionIntensity",
    "onTimerScript",
    "beforeDestroyScript",
    "positionVar",
    "MoveVelocityVar",
    "angle",
    "angleVar",
    "particleFSNtieth",
    "particleFSIndex",
    "particleFSFrameCount",
    "particleFSLoop",
    "animationName",
    "circleRadius",
    "circleVelocity",
    "timerPeriod",
    "lifeTimeVar",
    "rotationVelocityVar",
    "sizeVar",
    "randomDirectionPeriodVar",
    "randomDirectionIntensityVar",
    "angleVarVar",
    "onSurface",
    "bounceOnSurface",
    "emissiveColor",
    "vectorDir",
    "sourceSize",
    "timeToLive",
    "density",
    "damageType",
    "deltaT",
    "initT",
    "initYSpeed",
    "maxT",
    "cloudletAccY",
    "cloudletAlpha",
    "cloudletAnimPeriod",
    "cloudletDuration",
    "cloudletFadeIn",
    "cloudletFadeOut",
    "cloudletGrowUp",
    "cloudletMaxYSpeed",
    "cloudletMinYSpeed",
    "cloudletShape",
    "cloudletSize",
    "access",
}

CLASS_OPEN = re.compile(
    r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)\s*(:\s*([A-Za-z_][A-Za-z0-9_]*))?\s*\{"
)
FIELD = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", re.MULTILINE)


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


def block(text: str, start: int) -> str | None:
    """Return the body of the brace block whose { is at or after start."""
    j = text.find("{", start)
    if j < 0:
        return None
    depth = 0
    i = j
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[j + 1 : i]
        i += 1
    return None


def main() -> int:
    problems: list[str] = []
    blocks = 0
    classes = 0

    for path in sorted(p for g in ("*.cpp", "*.hpp") for p in ADDONS.rglob(g)):
        text = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
        rel = path.relative_to(REPO)
        for m in re.finditer(r"\bclass\s+CfgCloudlets\s*\{", text):
            blocks += 1
            body = block(text, m.start())
            if body is None:
                continue
            line0 = text[: m.start()].count("\n") + 1
            if not re.search(r"\bclass\s+Default\s*;", body):
                problems.append(
                    f"{rel}:{line0}: CfgCloudlets does not forward-declare class Default;"
                )
            if re.search(r"\bclass\s+Default\s*\{", body):
                problems.append(
                    f"{rel}:{line0}: CfgCloudlets defines class Default with a body (shadows vanilla)"
                )
            for cm in CLASS_OPEN.finditer(body):
                name, base = cm.group(1), cm.group(3)
                if name == "Default":
                    continue
                classes += 1
                if base != "Default":
                    cl = body[: cm.start()].count("\n") + line0
                    problems.append(
                        f"{rel}:{cl}: class {name} does not inherit Default"
                    )
                inner = block(body, cm.start())
                if inner is None:
                    continue
                for fm in FIELD.finditer(inner):
                    f = fm.group(1)
                    if f not in VALID_FIELDS:
                        fl = (
                            body[: cm.start()].count("\n")
                            + inner[: fm.start()].count("\n")
                            + line0
                        )
                        problems.append(
                            f"{rel}:{fl}: class {name} field {f!r} is not a CfgCloudlets field"
                        )

    print(f"CfgCloudlets blocks: {blocks}; cloudlet classes: {classes}")
    if problems:
        print(f"\nSCHEMA PROBLEMS ({len(problems)}):")
        for p in problems[:40]:
            print("  " + p)
    else:
        print("every CfgCloudlets class is well formed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
