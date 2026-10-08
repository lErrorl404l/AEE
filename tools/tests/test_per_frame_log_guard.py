#!/usr/bin/env python3
"""Structural contract: a per-frame handler must not log on every tick.

``CBA_fnc_addPerFrameHandler`` runs a handler every ``delay`` seconds (0 runs
every rendered frame).  A DEBUG or TRACE line emitted from inside a handler
with a delay below one second is a per-TICK cost, so its volume scales with
the frame rate and floods the RPT whenever the trace switch is on.

The five mobility loops did exactly this at 20 Hz: each built a
``format ["... %1 ms" ...]`` string and called ``diag_log`` every tick.  In the
operator's 104 s session that was 10,205 lines, 71 percent of all AEE debug
output, and the single largest block in a 16,027 line RPT.  The measured loop
cost was 0 to 1 ms, so the lines carried almost no signal.

The fix is to log nothing per tick and to report state from a SEPARATE 1 Hz
handler (mobility's ``fnc_logAirframeState`` is that line, and the CBA
BEGIN/END_COUNTER macros already expose the per-call cost on demand).  A 1 Hz
handler passes this test: one line a second is a diagnostic, not a flood.

This reads the SOURCE, because a mirror of a handler would prove nothing about
the handler.  Comments and string contents are blanked before every search, so
prose describing a per-tick log cannot satisfy the assertion.

Sites another worktree owns carry an allowlist reason.  Runs standalone (rc 0
on pass, rc 1 on an offending site) and through the unittest suite.
"""

import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADDONS = os.path.join(ROOT, "addons")

# A delay below this is a per-frame or high-rate handler.  1.0 and above is a
# state cadence and may log once a second.
PER_TICK_BELOW = 1.0

# Sites that cannot be fixed here, keyed by path relative to the repository
# root, each with the reason and the owner.
ALLOWLIST = {
    "addons/optics/XEH_postInit.sqf": (
        "optics perception worktree owns this file; the 0.1 s sensor PFH trace "
        "is tracked there"
    ),
    "addons/optics/functions/hud/fnc_hudUpdate.sqf": (
        "optics perception worktree owns this file; the 0.1 s HUD trace is "
        "tracked there"
    ),
    "addons/optics/functions/hud/fnc_trackerUpdate.sqf": (
        "optics perception worktree owns this file; the 0.1 s tracker trace is "
        "tracked there"
    ),
    "addons/optics/functions/perception/fnc_perceptionUpdate.sqf": (
        "optics perception worktree owns this file; the 0.5 s perception trace "
        "is tracked there"
    ),
    "addons/optics/functions/vision/fnc_dtvHostTick.sqf": (
        "optics perception worktree owns this file; the 0.1 s DTV host trace is "
        "tracked there"
    ),
}

LOG_RE = re.compile(r"AEE_LOG_(DEBUG|TRACE)\s*\(")
CALL_MARKER = "CBA_fnc_addPerFrameHandler"
FUNC_RE = re.compile(r"(?:E)?FUNC\s*\(\s*([^)]*)\)")


def strip_code(text):
    """Blank comments and string contents, preserving offsets and newlines."""
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
            out[i] = " "
            i += 1
            while i < n:
                if text[i] == "\\":
                    out[i] = " "
                    if i + 1 < n:
                        out[i + 1] = " "
                    i += 2
                    continue
                if text[i] == '"':
                    out[i] = " "
                    i += 1
                    break
                if text[i] != "\n":
                    out[i] = " "
                i += 1
        else:
            i += 1
    return "".join(out)


