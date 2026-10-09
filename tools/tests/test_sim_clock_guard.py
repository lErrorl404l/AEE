#!/usr/bin/env python3
"""Ban ``diag_deltaTime`` outside the one clock, and pin the jump contract.

``diag_deltaTime`` is the duration of the previous RENDERED frame, not the
interval between two calls of a throttled handler
(engine-commands-and-features.md:425,431-457).  A throttled model that integrates
it makes its time constant depend on the frame rate - the eye-driver and
thermal-AGC defect class (commits f36bc216, fc81d68e; probe P79).  The one clock
(``aee_core_simTime``, ``fnc_updateSimClock``) is the only time base a throttled
model may read.

This scan blanks comments and fails on any ``diag_deltaTime`` read in
``addons/**/*.sqf`` that is not the clock module and not an exact,
line-scoped allowlist entry.  Every allowlist entry must be a per-frame site,
a per-event site, or a stated ``max`` floor, and no read that uses
``diag_deltaTime`` AS ITS INTERVAL may be allowlisted.

Run: python3 -m unittest tools.tests.test_sim_clock_guard
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADDONS = os.path.join(ROOT, "addons")
CLOCK_MODULE = "addons/core/functions/fnc_updateSimClock.sqf"
CLOCK_PATH = os.path.join(ROOT, CLOCK_MODULE)

# Line-scoped allowlist: (path, line) -> reason and kind.  ONLY a per-frame
# site, a per-event site, or a stated max floor may appear here.  A read that
# USES diag_deltaTime AS ITS INTERVAL inside a throttled handler is never
# allowlisted; it is migrated onto the clock.
ALLOWLIST = {
    ("addons/ballistics/functions/fnc_calculateBarrelState.sqf", 83): {
        "reason": (
            "the Fired event, not a PFH: one call per shot, so the previous "
            "frame delta is the real inter-shot stopwatch, not a handler interval"
        ),
        "kind": "per-event",
        "contains": "private _dt = diag_deltaTime;",
    },
    ("addons/core/functions/fnc_getSmoothedWeather.sqf", 59): {
        "reason": (
            "cached on diag_frameNo, so this body runs once per frame, never "
            "inside a throttled handler; the frame delta IS the frame interval here"
        ),
        "kind": "per-frame",
        "contains": "private _dt = diag_deltaTime;",
    },
    ("addons/thermal/functions/solver/fnc_calculateObjectTemperature.sqf", 197): {
        "reason": (
            "a max floor only; the real interval is the diag_tickTime delta at "
            "line 103, clamped to 30 s, so diag_deltaTime bounds the floor"
        ),
        "kind": "floor",
        "contains": "max diag_deltaTime",
    },
}


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def strip_comments(text: str) -> str:
    """Blank out line and block comments, preserving line count and offsets."""
    out = list(text)
    i, n = 0, len(text)
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


def scan(addons_root: str = ADDONS) -> list[tuple[str, int, str]]:
    """Return (rel_path, line, text) for every non-allowlisted read."""
    violations: list[tuple[str, int, str]] = []
    for dirpath, _dirs, files in os.walk(addons_root):
        for name in files:
            if not name.endswith(".sqf"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            code = strip_comments(_read(path))
            for line_no, line in enumerate(code.split("\n"), start=1):
                if "diag_deltaTime" not in line:
                    continue
                if rel == CLOCK_MODULE:
                    continue
                if (rel, line_no) in ALLOWLIST:
                    continue
                violations.append((rel, line_no, line.strip()))
    return violations


def main() -> int:
    violations = scan()
    if not violations:
        print(
            f"test_sim_clock_guard: PASS (no diag_deltaTime outside the clock; "
            f"{len(ALLOWLIST)} reasoned line-scoped allowlist entries)"
        )
        return 0
    print("test_sim_clock_guard: FAIL")
    for rel, line, text in violations:
        print(f"  {rel}:{line} reads diag_deltaTime: {text}")
    print(
        f"{len(violations)} site(s); read aee_core_simTime and compute "
        f"_dt = aee_core_simTime - _lastSimTime once per run"
    )
    return 1


def _code(path: str) -> str:
    return strip_comments(_read(path))


class TestSimClockGuard(unittest.TestCase):
    def test_scan_is_clean(self):
        self.assertEqual(main(), 0)

    def test_a_raw_read_outside_the_clock_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "addons")
            os.makedirs(os.path.join(root, "mod", "functions"))
            fixture = os.path.join(root, "mod", "functions", "bad.sqf")
            with open(fixture, "w", encoding="utf-8") as fh:
                fh.write("private _dt = diag_deltaTime;\n")
            violations = scan(root)
        self.assertTrue(
            violations,
            "a raw diag_deltaTime read outside the clock must fail the scan",
        )

    def test_a_commented_read_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "addons")
            os.makedirs(os.path.join(root, "mod", "functions"))
            fixture = os.path.join(root, "mod", "functions", "ok.sqf")
            with open(fixture, "w", encoding="utf-8") as fh:
                fh.write("// diag_deltaTime is the frame delta\n")
            violations = scan(root)
        self.assertEqual(violations, [], "a comment is not a read")

    def test_allowlist_entries_have_a_reason_and_a_line(self):
        for (rel, line_no), entry in ALLOWLIST.items():
            self.assertTrue(entry["reason"].strip(), f"{rel}:{line_no} has no reason")
            self.assertIn(
                entry["kind"],
                ("per-frame", "per-event", "floor"),
                f"{rel}:{line_no} has no valid kind",
            )
            path = os.path.join(ROOT, rel)
            self.assertTrue(os.path.isfile(path), f"{rel} is missing")
            lines = _read(path).split("\n")
            self.assertLessEqual(line_no, len(lines), f"{rel}:{line_no} out of range")

    def test_every_allowlisted_line_is_a_per_frame_per_event_or_floor_site(self):
        for (rel, line_no), entry in ALLOWLIST.items():
            path = os.path.join(ROOT, rel)
            raw = _read(path)
            line = raw.split("\n")[line_no - 1]
            self.assertIn(
                entry["contains"], line, f"{rel}:{line_no} is not the pinned read"
            )
            self.assertIn("diag_deltaTime", line, f"{rel}:{line_no} is not a read")
            if entry["kind"] == "per-event":
                self.assertIn(
                    "Fired", raw, f"{rel}:{line_no} claims per-event but names no event"
                )
            if entry["kind"] == "per-frame":
                self.assertIn(
                    "diag_frameNo",
                    raw,
                    f"{rel}:{line_no} claims per-frame but caches on no frame counter",
                )
            if entry["kind"] == "floor":
                self.assertIn("max diag_deltaTime", line)
                self.assertIn(
                    "diag_tickTime",
                    raw,
                    f"{rel}:{line_no} claims a floor but has no real-interval clock",
                )

    def test_no_allowlisted_line_uses_delta_time_as_its_interval(self):
        # A read assigned to a variable that is then divided/integrated as the
        # step would be the defect.  The floor entry is a `max`, never the step.
        for (rel, line_no), entry in ALLOWLIST.items():
            line = _read(os.path.join(ROOT, rel)).split("\n")[line_no - 1]
            if entry["kind"] == "floor":
                self.assertIn("max diag_deltaTime", line)
            else:
                self.assertRegex(
                    line,
                    r"(private _dt = diag_deltaTime;)|(diag_deltaTime\)+ ?min)",
                    f"{rel}:{line_no} is not a plain per-frame/per-event read",
                )


class TestClockJumpContract(unittest.TestCase):
    """The clock owns the world-clock jump detector and handles the wrap."""

    def test_the_clock_reads_day_time_not_time(self):
        code = _code(CLOCK_PATH)
        self.assertIn("dayTime", code)
        self.assertIn("QGVAR(clockJump)", code)

    def test_the_clock_wraps_the_day_before_it_compares(self):
        # Pin the real predicate, not a Python mirror.  The midnight crossing
        # (86400 s / 24 h) must read the short way round, so both wrap lines
        # must sit before the threshold compare.  The same predicate is
        # exercised as real SQF by test_eye_adaptation.TestEyeTimeSkip.
        code = _code(CLOCK_PATH)
        self.assertRegex(code, r"if \(_delta > 12\) then \{ _delta = _delta - 24; \};")
        self.assertRegex(
            code, r"if \(_delta < -12\) then \{ _delta = _delta \+ 24; \};"
        )
        self.assertRegex(code, r"_jump = abs _delta > ([0-9.]+);")


if __name__ == "__main__":
    sys.exit(main())
