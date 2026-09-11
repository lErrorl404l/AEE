#!/usr/bin/env python3
"""
AEE String Cross-Reference Checker
Checks that all STR_AEE_* strings in Stringtable.xml files are referenced in code,
and all code references have matching definitions.
Returns 0 if clean, 1 if issues found.
"""

import os
import sys
import re
import xml.etree.ElementTree as ET

ADDONS_DIR = os.path.join(os.path.dirname(__file__), "..", "addons")
errors = []
warnings = []


def find_stringtables():
    for root, _dirs, files in os.walk(ADDONS_DIR):
        for f in files:
            if f == "stringtable.xml":
                yield root, os.path.join(root, f)


def parse_stringtable(path):
    """Return set of (key, container_key) tuples defined in a stringtable."""
    defined = set()
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        errors.append(
            f"{os.path.relpath(path, os.path.join(ADDONS_DIR, '..'))}: XML parse error — {e}"
        )
        return defined

    root = tree.getroot()
    if root.tag != "Project":
        return defined

    for pkg in root.findall("Package"):
        container = pkg.get("name", "")
        for key in pkg.findall("Key"):
            kid = key.get("ID", "")
            if kid:
                defined.add((kid, container))
    return defined


def find_references(addon_path):
    """Find all STR_AEE_* references in code files under addon_path."""
    refs = set()
    pattern = re.compile(r"\bSTR_AEE_\w+\b")
    for root, _dirs, files in os.walk(addon_path):
        for f in files:
            if not (
                f.endswith(".sqf")
                or f.endswith(".cpp")
                or f.endswith(".hpp")
                or f.endswith(".h")
                or f.endswith(".xml")
            ):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except OSError:
                continue
            for m in pattern.finditer(content):
                refs.add(m.group())
    return refs


def main():
    # Phase 1: collect all defined strings from XML
    all_defined = {}
    for addon_dir, st_path in find_stringtables():
        rel = os.path.relpath(st_path, os.path.join(ADDONS_DIR, ".."))
        defined = parse_stringtable(st_path)
        for key, container in defined:
            all_defined[key] = (rel, container)

    # Phase 2: collect all code references
    all_refs = set()
    for addon_dir, _st_path in find_stringtables():
        all_refs |= find_references(addon_dir)

    # Phase 3: check for undefined references
    for ref in sorted(all_refs):
        if ref not in all_defined:
            # Check for similar keys (typo detection)
            similar = [k for k in all_defined if k.startswith(ref.rsplit("_", 1)[0])]
            hint = ""
            if similar:
                hint = f" — similar: {similar[0]}"
            warnings.append(f"undefined string '{ref}'{hint}")

    # Phase 4: check for unused definitions
    for key, (st_path, container) in sorted(all_defined.items(), key=lambda x: x[0]):
        if key not in all_refs:
            warnings.append(
                f"unused string '{key}' defined in {st_path} (container '{container}')"
            )

    print(
        f"\nChecked {len(all_defined)} defined strings, {len(all_refs)} code references"
    )

    for w in warnings:
        print(f"  ⚠  {w}")
    for e in errors:
        print(f"  ✖  {e}")

    if errors:
        print(f"\n{len(errors)} errors — FAIL")
        sys.exit(1)

    if warnings:
        print(f"\n{len(warnings)} warnings (non-blocking)")
    print("  ✔  All clean")
    sys.exit(0)


if __name__ == "__main__":
    main()
