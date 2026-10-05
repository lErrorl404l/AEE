#!/usr/bin/env python3
"""Fail when a getVariable/setVariable name is the UNQUOTED macro form.

`EGVAR(component,name)` expands to the bare token `aee_component_name`, and
the one-part `GVAR(name)` expands to the bare token `aee_component_name` too.
SQF reads a bare token as a variable reference, so

    missionNamespace getVariable [EGVAR(core,currentTemperature), 15]
    missionNamespace getVariable [GVAR(manifest), []]

pass a variable whose value is nil, not the String name. The read returns
the default silently, or raises "Type HashMap, expected String" when the
default is not a String. The live incident: 125 "Undefined variable
aee_wildlife_manifest" errors in a docker run.

The correct forms are QEGVAR and QGVAR, which yield the quoted name:

    missionNamespace getVariable [QEGVAR(core,currentTemperature), 15]
    missionNamespace getVariable [QGVAR(manifest), []]

The EGVAR form has caused two incidents: the first was 72 sites across 52
files, found only in a client RPT; the second was a single site reintroduced
while fixing the first. The GVAR blind spot was the third: this lint saw only
EGVAR, so the wildlife addon shipped unquoted GVAR keys to a server. A rule
stated in prose did not prevent the recurrence, so it is a lint.

Run:  python3 tools/validation/check_macro_quoting.py
Exit 0 when clean, 1 on any unquoted name.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).parents[2]
ADDONS = REPO / "addons"

# getVariable [ EGVAR(...) ...  or  setVariable [ EGVAR(...)
# QEGVAR is the correct form and must not match.
BAD = re.compile(r"(?:get|set)Variable\s*\[\s*EGVAR\(")


def scan():
    hits = []
    for path in sorted(ADDONS.rglob("*.sqf")):
        if "compat_" in str(path):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in BAD.finditer(text):
            line = text[: match.start()].count("\n") + 1
            hits.append((path, line, text.splitlines()[line - 1].strip()))
    return hits


def main():
    hits = scan()
    if hits:
        print(f"unquoted EGVAR in a get/setVariable name: {len(hits)}")
        for path, line, text in hits:
            print(f"  {path.relative_to(REPO)}:{line}")
            print(f"    {text}")
        print("Use QEGVAR: EGVAR yields a bare token, QEGVAR yields the String name.")
        return 1
    print("macro quoting: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
