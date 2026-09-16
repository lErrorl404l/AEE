#!/usr/bin/env python3
"""Cross-reference CBA settings and AEE namespace variables.

The mod has no compiler check for the data-wiring contract: an addon can
read a variable no addon writes, or read it with the wrong addon prefix.
Both were real defects (issues #64, #65).  This script closes that gap.

It scans the source and reports four finding classes:

  1. WRONG PREFIX  - read as aee_X_n, but only aee_Y_n (Y != X) is
                     produced.  The reader silently gets its default.
  2. DEAD READ     - read as aee_X_n, nothing anywhere produces leaf n.
  3. DEAD SETTING  - declared with CBA_fnc_addSetting, never read.
  4. ORPHAN WRITE  - written, never read.

Macros resolve against the owning addon: GVAR(x) in addons/foo is
aee_foo_x; EGVAR(bar,x) is aee_bar_x.  A name passed as a bare macro
argument (not the first argument of getVariable/setVariable) counts as
produced, because helpers write it under that name.  Only aee_-prefixed
names are checked, so external mod variables (ACE, KAT) are ignored.

Run:  python3 tools/validation/validate_cba_settings.py [--strict]
Exit: 0 when no WRONG PREFIX and no DEAD READ, 1 otherwise.  --strict
      also fails on dead settings and orphan writes.
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ADDONS = REPO_ROOT / "addons"
TESTS = REPO_ROOT / "tests"
ALLOWLIST = Path(__file__).resolve().parent / "cba_settings_allowlist.txt"
ANNEX_C = REPO_ROOT / "docs" / "wiki" / "annexes" / "annex-c-variable-reference.qmd"
PREFIX = "aee"

_CALL = re.compile(
    r"(getVariable|setVariable)\s*\[\s*"
    r'(?:"(?P<lit>' + PREFIX + r'_\w+)"'
    r"|(?P<macro>(?:Q?GVAR|Q?EGVAR)\([^)]*\)))"
)
_MACRO = re.compile(r"\b(?:Q?GVAR|Q?EGVAR)\([^)]*\)")
_MACRO_NAME = re.compile(r"\bQ?EGVAR\(([^,)]+),([^)]+)\)|\bQ?GVAR\(([^)]+)\)")
_DECL = re.compile(r"\bQGVAR\((\w+)\)")
_LINE_COMMENT = re.compile(r"//[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def strip_comments(text):
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def addon_of(path):
    """addons/<addon>/... -> <addon>"""
    parts = path.relative_to(ADDONS).parts
    return parts[0] if len(parts) > 1 else ""


def resolve(macro_body, addon):
    """Expand a macro body to a full aee_ variable name.

    macro_body is the text inside the parentheses: "name" for GVAR/QGVAR,
    "addon,name" for EGVAR/QEGVAR.
    """
    if "," in macro_body:
        owner, name = (s.strip() for s in macro_body.split(",", 1))
        return f"{PREFIX}_{owner}_{name}"
    return f"{PREFIX}_{addon}_{macro_body.strip()}"


def macro_names(text, addon):
    """Every macro occurrence in the text, as resolved names."""
    for owner, name, gvar in _MACRO_NAME.findall(text):
        yield resolve(f"{owner},{name}" if owner else gvar, addon)


def leaf(name):
    """aee_addon_leaf -> leaf (first underscore run after the prefix+addon)."""
    return name.split("_", 2)[-1]


def scan():
    declared = {}  # name -> declaring file
    reads = {}  # name -> [files]
    writes = {}  # name -> [files]

    for sqf in sorted(ADDONS.rglob("*.sqf")):
        addon = addon_of(sqf)
        text = strip_comments(sqf.read_text(encoding="utf-8", errors="replace"))
        rel = str(sqf.relative_to(REPO_ROOT))

        if sqf.name == "initSettings.inc.sqf":
            for name in _DECL.findall(text):
                declared[f"{PREFIX}_{addon}_{name}"] = rel

        # Direct getVariable/setVariable calls.
        for kind, lit, macro in _CALL.findall(text):
            name = lit if lit else resolve(macro[macro.index("(") + 1 : -1], addon)
            bucket = reads if kind == "getVariable" else writes
            bucket.setdefault(name, []).append(rel)

        # Bare-form macros (not the first argument of get/setVariable):
        # an assignment like "GVAR(x) = ..." writes; a value use like
        # "[GVAR(x)] call" or "isNil QGVAR(x)" reads.  Separate the two
        # so bare-written handles (PFH ids) are not false-flagged.
        # initSettings declarations are not uses: skip the file entirely.
        is_decl_file = sqf.name == "initSettings.inc.sqf"
        for match in _MACRO.finditer(text):
            if is_decl_file:
                continue
            before = text[max(0, match.start() - 32) : match.start()]
            if re.search(r"(?:get|set)Variable\s*\[\s*$", before):
                continue
            after = text[match.end() : match.end() + 3]
            name = resolve(match.group()[match.group().index("(") + 1 : -1], addon)
            if re.match(r"\s*=", after):
                writes.setdefault(name, []).append(rel)
            else:
                reads.setdefault(name, []).append(rel)

    return declared, reads, writes


def scan_tests():
    """Reads/writes in the docker test missions.

    The missions seed state and read computed output with literal variable
    names.  A read that no addon produces and the test does not seed is a
    stale test (the aee_mobility_currentWaterLevel class fixed in #83).
    """
    test_reads = {}
    test_writes = {}
    for sqf in sorted(TESTS.rglob("*.sqf")):
        text = strip_comments(sqf.read_text(encoding="utf-8", errors="replace"))
        rel = str(sqf.relative_to(REPO_ROOT))
        for kind, lit, macro in _CALL.findall(text):
            if not lit:
                continue  # tests use literal names only
            if "_fnc_" in lit:
                continue  # function handle lookups, not data variables
            bucket = test_reads if kind == "getVariable" else test_writes
            bucket.setdefault(lit, []).append(rel)
    return test_reads, test_writes


def load_allowlist():
    """Read name -> reason for intentional dead reads."""
    allowed = {}
    if not ALLOWLIST.exists():
        return allowed
    for line in ALLOWLIST.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            name, _, reason = line.partition(" ")
            allowed[name] = reason.strip()
    return allowed


def main():
    strict = "--strict" in sys.argv
    declared, reads, writes = scan()
    test_reads, test_writes = scan_tests()
    allowed = load_allowlist()

    # A produced name containing %1 is a format template: the real variables
    # are composed at run time (e.g. format [QGVAR(ppHandle_%1), _name]).
    # Any read whose name matches a template prefix is satisfied by it.
    templates = [n for n in set(reads) | set(writes) if "%1" in n]
    dynamic = [t[: t.index("%1")] for t in templates]

    def is_produced(name):
        return (
            name in declared
            or name in writes
            or any(name.startswith(d) for d in dynamic)
        )

    produced = set(declared) | set(writes)
    by_leaf = {}
    for name in produced:
        by_leaf.setdefault(leaf(name), set()).add(name)

    wrong_prefix = []
    dead_read = []
    for name in sorted(reads):
        if is_produced(name):
            continue
        alternatives = by_leaf.get(leaf(name), set()) - {name}
        if alternatives:
            wrong_prefix.append((name, sorted(alternatives), reads[name]))
        else:
            dead_read.append((name, reads[name]))

    # Test mission reads must resolve against addon-produced state OR the
    # test's own seeds.  A read that is neither is a stale test assertion
    # (the aee_mobility_currentWaterLevel class: renamed producer, old test).
    stale_test = sorted(
        n for n in test_reads if not is_produced(n) and n not in test_writes
    )

    dead_setting = sorted(n for n in declared if n not in reads)
    orphan = sorted(
        n for n in writes if n not in reads and n not in declared and "%1" not in n
    )

    # Every orphan write must be documented in Annex C.  The annex is the
    # contract: a write with no reader is either API (documented) or dead.
    annex_doc = ANNEX_C.read_text(encoding="utf-8")
    undocumented = [n for n in orphan if f"`{n}`" not in annex_doc]

    allowed_hit = [n for n, _ in dead_read if n in allowed]
    dead_read = [(n, r) for n, r in dead_read if n not in allowed]

    for name, alts, readers in wrong_prefix:
        print(f"WRONG PREFIX  {name}")
        print(f"              produced as {', '.join(alts)}")
        for f in sorted(set(readers)):
            print(f"              read by {f}")

    for name, readers in dead_read:
        print(f"DEAD READ     {name}")
        for f in sorted(set(readers)):
            print(f"              read by {f}")

    for name in dead_setting:
        print(f"DEAD SETTING  {name}  (declared in {declared[name]})")

    for name in stale_test:
        print(f"STALE TEST    {name}")
        for f in sorted(set(test_reads[name])):
            print(f"              read by {f} (no producer in addons, not a test seed)")

    for name in orphan:
        print(f"ORPHAN WRITE  {name}  (written in {writes[name][0]})")

    for name in sorted(allowed_hit):
        print(f"ALLOWED       {name}  ({allowed[name]})")

    for name in undocumented:
        print(f"UNDOCUMENTED  {name}  (write with no reader; add to Annex C or delete)")

    print(
        f"\n{len(declared)} settings, {len(reads)} read names, "
        f"{len(writes)} produced names"
    )
    print(
        f"{len(wrong_prefix)} wrong prefix, {len(dead_read)} dead reads, "
        f"{len(dead_setting)} dead settings, {len(orphan)} orphan writes, "
        f"{len(allowed_hit)} allowed, {len(undocumented)} undocumented, "
        f"{len(stale_test)} stale test reads"
    )

    if (
        wrong_prefix
        or dead_read
        or undocumented
        or stale_test
        or (strict and (dead_setting or orphan))
    ):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
