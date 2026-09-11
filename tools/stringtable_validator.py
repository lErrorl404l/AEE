#!/usr/bin/env python3
"""
AEE Stringtable Validator
Validates all stringtable.xml files in addons/.
Returns 0 if clean, 1 if issues found.
"""

import os
import sys
import xml.etree.ElementTree as ET

ADDONS_DIR = os.path.join(os.path.dirname(__file__), "..", "addons")
errors = []


def walk():
    for root, _dirs, files in os.walk(ADDONS_DIR):
        for f in files:
            if f == "stringtable.xml":
                yield os.path.join(root, f)


def validate(path):
    rel = os.path.relpath(path, os.path.join(ADDONS_DIR, ".."))
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        errors.append(f"{rel}: XML parse error — {e}")
        return
    root = tree.getroot()
    if root.tag != "Project":
        errors.append(f"{rel}: root element is <{root.tag}>, expected <Project>")
        return

    seen_keys = set()
    for package in root.findall("Package"):
        for key in package.findall("Key"):
            kid = key.get("ID", "")
            if not kid:
                errors.append(f"{rel}: <Key> without ID attribute")
                continue
            if kid in seen_keys:
                errors.append(f"{rel}: duplicate key '{kid}'")
            seen_keys.add(kid)

            containers = [c.tag for c in key]
    # Done


def main():
    count = 0
    for path in walk():
        validate(path)
        count += 1

    print(f"\nChecked {count} stringtable files")

    for e in errors:
        print(f"  ✖  {e}")

    if errors:
        print(f"\n{len(errors)} errors — FAIL")
        sys.exit(1)

    print("  ✔  All clean")
    sys.exit(0)


if __name__ == "__main__":
    main()
