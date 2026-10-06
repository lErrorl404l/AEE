#!/usr/bin/env python3
"""Source contract: expensive AEE debug messages must be trace-guarded.

The AEE_LOG_DEBUG and AEE_LOG_TRACE macros guard the diag_log write, but a
caller that builds the message in a statement of its own (the
``private _xMsg = format [...]; AEE_LOG_DEBUG(_xMsg);`` pattern) evaluates
that build on every tick, whether or not the debug switch is on.  The build
must sit behind an ``if (AEE_TRACE_ON) then { ... };`` guard, or the site
must appear on the inline allowlist below with a reason.

A message expression is expensive when it invokes a script function or a
config query.  The markers match the audit in the observability plan:
``call FUNC(``, ``call EFUNC(``, ``getVariable``, ``configFile`` and the
per-tick ``diag_tickTime`` clock read.

Runs standalone: rc 0 on pass, rc 1 when an unguarded site is found.
"""

import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADDONS = os.path.join(ROOT, "addons")

EXPENSIVE = (
    "call FUNC(",
    "call EFUNC(",
    "getVariable",
    "configFile",
    "diag_tickTime",
)

# Sites that cannot carry a local guard, with a reason.  Keyed by path
# relative to the repository root.
ALLOWLIST = {
    "addons/optics/XEH_postInit.sqf": (
        "optics perception worktree owns this file; the guard is tracked there"
    ),
    "addons/optics/functions/vision/fnc_dtvHostTick.sqf": (
        "optics perception worktree owns this file; the guard is tracked there"
    ),
    "addons/optics/functions/vision/fnc_managePostProcess.sqf": (
        "optics perception worktree owns this file; the guard is tracked there"
    ),
}

LOG_RE = re.compile(r"AEE_LOG_(DEBUG|TRACE)\s*\(")
ASSIGN_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def strip_comments(text):
    """Blank out comments while preserving line count and offsets."""
    out = list(text)
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        elif text[i] == '"':
            # keep strings intact; their content is data, but the macros use
            # no marker inside a string in this addon set, so leave them.
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
        else:
            i += 1
    return "".join(out)


def balanced(text, start):
    """Return (argument, end) for the parenthesised call at ``start``+1."""
    i = start
    depth = 1
    instr = False
    esc = False
    n = len(text)
    while i < n and depth > 0:
        c = text[i]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
        else:
            if c == '"':
                instr = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
        i += 1
    return text[start : i - 1], i


def assignment_statement(lines, end_line, var):
    """Return (start_line, text) for the nearest preceding assign to var."""
    for k in range(end_line, max(-1, end_line - 40), -1):
        if k >= len(lines):
            continue
        m = ASSIGN_RE.search(lines[k])
        if not m or m.group(1) != var:
            continue
        chunk = []
        depth = 0
        instr = False
        esc = False
        for j in range(k, min(len(lines), k + 25)):
            line = lines[j]
            chunk.append(line)
            for c in line:
                if instr:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        instr = False
                else:
                    if c == '"':
                        instr = True
                    elif c in "[(":
                        depth += 1
                    elif c in "])":
                        depth -= 1
            if depth <= 0 and j > k:
                break
            if depth <= 0 and line.rstrip().endswith(";"):
                break
        return k, "\n".join(chunk)
    return None, None


def guarded(lines, builder_start, log_line):
    lo = builder_start if builder_start is not None else log_line
    for k in range(max(0, lo - 2), log_line + 1):
        if "AEE_TRACE_ON" in lines[k]:
            return True
    return False


def scan():
    failures = []
    for dirpath, _dirs, files in os.walk(ADDONS):
        for name in files:
            if not name.endswith(".sqf"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            raw = open(path, encoding="utf-8").read()
            text = strip_comments(raw)
            lines = text.split("\n")
            for m in LOG_RE.finditer(text):
                line_no = text.count("\n", 0, m.start())
                arg, _end = balanced(text, m.end())
                arg = arg.strip()
                if not arg:
                    continue
                if IDENT_RE.match(arg):
                    bstart, builder = assignment_statement(lines, line_no - 1, arg)
                    expr = (builder or "") + "\n" + arg
                else:
                    bstart, expr = line_no, arg
                hits = [p for p in EXPENSIVE if p in expr]
                if not hits:
                    continue
                if guarded(lines, bstart, line_no):
                    continue
                if rel in ALLOWLIST:
                    continue
                failures.append((rel, line_no + 1, arg, hits))
    return failures


def main():
    failures = scan()
    if not failures:
        print("test_debug_guard: PASS (every expensive debug message is guarded)")
        return 0
    print("test_debug_guard: FAIL")
    for rel, line, arg, hits in failures:
        print(
            f"  {rel}:{line} unguarded AEE_LOG_DEBUG/TRACE argument {arg!r} uses {hits}"
        )
    print(
        f"{len(failures)} unguarded site(s); wrap in `if (AEE_TRACE_ON) then {{ ... }};`"
    )
    return 1


class TestDebugGuard(unittest.TestCase):
    """The standalone scan, runnable through the unittest suite."""

    def test_every_expensive_debug_message_is_guarded(self):
        self.assertEqual(main(), 0)


if __name__ == "__main__":
    sys.exit(main())
