#!/usr/bin/env python3
"""
AEE Config Style Checker
Validates format of all .cpp/.hpp config files in addons/.
Returns 0 if clean, 1 if issues found.
"""

import os
import sys
import re

ADDONS_DIR = os.path.join(os.path.dirname(__file__), "..", "addons")
EXTENSIONS = (".cpp", ".hpp")
errors = []
warnings = []


def walk():
    for root, _dirs, files in os.walk(ADDONS_DIR):
        for f in files:
            if f.endswith(EXTENSIONS):
                yield os.path.join(root, f)


def check_file(path):
    rel = os.path.relpath(path, os.path.join(ADDONS_DIR, ".."))
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as e:
        errors.append(f"{rel}: cannot read — {e}")
        return

    # Check for BOM
    if raw[:3] == b"\xef\xbb\xbf":
        warnings.append(f"{rel}: UTF-8 BOM detected")

    # Check for zero-width / non-printable chars
    text = raw.decode("utf-8", errors="replace")

    for i, ch in enumerate(text):
        if 0 < ord(ch) < 32 and ch not in "\n\r\t":
            warnings.append(f"{rel}: non-printable char U+{ord(ch):04X} at offset {i}")

    lines = text.splitlines()

    # Invisible Unicode (zero-width, BOM remnants, etc.)
    invisible = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
    for lineno, line in enumerate(lines, 1):
        m = invisible.search(line)
        if m:
            errors.append(
                f"{rel}:{lineno}: invisible Unicode character U+{ord(m.group()):04X}"
            )

    # Tabs (common paste error)
    for lineno, line in enumerate(lines, 1):
        if "\t" in line:
            errors.append(f"{rel}:{lineno}: tab character (use spaces)")

    # Trailing whitespace
    for lineno, line in enumerate(lines, 1):
        if line != line.rstrip() and line.strip():
            errors.append(f"{rel}:{lineno}: trailing whitespace")

    # No final newline
    if not raw.endswith(b"\n"):
        warnings.append(f"{rel}: no trailing newline")

    # Crude bracket balance (skip inside strings)
    brace_depth = 0
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue
        for ch in line:
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
        if brace_depth < 0:
            errors.append(f"{rel}:{lineno}: unexpected closing brace (depth < 0)")
            brace_depth = 0

    if brace_depth > 0:
        errors.append(f"{rel}: end of file with {brace_depth} unclosed braces")

    # Empty parentheses on class-like forward declarations
    for lineno, line in enumerate(lines, 1):
        if re.match(r"^\s*class\s+\w+\s*\(\s*\)\s*;", line):
            errors.append(f"{rel}:{lineno}: `class X()` used instead of `class X;`")


def main():
    count = 0
    for path in walk():
        check_file(path)
        count += 1

    print(f"\nChecked {count} config files")

    for w in warnings:
        print(f"  ⚠  {w}")
    for e in errors:
        print(f"  ✖  {e}")

    if warnings:
        print(f"\n{len(warnings)} warnings")
    if errors:
        print(f"\n{len(errors)} errors — FAIL")
        sys.exit(1)

    print("  ✔  All clean")
    sys.exit(0)


if __name__ == "__main__":
    main()
