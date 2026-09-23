#!/usr/bin/env python3
"""Find and fix the no-op current-unit guard.

`CBA_fnc_currentUnit` is, in the pinned CBA 3.19.0:

    missionNamespace getVariable ["bis_fnc_moduleRemoteControl_unit", player]

That ALWAYS returns an object. On a dedicated server it is objNull, never
nil. So a guard written `if (!isNil "_player") then {...}` tests nothing
and the body always runs. Verified from the shipped PBO text.

The correct form, already used across this codebase, is:

    if (!isNil "_unit" && {!isNull _unit}) then { ... }

This tool reports the class, and with --apply rewrites the simple cases.

Run:
  python3 tools/validation/fix_current_unit_guard.py           # report
  python3 tools/validation/fix_current_unit_guard.py --apply   # rewrite
"""

import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).parents[2]
ADDONS = REPO / "addons"

ASSIGN = re.compile(r"private (_\w+)\s*=\s*call CBA_fnc_currentUnit")
GUARD = re.compile(
    r'if \(!?isNil\s+"?(?P<var>_?\w+)"?\)\s*then\s*\{(?P<body>[^}]*)\};?'
)


def scan():
    """Every site whose only guard on the unit is isNil."""
    found = []
    for root, dirs, files in os.walk(ADDONS):
        if "compat_" in root:
            continue
        for name in files:
            if not name.endswith(".sqf"):
                continue
            path = Path(root) / name
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in ASSIGN.finditer(text):
                var = match.group(1)
                # The guard can sit well below the assignment, after a
                # comment block. 900 characters covers the widest real case.
                window = text[match.end() : match.end() + 900]
                if not re.search(rf'isNil\s+"?{re.escape(var)}"?', window):
                    continue
                # a null test already covers it. `!alive` also covers it:
                # `alive objNull` is false, so `isNil _x || !alive _x`
                # exits correctly on a dedicated server.
                if re.search(
                    rf'isNull\s+"?{re.escape(var)}"?|!?alive\s+{re.escape(var)}\b',
                    window,
                ):
                    continue
                found.append((path, var))
    return found


def apply_fixes():
    """Rewrite the one-line guard form to the null-aware form."""
    changed = []
    for root, dirs, files in os.walk(ADDONS):
        if "compat_" in root:
            continue
        for name in files:
            if not name.endswith(".sqf"):
                continue
            path = Path(root) / name
            text = path.read_text(encoding="utf-8", errors="replace")
            original = text

            # if (!isNil "_x") then { <body> };   ->   if (!isNil "_x" && {!isNull _x}) then { <body> };
            def repl(match):
                var = match.group("var")
                body = match.group("body")
                return f'if (!isNil "{var}" && {{!isNull {var}}}) then {{{body}}};'

            text = re.sub(
                r'if \(!isNil\s+"(_\w+)"\)\s*then\s*\{([^}]*)\};?', repl, text
            )
            if text != original:
                path.write_text(text, encoding="utf-8")
                changed.append(path)
    return changed


def main():
    if "--apply" in sys.argv:
        changed = apply_fixes()
        print(f"rewrote {len(changed)} files")
        for p in changed:
            print(f"  {p.relative_to(REPO)}")
        remaining = scan()
        print(f"remaining no-op guards: {len(remaining)}")
        for p, v in remaining:
            print(f"  {p.relative_to(REPO)} ({v})")
        return 1 if remaining else 0

    found = scan()
    print(f"no-op current-unit guards: {len(found)}")
    for p, v in found:
        print(f"  {p.relative_to(REPO)} ({v})")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
