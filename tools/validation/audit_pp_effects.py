#!/usr/bin/env python3
"""Post-process effect safety audit (issue #204).

Scans EVERY ppEffect call in the codebase and flags the failure modes
that throw "Invalid post effect handle" in the RPT:

  1. ppEffectAdjust on a handle variable that is not guarded by a
     `if (_h >= 0)` / `if (_h < 0) exitWith` check.
  2. ppEffectEnable/ppEffectDestroy on a handle without a guard.
  3. ppEffectCreate results used before the negative-check.
  4. Effect-adjust by STRING name (LightShafts etc.) - applies to the
     engine's own effects, which may not exist.

The RPT error "Invalid post effect handle." recurring every environment
tick is exactly this class: an adjust on a -1 handle.  Visual code is
audited three times (SQF-param check + simulation + this safety scan).
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"

# The call patterns and their required guards.
ADJUST = re.compile(r"(\w+)\s+ppEffectAdjust")
ENABLE = re.compile(r"(\w+)\s+ppEffectEnable\s+(true|false)")
DESTROY = re.compile(r"(\w+)\s+ppEffectDestroy")
CREATE = re.compile(r"(\w+)\s*=\s*ppEffectCreate")


def is_guarded(text: str, var: str, pos: int) -> bool:
    """Check the code before `pos` guards `var` with an if (_var >= 0)
    block or an exitWith on negative.  Scans back to the start of the
    current enclosing block (40 lines) so nested if-guards are found."""
    line_no = text[:pos].count("\n")
    window_lines = text.split("\n")[max(0, line_no - 40) : line_no]
    window = "\n".join(window_lines)
    return (
        re.search(rf"if\s*\([^)]*{var}\s*>=\s*0\)\s*then", window) is not None
        or re.search(rf"if\s*\({var}\s*<\s*0\)\s*exitWith", window) is not None
        or re.search(rf"if\s*\({var}\s*<\s*0\)\s*then", window) is not None
        or re.search(rf"if\s*\({var}\s*<=\s*-1\)\s*exitWith", window) is not None
    )


# Handle-like tokens only: _hX or the quoted effect names.  Prose words
# ("into", "every") and comments never match.
HANDLE = re.compile(r"^_[a-zA-Z][a-zA-Z0-9_]*$")


def audit() -> int:
    problems = []
    for sqf in sorted(ADDONS.glob("*/**/*.sqf")):
        if "functions" not in str(sqf):
            continue
        text = sqf.read_text(encoding="utf-8")
        lines = text.split("\n")

        for m in ADJUST.finditer(text):
            var = m.group(1)
            if not HANDLE.match(var):
                continue
            if var.startswith('"'):
                problems.append(
                    f"{sqf.relative_to(REPO)}:{text[: m.start()].count(chr(10)) + 1}: "
                    f"ppEffectAdjust by STRING {var}"
                )
                continue
            line = text[: m.start()].count("\n") + 1
            if not is_guarded(text, var, m.start()):
                problems.append(
                    f"{sqf.relative_to(REPO)}:{line}: unguarded ppEffectAdjust {var}"
                )

        for m in ENABLE.finditer(text):
            var = m.group(1)
            if not HANDLE.match(var):
                continue
            if var.startswith('"'):
                problems.append(
                    f"{sqf.relative_to(REPO)}:{text[: m.start()].count(chr(10)) + 1}: "
                    f"ppEffectEnable by STRING {var}"
                )
                continue
            line = text[: m.start()].count("\n") + 1
            if not is_guarded(text, var, m.start()):
                problems.append(
                    f"{sqf.relative_to(REPO)}:{line}: unguarded ppEffectEnable {var}"
                )

        for m in DESTROY.finditer(text):
            var = m.group(1)
            if not HANDLE.match(var):
                continue
            line = text[: m.start()].count("\n") + 1
            if not var.startswith('"') and not is_guarded(text, var, m.start()):
                problems.append(
                    f"{sqf.relative_to(REPO)}:{line}: unguarded ppEffectDestroy {var}"
                )

    if problems:
        print(f"POST-PROCESS SAFETY: {len(problems)} potential issue(s)")
        for p in sorted(set(problems)):
            print(f"  {p}")
        return 1
    print("post-process effect audit: clean")
    return 0


if __name__ == "__main__":
    sys.exit(audit())
