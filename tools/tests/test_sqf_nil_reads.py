#!/usr/bin/env python3
"""Source contract: a nil-valued private must not be read before an isNil guard.

Why this test exists
--------------------
In SQF, assigning `nil` to a private variable leaves the variable UNDEFINED
rather than binding it to a nil value.  A later read of that variable, or a
type check on it, then raises "Undefined variable _x" at runtime.  The live
defect this locks: fnc_wildlifeTick read the normally-unset force-night hook
with a nil default,

    private _forceNight = missionNamespace getVariable ["aee_wildlife_forceNight", nil];
    if (_forceNight isEqualType false) then { ... };

so the guard on the next line threw on every client tick.  The engine RPT
showed 384 such errors in one short run, and the Python suite could not see
it because the failure is an SQF runtime semantic, not a Python value.

The safe patterns, both accepted here:
  1. a non-nil default:  getVariable [key, 0]  (no nil is ever bound)
  2. an isNil guard before any read:  if (isNil "_x") then { ... }

The test scans every TRACKED SQF file in the repository, strips comments,
finds each `private _v = <expression containing nil>`, and fails if `_v` is
read before an `isNil "_v"` guard.  It carries positive and negative controls
so a broken matcher cannot pass vacuously.

The scan is limited to tracked source.  An untracked clone of another mod
dropped in the repo root (for example a `cba/` checkout left by a research
study) is not AEE's source, and its own defensive style must not be judged by
this gate.  Git tracking is the boundary: only what AEE ships is scanned.
"""

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Directories that hold vendored, generated or historical copies rather than
# the shipped source.
SKIP_DIRS = {".git", ".hemttout", "releases", ".omo", "node_modules"}

DECL_RE = re.compile(r"\bprivate\s+(_[A-Za-z0-9_]+)\s*=")
NIL_RE = re.compile(r"(?<![A-Za-z0-9_])nil(?![A-Za-z0-9_])")
GUARD_RE = re.compile(r"isNil\s*\"(_[A-Za-z0-9_]+)\"")
VAR_TPL = r"(?<![A-Za-z0-9_]){v}(?![A-Za-z0-9_])"


def _strip_block_comments(text: str) -> str:
    # Blank the comment body but keep every newline, so line numbers and
    # offsets stay aligned with the source file.
    def keep_lines(m: "re.Match[str]") -> str:
        return "".join("\n" if c == "\n" else " " for c in m.group(0))

    return re.sub(r"/\*.*?\*/", keep_lines, text, flags=re.S)


def _strip_line_comments(text: str) -> str:
    out = []
    for line in text.split("\n"):
        cut = -1
        in_str = False
        i = 0
        while i < len(line):
            c = line[i]
            if c == '"' and (i == 0 or line[i - 1] != "\\"):
                in_str = not in_str
            elif not in_str and c == "/" and i + 1 < len(line) and line[i + 1] == "/":
                cut = i
                break
            i += 1
        out.append(line if cut < 0 else line[:cut])
    return "\n".join(out)


def _mask_strings(text: str) -> str:
    """Blank the inside of string literals, keeping quotes and offsets.

    A variable token inside a string is data, not a read (for example an
    `isNil "_x"` guard).  Masking keeps the offsets aligned with the source
    so line numbers stay correct.
    """
    out = list(text)
    in_str = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == '"' and (i == 0 or text[i - 1] != "\\"):
            in_str = not in_str
        elif in_str:
            out[i] = " "
        i += 1
    return "".join(out)


def _stmt_end(text: str, start: int) -> int:
    """Return the offset of the `;` that ends the statement at `start`.

    Tracks bracket depth so a `;` inside `[ ... ]` does not terminate early.
    Falls back to the end of the line when the statement is unterminated.
    """
    depth = 0
    i = start
    limit = min(len(text), start + 2000)
    while i < limit:
        c = text[i]
        if c in "[(":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == ";" and depth <= 0:
            return i
        elif c == "\n" and depth <= 0:
            return i
        i += 1
    return limit


def find_nil_reads(text: str) -> list[tuple[int, str, str, str]]:
    """Return (line, var, decl_line, read_line) for each dangerous read."""
    source = _strip_line_comments(_strip_block_comments(text))
    masked = _mask_strings(source)

    guards: dict[str, list[int]] = {}
    for m in GUARD_RE.finditer(source):
        guards.setdefault(m.group(1), []).append(m.start())

    findings: list[tuple[int, str, str, str]] = []
    lines = source.split("\n")

    def line_of(offset: int) -> int:
        return source.count("\n", 0, offset) + 1

    for decl in DECL_RE.finditer(masked):
        var = decl.group(1)
        end = _stmt_end(masked, decl.end())
        expr = source[decl.end() : end]
        if not NIL_RE.search(_mask_strings(expr)):
            continue
        var_re = re.compile(VAR_TPL.format(v=re.escape(var)))
        guard_offsets = guards.get(var, [])
        for use in var_re.finditer(masked, end):
            pos = use.start()
            # A guard at or before this use makes every later read safe.
            if any(g < pos for g in guard_offsets):
                break
            # A write is not a read: `_v = ...` assigns, it does not throw.
            after = masked[use.end() : use.end() + 4]
            if re.match(r"\s*=(?!=)", after):
                continue
            findings.append(
                (
                    line_of(decl.start()),
                    var,
                    lines[line_of(decl.start()) - 1].strip(),
                    lines[line_of(pos) - 1].strip(),
                )
            )
            break
    return findings


