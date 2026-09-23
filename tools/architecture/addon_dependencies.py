#!/usr/bin/env python3
"""Generate docs/architecture/addon-dependencies.md from the repository.

An addon edge is an EFUNC(component,...) call or an EGVAR(component,...)
variable read in another addon's source. Those are the only two forms a
cross-addon reference can take, so scanning for them yields the whole
graph. Hand-written dependency maps drift; this one cannot.

Run:  python3 tools/architecture/addon_dependencies.py
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
OUT = REPO / "docs" / "architecture" / "addon-dependencies.md"

CALL = re.compile(r"EFUNC\(\s*([a-z_]+)\s*,")
VAR = re.compile(r"[QE]?EGVAR\(\s*([a-z_]+)\s*,")


def dependencies(addon):
    found = set()
    for path in (ADDONS / addon).rglob("*.sqf"):
        text = path.read_text(encoding="utf-8", errors="replace")
        found.update(CALL.findall(text))
        found.update(VAR.findall(text))
    found.discard(addon)
    return sorted(found)


def main():
    names = sorted(d.name for d in ADDONS.iterdir() if d.is_dir())
    graph = {n: dependencies(n) for n in names}

    lines = [
        "# Addon dependency map",
        "",
        "Generated from the repository, not from memory. Regenerate with",
        "`python3 tools/architecture/addon_dependencies.py`. It scans every",
        "`*.sqf` under `addons/<component>/` for `EFUNC(component,...)` calls and",
        "`EGVAR(component,...)` variable reads, the only two forms a cross-addon",
        "edge can take.",
        "",
        "## The map",
        "",
        "| addon | depends on |",
        "|---|---|",
    ]
    for n in names:
        d = graph[n]
        cell = "none" if not d else ", ".join(f"`{x}`" for x in d)
        lines.append(f"| `{n}` | {cell} |")

    leaves = [n for n in names if not graph[n] and not n.startswith("compat_")]
    hubs = sorted((n for n in names if len(graph[n]) > 5), key=lambda n: -len(graph[n]))
    lines += [
        "",
        "## Reading it",
        "",
        "- Leaves (depend on nothing, safe for anything to depend on): "
        + ", ".join(f"`{n}`" for n in leaves)
        + ".",
        "- Hubs (depend on most others): "
        + ", ".join(f"`{n}` ({len(graph[n])})" for n in hubs)
        + ".",
        "- Compat addons (`compat_*`) load only when their host mod is present. An",
        "  optional read of a compat variable is not an edge in the core set.",
        "",
        "## Why this exists",
        "",
        "Issue #203 carried a hand-written map whose tiers did not match the",
        "repository, and a cycle between `environmental` and `thermal` went",
        "unnoticed. This file is generated so the two cannot drift apart again.",
        "",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)}: {len(names)} addons")


if __name__ == "__main__":
    main()
