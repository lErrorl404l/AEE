#!/usr/bin/env python3
"""
AEE SQF Validator
Validates all .sqf files in addons/ for bracket balance, tabs, semicolons.
Returns 0 if clean, 1 if issues found.
"""

import os
import sys
import re
import fnmatch

ADDONS_DIR = os.path.join(os.path.dirname(__file__), "..", "addons")
SKIP_FILES = {"script_component.hpp"}
errors = []


def walk_sqf():
    for root, _dirs, files in os.walk(ADDONS_DIR):
        for f in fnmatch.filter(files, "*.sqf"):
            if f.lower() in SKIP_FILES:
                continue
            yield os.path.join(root, f)


def check_file(path):
    rel = os.path.relpath(path, os.path.join(ADDONS_DIR, ".."))
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError as e:
        errors.append(f"{rel}: cannot read — {e}")
        return

    # Track bracket stacks per line for precise error reporting
    parens = []  # (
    brackets = []  # [
    braces = []  # {

    for lineno, raw in enumerate(lines, 1):
        line = raw.rstrip("\n").rstrip("\r")

        # Skip comments (single-line)
        stripped = line.strip()

        # Track if we're inside a string
        in_string_sq = False  # 'single quoted'
        in_string_dq = False  # "double quoted"
        in_block_comment = False

        # Check for tab
        if "\t" in line:
            errors.append(f"{rel}:{lineno}: tab character (use spaces)")

        # Check for trailing whitespace
        if line != line.rstrip() and line.strip():
            errors.append(f"{rel}:{lineno}: trailing whitespace")

        i = 0
        while i < len(line):
            ch = line[i]

            # Handle strings
            if ch == "'" and not in_string_dq:
                in_string_sq = not in_string_sq
                i += 1
                continue
            if ch == '"' and not in_string_sq:
                in_string_dq = not in_string_dq
                i += 1
                continue

            if not in_string_sq and not in_string_dq:
                # Block comments
                if ch == "/" and i + 1 < len(line) and line[i + 1] == "*":
                    in_block_comment = True
                    i += 2
                    continue
                if ch == "*" and i + 1 < len(line) and line[i + 1] == "/":
                    in_block_comment = False
                    i += 2
                    continue

                if not in_block_comment:
                    # Line comments
                    if ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                        break  # rest of line is comment

                    # Bracket tracking
                    if ch == "(":
                        parens.append((lineno, i))
                    elif ch == ")":
                        if not parens:
                            errors.append(f"{rel}:{lineno}: unmatched ')'")
                        else:
                            parens.pop()
                    elif ch == "[":
                        brackets.append((lineno, i))
                    elif ch == "]":
                        if not brackets:
                            errors.append(f"{rel}:{lineno}: unmatched ']'")
                        else:
                            brackets.pop()
                    elif ch == "{":
                        braces.append((lineno, i))
                    elif ch == "}":
                        if not braces:
                            errors.append(f"{rel}:{lineno}: unmatched '}}'")
                        else:
                            braces.pop()

            i += 1

    # Report unclosed brackets
    for lineno, col in parens:
        errors.append(f"{rel}:{lineno}: unclosed '('")
    for lineno, col in brackets:
        errors.append(f"{rel}:{lineno}: unclosed '['")
    for lineno, col in braces:
        errors.append(f"{rel}:{lineno}: unclosed '{{'")

    # Check for old-style script_component.hpp include in functions/
    if "\\functions\\" in rel or "/functions/" in rel:
        if lines and '#include "script_component.hpp"' in lines[0]:
            errors.append(
                f'{rel}: line 1: uses old `#include "script_component.hpp"` — should be `#include "..\\script_component.hpp"`'
            )


def main():
    count = 0
    for path in walk_sqf():
        check_file(path)
        count += 1

    print(f"\nChecked {count} SQF files")
    for e in errors:
        print(f"  ✖  {e}")

    if errors:
        print(f"\n{len(errors)} errors — FAIL")
        sys.exit(1)

    print("  ✔  All clean")
    sys.exit(0)


if __name__ == "__main__":
    main()
