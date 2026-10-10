#!/usr/bin/env python3
"""Contract: a raw diag_log in addons/**/*.sqf must be on the allowlist.

Every diagnostic that carries AEE state must go through AEE_LOG_ERROR,
AEE_LOG_WARN, AEE_LOG_INFO or AEE_LOG_DEBUG (addons/lib/script_macros.hpp),
so the module tag and the debug switch apply.  A raw diag_log is allowed
only when it is a deliberate banner, an engine callback with no component
context, or code that runs before the macros exist.  Each such site is
recorded in tools/validation/raw_diag_allowlist.txt with a reason.

The scan mirrors the plan command:

    rg -n "diag_log" addons --glob '*.sqf'

Comment-only references to diag_log are not sites and are ignored.

Run:  python3 tools/tests/raw_diag_allowlist.py
Exit 0 when clean, 1 on any site that is not on the allowlist.
"""

import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
ALLOWLIST = REPO / "tools" / "validation" / "raw_diag_allowlist.txt"

MATCH_RE = re.compile(r"^(.*?):(\d+):(.*)$")
ENTRY_RE = re.compile(r"^(\S+:\d+)\s+(\S.*)$")


def scan_rg():
    """Return [(rel_path, line, content)] from ripgrep."""
    out = subprocess.run(
        ["rg", "-n", "diag_log", "addons", "--glob", "*.sqf"],
        cwd=REPO,
        capture_output=True,
        text=True,
    ).stdout
    sites = []
    for row in out.splitlines():
        m = MATCH_RE.match(row)
        if not m:
            continue
        path, line, content = m.group(1), int(m.group(2)), m.group(3)
        if content.lstrip().startswith("//"):
            continue
        sites.append((path.replace("\\", "/"), line, content.strip()))
    return sites


def scan_python():
    """Fallback scan when ripgrep is not installed."""
    sites = []
    for path in sorted(ADDONS.rglob("*.sqf")):
        for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            if "diag_log" not in line:
                continue
            if line.lstrip().startswith("//"):
                continue
            sites.append((path.relative_to(REPO).as_posix(), n, line.strip()))
    return sites


def load_allowlist():
    entries = {}
    for raw in ALLOWLIST.read_text(encoding="utf-8").split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = ENTRY_RE.match(line)
        if not m:
            print(f"raw_diag_allowlist: bad allowlist line: {raw!r}")
            return None
        entries[m.group(1)] = m.group(2)
    return entries


def main():
    if not ALLOWLIST.exists():
        print(f"raw_diag_allowlist: FAIL (missing {ALLOWLIST})")
        return 1
    allow = load_allowlist()
    if allow is None:
        return 1

    sites = scan_rg() if shutil.which("rg") else scan_python()

    failures = []
    seen = set()
    for path, line, _content in sites:
        key = f"{path}:{line}"
        seen.add(key)
        if key not in allow:
            failures.append(key)

    for key in sorted(set(allow) - seen):
        print(f"raw_diag_allowlist: stale allowlist entry (no such site): {key}")

    if failures:
        print("raw_diag_allowlist: FAIL")
        for key in failures:
            print(f"  {key} raw diag_log is not on the allowlist")
        print(f"{len(failures)} site(s) must use an AEE_LOG_* macro or be allowlisted")
        return 1

    print(f"raw_diag_allowlist: PASS ({len(sites)} allowlisted raw diag_log site(s))")
    return 0


class TestRawDiagAllowlist(unittest.TestCase):
    """The standalone scan, runnable through the unittest suite."""

    def test_every_raw_diag_is_allowlisted(self):
        self.assertEqual(main(), 0)


if __name__ == "__main__":
    sys.exit(main())
