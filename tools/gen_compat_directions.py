#!/usr/bin/env python3
"""Audit and render the compat_ace3 direction split (ADR-027).

AEE owns by declaration and load order, not by force.  Every function in a
compat addon takes one of two integration directions:

  ownership-claim  AEE is the declared authority and the host stands down
                   (for example AEE sets `ace_weather_enabled = false`).
  adaptation       the host owns the subsystem and AEE publishes into the
                   host's public API (for example ACE medical vitals).

A diagnostics function reads AEE state only and touches no host API; it is
neither, and is declared as `diagnostics` so it is not silently unclassified.

The source of truth is `addons/compat_ace3/directions.json`.  This generator
renders the direction table into the marked block of
`docs/wiki/chapters/integrations.qmd` and fails when a compat function has no
declared direction, when a declared entry names a function that does not
exist, or when the rendered block is stale.

Run:
    python3 tools/gen_compat_directions.py           # update the doc block
    python3 tools/gen_compat_directions.py --check   # fail on drift
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "addons" / "compat_ace3" / "directions.json"
FUNCS_DIR = ROOT / "addons" / "compat_ace3" / "functions"
DOC = ROOT / "docs" / "wiki" / "chapters" / "integrations.qmd"

BEGIN = "<!-- BEGIN GENERATED: compat_ace3 directions -->"
END = "<!-- END GENERATED: compat_ace3 directions -->"

ALLOWED = ("ownership-claim", "adaptation", "diagnostics")
# The two integration directions.  `diagnostics` is not an integration.
INTEGRATION = ("ownership-claim", "adaptation")

DIR_TITLE = {
    "ownership-claim": "OWNERSHIP CLAIM",
    "adaptation": "ADAPTATION",
    "diagnostics": "diagnostics",
}


def functions_on_disk() -> set[str]:
    """Return every compat_ace3 function file name (no extension)."""
    return {p.stem for p in FUNCS_DIR.glob("fnc_*.sqf")}


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def audit(functions: set[str], manifest: dict) -> list[str]:
    """Return the direction errors for the given function set and manifest."""
    errors: list[str] = []
    declared = manifest.get("functions", {})
    for fn in sorted(functions):
        entry = declared.get(fn)
        if entry is None:
            errors.append(f"no declared direction: {fn}")
            continue
        direction = entry.get("direction")
        if direction not in ALLOWED:
            errors.append(f"{fn}: invalid direction {direction!r}")
    for fn in sorted(set(declared) - functions):
        errors.append(f"{fn}: declared direction for a function that does not exist")
    return errors


def build_block(manifest: dict) -> str:
    """Render the deterministic markdown block for the doc."""
    rows = []
    for fn, entry in sorted(manifest.get("functions", {}).items()):
        api = ", ".join(f"`{a}`" for a in entry.get("host_api", [])) or "none"
        rows.append(
            f"| `{fn}` | {DIR_TITLE[entry['direction']]} | "
            f"{entry.get('domain', '')} | {api} | {entry['reason']} |"
        )
    lines = [
        BEGIN,
        "",
        "| Function | Direction | Domain | Host surface | Why |",
        "|---|---|---|---|---|",
        *rows,
        "",
        END,
    ]
    return "\n".join(lines)


def current_block(doc: str) -> str | None:
    start = doc.find(BEGIN)
    end = doc.find(END)
    if start < 0 or end < 0 or end < start:
        return None
    return doc[start : end + len(END)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail on drift, write nothing"
    )
    args = parser.parse_args()

    manifest = load_manifest()
    errors = audit(functions_on_disk(), manifest)
    if errors:
        for error in errors:
            print(f"compat directions: {error}")
        print("compat directions: FAIL")
        return 1

    block = build_block(manifest)
    doc = DOC.read_text(encoding="utf-8")
    present = current_block(doc)
    if present is None:
        print(f"compat directions: markers missing from {DOC.relative_to(ROOT)}")
        return 1

    if args.check:
        if present != block:
            print(
                "compat directions: integrations.qmd block is stale (run without --check)"
            )
            return 1
        print("compat directions: PASS")
        return 0

    DOC.write_text(doc.replace(present, block), encoding="utf-8")
    print("compat directions: wrote block to integrations.qmd")
    return 0


if __name__ == "__main__":
    sys.exit(main())