def _arg_array(code, call_start):
    """Return the text inside the argument array that precedes ``call_start``.

    ``code`` must already be comment- and string-stripped.  Returns None when
    the call is not preceded by a bracketed array.
    """
    i = call_start - 1
    while i >= 0 and code[i] in " \t\r\n":
        i -= 1
    # "call" sits between the argument array and the marker name.
    if i >= 3 and code[i - 3 : i + 1] == "call":
        i -= 4
    else:
        return None
    while i >= 0 and code[i] in " \t\r\n":
        i -= 1
    if i < 0 or code[i] != "]":
        return None
    close = i
    depth = 0
    j = close
    while j >= 0:
        if code[j] == "]":
            depth += 1
        elif code[j] == "[":
            depth -= 1
            if depth == 0:
                return code[j + 1 : close]
        j -= 1
    return None


def _split_top_level(array):
    """Split on commas at bracket/brace/paren depth zero."""
    parts = []
    depth = 0
    start = 0
    for i, ch in enumerate(array):
        if ch in "[{(":
            depth += 1
        elif ch in "]})":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(array[start:i])
            start = i + 1
    parts.append(array[start:])
    return parts


def _handler_body(addon, registration_file, handler_expr):
    """Return (body_text, body_path) or (None, None) when unresolved.

    An inline ``{ ... }`` block is the body itself.  A ``FUNC``/``EFUNC`` name
    resolves to the function file; the whole file is the body because it is
    the unit the handler runs.
    """
    expr = handler_expr.strip()
    if expr.startswith("{"):
        # The block runs to the end of the array field; the array split keeps
        # it intact, so the body is the block text.
        return expr, None
    match = FUNC_RE.match(expr)
    if not match:
        return None, None
    names = [p.strip() for p in match.group(1).split(",")]
    if expr.startswith("EFUNC"):
        fn = names[-1] if len(names) > 1 else names[0]
    else:
        fn = names[0]
    base = os.path.join(ADDONS, addon, "functions")
    hits = []
    for dirpath, _dirs, files in os.walk(base):
        for name in files:
            if name == "fnc_%s.sqf" % fn:
                hits.append(os.path.join(dirpath, name))
    if not hits:
        return None, None
    path = sorted(hits)[0]
    with open(path, encoding="utf-8") as fh:
        return strip_code(fh.read()), path


def scan():
    failures = []
    for dirpath, _dirs, files in os.walk(ADDONS):
        for name in files:
            if not name.endswith(".sqf"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            addon = os.path.relpath(dirpath, ADDONS).split(os.sep)[0]
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
            code = strip_code(raw)
            for found in re.finditer(re.escape(CALL_MARKER), code):
                array = _arg_array(code, found.start())
                if array is None:
                    continue
                parts = _split_top_level(array)
                if len(parts) < 2:
                    continue
                interval_text = parts[1].strip()
                try:
                    interval = float(interval_text)
                except ValueError:
                    # A named constant or variable delay: not statically
                    # knowable, so it is out of scope for this contract.
                    continue
                if interval >= PER_TICK_BELOW:
                    continue
                body, body_path = _handler_body(addon, rel, parts[0])
                if body is None:
                    continue
                for log in LOG_RE.finditer(body):
                    target = rel
                    if body_path is not None:
                        target = os.path.relpath(body_path, ROOT).replace(os.sep, "/")
                    if target in ALLOWLIST:
                        break
                    line = body.count("\n", 0, log.start()) + 1
                    failures.append(
                        "%s:%d a handler registered with delay %s emits "
                        "AEE_LOG_%s every tick; report it from a >= 1 s handler"
                        % (target, line, interval_text, log.group(1))
                    )
                    break
    return failures


def main():
    failures = scan()
    if not failures:
        print("test_per_frame_log_guard: PASS (no per-tick handler logs)")
        return 0
    print("test_per_frame_log_guard: FAIL")
    for failure in failures:
        print("  " + failure)
    print(
        "%d per-tick handler(s) log every tick; move the line to a >= 1 s "
        "handler or guard it off the tick" % len(failures)
    )
    return 1


class TestPerFrameLogGuard(unittest.TestCase):
    """The standalone scan, runnable through the unittest suite."""

    def test_no_per_tick_handler_logs(self):
        self.assertEqual(scan(), [])


if __name__ == "__main__":
    sys.exit(main())
