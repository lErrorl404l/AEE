#!/usr/bin/env python3
"""Cross-module reference validator (issue #204).

The nvgTitle / titleDisplay / ChromAberration bugs shared one root cause:
after the nvg->nightvision rename, references to RESOURCES and STATE
owned by OTHER modules kept the local QGVAR/GVAR form instead of the
cross-module QEGVAR/EGVAR.  They resolve to the wrong namespace silently
(always -1 / nil / not-found) and produce no error - the engine just
does nothing.

validate_cba_settings.py catches missionNamespace getVariable/setVariable
STATE, but has NO coverage of:
  - cutRsc / RscTitles resource references
  - uiNamespace state (onLoad assignments)
  - ppEffect handles stored via the ppEffectCreate loop
    (missionNamespace setVariable [_store, _handle] with _store passed
    as a QGVAR arg - the dynamic form a literal scan misses)

INVARIANT:
  A QGVAR/GVAR (own-module form) referenced in module X must be DECLARED
  in module X (as a ppEffect-store arg, setVariable, config resource, or
  RscTitles class).  If the same name is declared ONLY in a different
  module Y, module X must use the QEGVAR/EGVAR cross-module form - the
  own-module form is a scope bug that silently fails.

DECLARATION forms recognised per module:
  - ppEffectCreate loop: QGVAR(name) passed as the store arg
    (missionNamespace setVariable [_store, _handle])
  - missionNamespace setVariable [QGVAR(name), ...]
  - uiNamespace setVariable [QGVAR(name), ...]
  - config.cpp: class GVAR(name)
  - RscTitles.hpp (or any .hpp): class GVAR(name)

REFERENCE forms recognised:
  - getVariable [QGVAR(name), ...]  -> BUG if declared elsewhere
  - cutRsc [QGVAR(name), ...]       -> BUG if declared elsewhere
  - uiNamespace getVariable [QGVAR(name)...] -> BUG if declared elsewhere
  - ppEffectCreate loop store arg QGVAR(name) -> declaration (not a ref)

Exit code: 1 when any definite cross-module scope bug is found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"


def strip_comments(text: str) -> str:
    out = []
    i = 0
    in_str = False
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"' and (i == 0 or text[i - 1] != "\\"):
            in_str = not in_str
            out.append(c)
            i += 1
            continue
        if not in_str and c == "/" and i + 1 < n:
            if text[i + 1] == "/":
                while i < n and text[i] != "\n":
                    i += 1
                continue
            if text[i + 1] == "*":
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


def module_of(path: Path) -> str:
    parts = path.parts
    for i, p in enumerate(parts):
        if p == "addons":
            return parts[i + 1]
    return "?"


def _all_sqf() -> list[Path]:
    """All .sqf under every addon's functions tree - flat OR subfoldered
    (nightvision is flat; the six large modules are subfoldered).  The
    module is derived from the path, so the layout does not matter."""
    result = []
    for fdir in ADDONS.glob("*/functions"):
        for sqf in fdir.rglob("*.sqf"):
            result.append(sqf)
    return result


def scan_declarations() -> dict[str, set[str]]:
    """name -> set of modules where it is DECLARED."""
    declared: dict[str, set[str]] = {}

    def add(name: str, mod: str):
        declared.setdefault(name, set()).add(mod)

    # 1. ppEffectCreate loop store args (the dynamic setVariable form).
    #    ONLY names appearing as the third element of the effect tuples
    #    are declarations - NOT every QGVAR in the file (a file that
    #    happens to also have setVariable [_store, _handle] somewhere).
    for sqf in _all_sqf():
        text = strip_comments(sqf.read_text(encoding="utf-8"))
        mod = module_of(sqf)
        # match ["EffectType", priority, QGVAR(store)] tuples
        for m in re.finditer(
            r"\[\s*\"\w+\"\s*,\s*[\d\.]+\s*,\s*QGVAR\((\w+)\)\s*\]",
            text,
        ):
            add(m.group(1), mod)
    # 2. literal setVariable declarations (missionNamespace / uiNamespace)
    for sqf in _all_sqf():
        text = strip_comments(sqf.read_text(encoding="utf-8"))
        mod = module_of(sqf)
        for m in re.finditer(
            r"(?:missionNamespace|uiNamespace)\s+setVariable\s*\[QGVAR\((\w+)\)",
            text,
        ):
            add(m.group(1), mod)
    # 3. config.cpp class GVAR(name) / QGVAR(name)
    for cfg in ADDONS.glob("*/config.cpp"):
        text = strip_comments(cfg.read_text(encoding="utf-8"))
        mod = cfg.parent.name
        for m in re.finditer(r"class\s+GVAR\((\w+)\)|class\s+QGVAR\((\w+)\)", text):
            add(m.group(1) or m.group(2), mod)
    # 4. .hpp class GVAR(name) (RscTitles etc.) AND onLoad/uiNamespace
    #    assignments (e.g. RscTitles onLoad = QUOTE(uiNamespace GVAR(x) = ...))
    for hpp in ADDONS.glob("*/*.hpp"):
        text = strip_comments(hpp.read_text(encoding="utf-8"))
        mod = hpp.parent.name
        for m in re.finditer(
            r"class\s+GVAR\((\w+)\)|class\s+QGVAR\((\w+)\)|"
            r"uiNamespace\s+setVariable\s*\[GVAR\((\w+)\)|"
            r"uiNamespace\s+do\s*\{[^}]*GVAR\((\w+)\)\s*=",
            text,
        ):
            name = m.group(1) or m.group(2) or m.group(3) or m.group(4)
            if name:
                add(name, mod)
    # 5. initSettings declarations (QGVAR(name) as setting key)
    for inc in ADDONS.glob("*/initSettings.inc.sqf"):
        text = strip_comments(inc.read_text(encoding="utf-8"))
        mod = inc.parent.name
        for m in re.finditer(r"QGVAR\((\w+)\)", text):
            add(m.group(1), mod)
    # 6. Cross-module writes: setVariable [QEGVAR(M, name), ...] from any
    #    module declares (M, name).  Without this rule the fx module
    #    writing QEGVAR(optics,severeWeatherBlur) leaves optics' own
    #    QGVAR(severeWeatherBlur) read flagged as a false positive - the
    #    write INTO optics scope is exactly what makes it optics-owned.
    for sqf in _all_sqf():
        text = strip_comments(sqf.read_text(encoding="utf-8"))
        for m in re.finditer(
            r"(?:missionNamespace|uiNamespace)\s+setVariable\s*\[QEGVAR\((\w+),\s*(\w+)\)",
            text,
        ):
            add(m.group(2), m.group(1))
    return declared


def scan_references() -> dict[str, list[tuple[str, str, str]]]:
    """module -> list of (name, form, context)."""
    refs: dict[str, list[tuple[str, str, str]]] = {}

    def add_ref(mod: str, name: str, form: str, context: str):
        refs.setdefault(mod, []).append((name, form, context))

    for sqf in _all_sqf():
        text = strip_comments(sqf.read_text(encoding="utf-8"))
        mod = module_of(sqf)
        for m in re.finditer(r"getVariable\s*\[QGVAR\((\w+)\)", text):
            add_ref(mod, m.group(1), "QGVAR", "getVariable")
        for m in re.finditer(r"cutRsc\s*\[QGVAR\((\w+)\)", text):
            add_ref(mod, m.group(1), "QGVAR", "cutRsc")
        for m in re.finditer(r"uiNamespace\s+getVariable\s*\[QGVAR\((\w+)\)", text):
            add_ref(mod, m.group(1), "QGVAR", "uiNamespace")
    return refs


def refs_with_location() -> list[tuple[str, str, str, str, int]]:
    """(mod, name, form, context, line) for every QGVAR/QEGVAR read
    reference in every addon, in file order.  Forms: QGVAR (own-scope
    read) and QEGVAR (explicit cross-module read).

    The macro token is matched as a unit first (Q?E?GVAR(...) with the
    parens), then split on the inner comma.  Matching the paren as a
    unit is essential: `getVariable [QGVAR(x), false]` must NOT be read
    as a two-arg macro - the default value lives at array level, outside
    the parens."""
    out: list[tuple[str, str, str, str, int]] = []
    for sqf in _all_sqf():
        text = strip_comments(sqf.read_text(encoding="utf-8"))
        mod = module_of(sqf)
        for m in re.finditer(
            r"(getVariable\s*\[|cutRsc\s*\[)(Q?E?GVAR)\(([^)]*)\)",
            text,
        ):
            context = "cutRsc" if m.group(1).startswith("cutRsc") else "getVariable"
            form = m.group(2)
            inner = m.group(3)
            if form == "QEGVAR":
                mod_part, _, name = inner.partition(",")
                owner = mod_part.strip()
            else:
                owner, name = mod, inner
            line = text[: m.start()].count("\n") + 1
            out.append((owner, name.strip(), form, context, line))
    return out


def main() -> int:
    if "--report" in sys.argv:
        return report()
    declared = scan_declarations()
    refs = scan_references()
    bugs = []
    for mod, mod_refs in refs.items():
        for name, form, context in mod_refs:
            if form != "QGVAR":
                continue
            owners = declared.get(name, set())
            owners = {o for o in owners if o not in ("cba_main", "cba_xeh")}
            if owners and mod not in owners:
                bugs.append(
                    f"{mod}: QGVAR({name}) [{context}] but owned by {sorted(owners)}"
                )
    if bugs:
        seen = sorted(set(bugs))
        print(f"CROSS-MODULE SCOPE BUGS: {len(seen)}")
        for b in seen:
            print(f"  {b}")
        return 1
    print("cross-module reference check: clean")
    return 0


def report() -> int:
    """List every read reference found, classified.  Shows what the
    validator covers (and what it cannot see) so coverage gaps are
    visible instead of silent."""
    declared = scan_declarations()
    refs = refs_with_location()
    rows = []
    for owner, name, form, context, line in refs:
        if form == "QEGVAR":
            rows.append((owner, name, form, context, line, "valid-cross-module"))
        else:  # QGVAR own-scope read
            owners = {
                o for o in declared.get(name, set()) if o not in ("cba_main", "cba_xeh")
            }
            if owners and owner not in owners:
                rows.append((owner, name, form, context, line, "FLAGGED"))
            elif owners:
                rows.append((owner, name, form, context, line, "valid-shared"))
            else:
                rows.append((owner, name, form, context, line, "valid-self"))
    n_flagged = sum(1 for r in rows if r[5] == "FLAGGED")
    n_cross = sum(1 for r in rows if r[5] == "valid-cross-module")
    n_shared = sum(1 for r in rows if r[5] == "valid-shared")
    n_self = sum(1 for r in rows if r[5] == "valid-self")
    print(
        f"read references: {len(rows)}  "
        f"(flagged={n_flagged}, cross-module={n_cross}, "
        f"shared={n_shared}, self={n_self})"
    )
    for owner, name, form, context, line, status in rows:
        print(f"  {status:17} {owner:12} {name:28} {context:12} L{line}")
    return 1 if n_flagged else 0


if __name__ == "__main__":
    sys.exit(main())
