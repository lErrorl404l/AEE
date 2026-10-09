#!/usr/bin/env python3
"""Generate AEE's public extension contract (ADR-027).

AEE owns by declaration and load order.  A third-party mod consumes AEE by
declaring `requiredAddons[] = {"aee_core"}` and loading after AEE.  AEE treats
the `aee_*` names as a stable public contract:

  * the addon PBOs `aee_<component>`,
  * the callable functions `aee_<component>_fnc_<name>`,
  * the shared state variables `aee_core_*`,
  * the AEE-authored config classes (`AEE_*`, `ColorAEE`, `CfgClothing`).

The physiology resolver registries are the template for a deliberate
extension: `compat_ace3` registers into `aee_physiology_massResolvers` and
`aee_physiology_categoryResolvers`, and `aee_core` reads them and never names
the host mod.  The direction inverts onto AEE's registry.

This generator scans the repository and renders the contract into the marked
block of `docs/wiki/research/extension-contract.md`.

Run:
    python3 tools/gen_extension_contract.py           # update the doc block
    python3 tools/gen_extension_contract.py --check   # fail on drift
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
ADDONS = ROOT / "addons"
DOC = ROOT / "docs" / "wiki" / "research" / "extension-contract.md"

BEGIN = "<!-- BEGIN GENERATED: extension contract -->"
END = "<!-- END GENERATED: extension contract -->"

# AEE-authored config classes that anchor the class contract.  Each must be
# declared with a literal `class <name>` in the named source.  Macro-built
# classes (for example the EDEN modules) are not anchored by name.
ANCHOR_CLASSES = {
    "AEE_Unknown_Other": "addons/symbology/config.cpp",
    "ColorAEE": "addons/symbology/config.cpp",
    "AEE_MarkerBase": "addons/symbology/config.cpp",
    "AEE_SandCloud": "addons/fx/config.cpp",
    "AEE_SnowCloud": "addons/fx/config.cpp",
    "AEE_SupersonicTrace": "addons/fx/config.cpp",
    "CfgClothing": "addons/clothing/config.cpp",
}

# The engine config classes AEE re-declares.  Each must be opened literally in
# the named source.
ANCHOR_ENGINE_CLASSES = {
    "CfgWorlds": "addons/lighting/config.cpp",
    "CfgCloudlets": "addons/fx/config.cpp",
    "CfgMarkers": "addons/symbology/config.cpp",
    "CfgMarkerColors": "addons/symbology/config.cpp",
    "CfgMarkerClasses": "addons/symbology/config.cpp",
}

PREP_RE = re.compile(r"\bPREP\(([A-Za-z0-9_]+)\)")
PREPS_RE = re.compile(r"\bPREPS\([A-Za-z0-9_]+,\s*([A-Za-z0-9_]+)\)")
STATE_RE = re.compile(r"\baee_core_[A-Za-z0-9_]+")
# The per-module migration tables (ADR-032) hold old setting names; they are
# not part of the published state surface.
MIGRATION_TABLES = frozenset({"settingsMigration.sqf"})
LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def addon_components() -> list[str]:
    return sorted(p.parent.name for p in ADDONS.glob("*/$PBOPREFIX$"))


def public_functions() -> list[str]:
    names: set[str] = set()
    for prep in ADDONS.glob("*/XEH_PREP.hpp"):
        component = prep.parent.name
        text = prep.read_text(encoding="utf-8")
        for match in PREP_RE.findall(text):
            names.add(f"aee_{component}_fnc_{match}")
        for match in PREPS_RE.findall(text):
            names.add(f"aee_{component}_fnc_{match}")
    return sorted(names)


def public_core_state() -> list[str]:
    names: set[str] = set()
    for sqf in ADDONS.glob("**/*.sqf"):
        # The migration tables name the OLD setting on purpose; they are not a
        # contract surface, so skip them.
        if sqf.name in MIGRATION_TABLES:
            continue
        text = LINE_COMMENT_RE.sub(
            "", sqf.read_text(encoding="utf-8", errors="replace")
        )
        names.update(STATE_RE.findall(text))
    return sorted(names)


def class_exists(source: str, name: str) -> bool:
    path = ROOT / source
    if not path.exists():
        return False
    return (
        re.search(rf"\bclass\s+{re.escape(name)}\b", path.read_text(encoding="utf-8"))
        is not None
    )


def audit() -> list[str]:
    errors: list[str] = []
    for name, source in {**ANCHOR_CLASSES, **ANCHOR_ENGINE_CLASSES}.items():
        if not class_exists(source, name):
            errors.append(f"class {name} not declared in {source}")
    if not public_functions():
        errors.append("no public functions found (XEH_PREP.hpp scan is empty)")
    if not addon_components():
        errors.append("no addon components found ($PBOPREFIX$ scan is empty)")
    return errors


def build_block() -> str:
    lines: list[str] = [BEGIN, ""]

    lines.append("### Public addon PBOs")
    lines.append("")
    lines.append("| PBO | Component |")
    lines.append("|---|---|")
    for component in addon_components():
        lines.append(f"| `aee_{component}` | `{component}` |")
    lines.append("")

    functions = public_functions()
    lines.append(f"### Public functions ({len(functions)})")
    lines.append("")
    lines.append(
        "Compiled by CBA XEH `PREP`/`PREPS` into the `aee_<component>_fnc_<name>` "
        "namespace. Call one as `call aee_<component>_fnc_<name>`."
    )
    lines.append("")
    for name in functions:
        lines.append(f"- `{name}`")
    lines.append("")

    state = public_core_state()
    lines.append(f"### Public core state variables ({len(state)})")
    lines.append("")
    lines.append(
        "The `aee_core_*` mission variables. The canonical list of every "
        "published variable is `docs/wiki/chapters/state-variables.qmd`; these "
        "are the names that appear in the source as a contract surface."
    )
    lines.append("")
    for name in state:
        lines.append(f"- `{name}`")
    lines.append("")

    lines.append("### AEE-authored config classes")
    lines.append("")
    lines.append("| Class | Declaring source |")
    lines.append("|---|---|")
    for name, source in ANCHOR_CLASSES.items():
        lines.append(f"| `{name}` | `{source}` |")
    lines.append("")
    lines.append("Engine classes AEE re-declares:")
    lines.append("")
    for name, source in ANCHOR_ENGINE_CLASSES.items():
        lines.append(f"- `{name}` (`{source}`)")
    lines.append("")
    lines.append(END)
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

    errors = audit()
    if errors:
        for error in errors:
            print(f"extension contract: {error}")
        print("extension contract: FAIL")
        return 1

    block = build_block()
    doc = DOC.read_text(encoding="utf-8")
    present = current_block(doc)
    if present is None:
        print(f"extension contract: markers missing from {DOC.relative_to(ROOT)}")
        return 1

    if args.check:
        if present != block:
            print("extension contract: doc block is stale (run without --check)")
            return 1
        print(
            f"extension contract: PASS ({len(public_functions())} functions, "
            f"{len(public_core_state())} core vars, {len(addon_components())} addons)"
        )
        return 0

    DOC.write_text(doc.replace(present, block), encoding="utf-8")
    print("extension contract: wrote docs/wiki/research/extension-contract.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