def _git_tracked_sqf() -> set[str] | None:
    """Return the tracked *.sqf paths (repo-relative, POSIX), or None.

    None means git could not run, so the caller falls back to a filesystem
    walk.  An untracked clone placed in the repo root is absent from the
    tracked set and is therefore never scanned.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "-z", "--", "*.sqf"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return {p for p in out.split("\0") if p}


def _scannable(rel: str, tracked: set[str]) -> bool:
    """True when a repo-relative *.sqf path is tracked and not in SKIP_DIRS."""
    if rel not in tracked:
        return False
    return not any(part in SKIP_DIRS for part in Path(rel).parts)


def _sqf_files():
    tracked = _git_tracked_sqf()
    if tracked is None:
        for path in sorted(REPO.rglob("*.sqf")):
            if any(part in SKIP_DIRS for part in path.relative_to(REPO).parts):
                continue
            yield path
        return
    for rel in sorted(tracked):
        if _scannable(rel, tracked):
            yield REPO / rel


class TestNilDefaultedPrivateIsGuarded(unittest.TestCase):
    """No shipped SQF may read a nil-defaulted private before an isNil guard."""

    def test_no_nil_defaulted_private_is_read_before_an_isnil_guard(self):
        failures = []
        for path in _sqf_files():
            for line, var, decl, use in find_nil_reads(
                path.read_text(errors="replace")
            ):
                failures.append(
                    f"{path.relative_to(REPO)}:{line} {var}\n    {decl}\n    {use}"
                )
        if failures:
            self.fail(
                "nil default assigned to an SQF private that is read before an "
                'isNil guard; use a non-nil default (for example 0 or "") or add '
                'if (isNil "_x") then { ... } before any read:\n' + "\n".join(failures)
            )


class TestDetectorControls(unittest.TestCase):
    """Positive and negative controls: the matcher is not passing vacuously."""

    def test_untracked_foreign_clone_is_not_scanned(self):
        # A tracked AEE file is scannable; an untracked foreign clone in the
        # repo root (the cba/ incident) is not, because it is not in the
        # tracked set.
        tracked = {"addons/core/functions/fnc_ok.sqf"}
        self.assertTrue(_scannable("addons/core/functions/fnc_ok.sqf", tracked))
        self.assertFalse(_scannable("cba/addons/optics/fnc_currentOptic.sqf", tracked))
        self.assertFalse(_scannable("cba/addons/settings/fnc_priority.sqf", tracked))

    def test_skip_dirs_remain_excluded(self):
        tracked = {".hemttout/build/generated.sqf", "releases/legacy.sqf"}
        self.assertFalse(_scannable(".hemttout/build/generated.sqf", tracked))
        self.assertFalse(_scannable("releases/legacy.sqf", tracked))

    def test_the_live_defect_shape_is_detected(self):
        bad = (
            "private _forceNight = missionNamespace getVariable "
            '["aee_wildlife_forceNight", nil];\n'
            "if (_forceNight isEqualType false) then { _isNight = _forceNight; };\n"
        )
        self.assertEqual(len(find_nil_reads(bad)), 1)

    def test_a_non_nil_default_is_clean(self):
        good = (
            "private _forceNight = missionNamespace getVariable "
            '["aee_wildlife_forceNight", 0];\n'
            "if (_forceNight isEqualType false) then { _isNight = _forceNight; };\n"
        )
        self.assertEqual(find_nil_reads(good), [])

    def test_an_isnil_guard_before_the_read_is_clean(self):
        good = (
            'private _x = missionNamespace getVariable ["k", nil];\n'
            'if (isNil "_x") then { _x = 5; };\n'
            "private _y = _x + 1;\n"
        )
        self.assertEqual(find_nil_reads(good), [])

    def test_a_conditional_write_does_not_define_the_variable(self):
        # A write inside a branch only runs when the branch does, so the
        # variable is still undefined on the other path.
        bad = (
            'private _x = missionNamespace getVariable ["k", nil];\n'
            "if (false) then { _x = 5; };\n"
            "private _y = _x + 1;\n"
        )
        self.assertEqual(len(find_nil_reads(bad)), 1)


if __name__ == "__main__":
    unittest.main()
