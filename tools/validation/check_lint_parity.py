#!/usr/bin/env python3
"""Fail when `make lint` and the CI workflow disagree.

A local gate set narrower than CI is not a gate. On 2026-09-23 a red build
shipped to main because `validate_cross_module.py` ran in CI and not in the
local `make lint`: a cross-addon read used QGVAR where EGVAR was needed, and
no local check could see it.

This compares the validator invocations in the two files and reports any
that appear in one and not the other.

Run:  python3 tools/validation/check_lint_parity.py
Exit 0 when the sets match, 1 when they differ.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
MAKEFILE = REPO / "Makefile"

# Only the validator-style invocations matter. A step that sets up a
# toolchain or uploads an artefact is not a gate.
PATTERN = re.compile(r"python3\s+(tools/[\w./-]+\.py)((?:\s+--?[\w-]+)*)")


# These are not gates. An SBOM is generated output, and the parity check
# cannot include itself without recursing.
NOT_A_GATE = {
    "tools/make_sbom.py",
    "tools/validation/check_lint_parity.py",
}


def invocations(path, section=None):
    text = path.read_text(encoding="utf-8")
    if section is not None:
        # The CI jobs are separate; the "validate" job holds the checks.
        match = re.search(rf"^\s+{section}:", text, re.M)
        if match:
            text = text[match.start() :]
    found = set()
    for script, args in PATTERN.findall(text):
        entry = f"{script}{args}".strip()
        if script in NOT_A_GATE:
            continue
        found.add(entry)
    return found


def main():
    ci = invocations(WORKFLOW)
    local = invocations(MAKEFILE)

    missing_locally = sorted(ci - local)
    missing_in_ci = sorted(local - ci)

    if missing_locally:
        print(f"IN CI BUT NOT IN `make lint` ({len(missing_locally)}):")
        for item in missing_locally:
            print(f"  {item}")
    if missing_in_ci:
        print(f"IN `make lint` BUT NOT IN CI ({len(missing_in_ci)}):")
        for item in missing_in_ci:
            print(f"  {item}")

    if missing_locally or missing_in_ci:
        print("lint parity: FAIL")
        return 1

    print(f"lint parity: PASS ({len(ci)} checks match)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
