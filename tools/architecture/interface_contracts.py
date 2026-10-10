#!/usr/bin/env python3
"""Generate the Interface Control Documents under ``docs/icd/``.

An interface between two addons is a variable one addon publishes and
another addon reads. The only cross-addon read form is ``EGVAR`` and
``QEGVAR``, so scanning for it yields the whole boundary set. A
hand-written contract drifts; this one cannot.

The producer addon is the Configuration Item that owns the variable. The
consumer is the Configuration Item that reads it. The producer must
initialise before the consumer reads, so the direction is one way.

Run:  python3 tools/architecture/interface_contracts.py
Check: python3 tools/architecture/interface_contracts.py --check
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
ICD = REPO / "docs" / "icd"
ANNEX_C = REPO / "docs" / "wiki" / "annexes" / "annex-c-variable-reference.qmd"

# A cross-addon read: EGVAR(producer, leaf) or QEGVAR(producer, leaf).
READ = re.compile(r"[QE]?EGVAR\(\s*([a-z_0-9]+)\s*,\s*([A-Za-z0-9_]+)\s*\)")

# An Annex C row: | `aee_core_currentTemperature` | core | Air temperature in C |
ANNEX_ROW = re.compile(r"\|\s*`(aee_[A-Za-z0-9_]+)`\s*\|\s*[^|]+\|\s*([^|]+?)\s*\|")

# The minimum crossing count for a boundary to earn its own document.
MIN_VARS = 2

# A unit phrase in an Annex C purpose -> (type, unit, range).
UNITS = (
    ("in C", "SCALAR", "degrees C", "UNKNOWN"),
    ("in hPa", "SCALAR", "hPa", "UNKNOWN"),
    ("in m/s", "SCALAR", "m/s", "UNKNOWN"),
    ("in degrees", "SCALAR", "degrees", "UNKNOWN"),
    ("in metres", "SCALAR", "m", "UNKNOWN"),
    ("in minutes", "SCALAR", "minutes", "UNKNOWN"),
    ("in seconds", "SCALAR", "s", "UNKNOWN"),
    ("percent", "SCALAR", "percent", "0..100"),
    ("0..1", "SCALAR", "fraction", "0..1"),
    ("Koppen", "STRING", "code", "UNKNOWN"),
    ("flag", "BOOL", "boolean", "0 or 1"),
)


def scan() -> dict[tuple[str, str], dict[str, str]]:
    """Every producer->consumer boundary, its variables, and one source read.

    Returns {(producer, consumer): {variable: "file:line"}}. The first read
    of a variable in a consumer is kept as its evidence.
    """
    edges: dict[tuple[str, str], dict[str, str]] = {}
    for addon in sorted(d for d in ADDONS.iterdir() if d.is_dir()):
        consumer = addon.name
        for path in sorted(addon.rglob("*.sqf")):
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in READ.finditer(text):
                producer, leaf = match.group(1), match.group(2)
                if producer == consumer:
                    continue
                line = text.count("\n", 0, match.start()) + 1
                rel = path.relative_to(REPO).as_posix()
                variable = f"aee_{producer}_{leaf}"
                bucket = edges.setdefault((producer, consumer), {})
                bucket.setdefault(variable, f"{rel}:{line}")
    return edges


def annex_purposes() -> dict[str, str]:
    """Variable -> its Annex C purpose sentence, verbatim."""
    if not ANNEX_C.is_file():
        return {}
    text = ANNEX_C.read_text(encoding="utf-8")
    return {name: purpose for name, purpose in ANNEX_ROW.findall(text)}


def fields(variable: str, purpose: str) -> tuple[str, str, str]:
    """(type, unit, range) for a variable, read from its Annex C purpose.

    A field the purpose does not state is UNKNOWN. This function invents
    nothing: it copies a unit only when the purpose names one.
    """
    for phrase, kind, unit, rng in UNITS:
        if phrase in purpose:
            return kind, unit, rng
    return "UNKNOWN", "UNKNOWN", "UNKNOWN"


def edge_doc(
    producer: str, consumer: str, variables: dict[str, str], purposes: dict[str, str]
) -> str:
    """One Interface Control Document as markdown text."""
    title = f"# ICD: {producer} to {consumer}"
    lines = [
        title,
        "",
        f"- Producer CI: `addons/{producer}/`",
        f"- Consumer CI: `addons/{consumer}/`",
        f"- Direction: one way. `{producer}` must initialise before `{consumer}` reads.",
        f"- Variables crossing: {len(variables)}.",
        "",
        "A variable named `aee_{p}_{leaf}` is written as `EGVAR({p},leaf)` by the "
        "producer and read as `EGVAR({p},leaf)` or `QEGVAR({p},leaf)` by the "
        "consumer.".replace("{p}", producer),
        "",
        "| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |",
        "|---|---|---|---|---|---|---|",
    ]
    for variable in sorted(variables):
        purpose = purposes.get(variable, "UNKNOWN")
        kind, unit, rng = fields(variable, purpose)
        lines.append(
            f"| `{variable}` | {kind} | {unit} | {rng} | UNKNOWN | "
            f"`{variables[variable]}` | {purpose} |"
        )
    lines += [
        "",
        "The default value and the update frequency are the producer's "
        "contract. They are set in the producer's CBA settings and recorded "
        "in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This "
        "document records the boundary and the direction, not a second copy "
        "of the variable reference.",
        "",
        "Regenerate with `python3 tools/architecture/interface_contracts.py`.",
        "",
    ]
    return "\n".join(lines)


def readme(edges: dict[tuple[str, str], dict[str, str]]) -> str:
    """The ICD index, the naming convention, and the single-variable edges."""
    big = {k: v for k, v in edges.items() if len(v) >= MIN_VARS}
    small = {k: v for k, v in edges.items() if len(v) < MIN_VARS}
    lines = [
        "# Interface Control Documents",
        "",
        "Each document defines one boundary between two Configuration Items "
        "(CIs). A CI is one addon under `addons/`. A boundary is a variable "
        "one CI publishes and another CI reads.",
        "",
        "The documents are generated from the source, not from memory. "
        "Regenerate with `python3 tools/architecture/interface_contracts.py`. "
        "The generator scans every `*.sqf` for `EGVAR(producer,leaf)` and "
        "`QEGVAR(producer,leaf)`, the only two cross-addon read forms.",
        "",
        "## Naming convention",
        "",
        "- File name: `<producer>-<consumer>.md`. The producer is the CI that "
        "owns the variable. The consumer is the CI that reads it.",
        "- Variable name: `aee_<producer>_<leaf>`. The producer writes it as "
        "`EGVAR(<producer>,<leaf>)`.",
        "- Direction: one way. The producer must initialise before the consumer reads.",
        "",
        "## Why this layer exists",
        "",
        "JSP 945 controls a Configuration Item and the interface between "
        "Configuration Items. The `addons/` tree is the CI decomposition. "
        "The interface between two CIs was implicit in the source, so a "
        "wiring defect (issue #64) could not be seen from the documentation. "
        "This layer makes the boundary explicit and checkable.",
        "",
        "## Index",
        "",
        f"Every boundary with {MIN_VARS} or more crossing variables has its "
        "own document. A boundary with one crossing variable is listed in the "
        "table below.",
        "",
        "| Producer | Consumer | Variables | Document |",
        "|---|---|---|---|",
    ]
    for (producer, consumer), variables in sorted(
        big.items(), key=lambda kv: (-len(kv[1]), kv[0])
    ):
        lines.append(
            f"| `{producer}` | `{consumer}` | {len(variables)} | "
            f"[{producer}-{consumer}.md]({producer}-{consumer}.md) |"
        )
    lines += [
        "",
        "## Single-variable boundaries",
        "",
        "| Producer | Consumer | Variable |",
        "|---|---|---|",
    ]
    for (producer, consumer), variables in sorted(small.items()):
        for variable in sorted(variables):
            lines.append(f"| `{producer}` | `{consumer}` | `{variable}` |")
    lines += [
        "",
        f"Counts: {len(big)} documented boundaries, {len(small)} "
        "single-variable boundaries.",
        "",
    ]
    return "\n".join(lines)


def outputs() -> dict[Path, str]:
    """The full generated file set: path -> text."""
    edges = scan()
    purposes = annex_purposes()
    files = {ICD / "README.md": readme(edges)}
    for (producer, consumer), variables in edges.items():
        if len(variables) >= MIN_VARS:
            files[ICD / f"{producer}-{consumer}.md"] = edge_doc(
                producer, consumer, variables, purposes
            )
    return files


def write() -> int:
    files = outputs()
    ICD.mkdir(parents=True, exist_ok=True)
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    # Remove a document whose boundary fell below the threshold.
    for path in ICD.glob("*.md"):
        if path not in files:
            path.unlink()
    print(f"wrote {len(files)} files under {ICD.relative_to(REPO)}")
    return 0


def check() -> int:
    files = outputs()
    stale = []
    for path, text in files.items():
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            stale.append(path.relative_to(REPO).as_posix())
    for path in ICD.glob("*.md"):
        if path not in files:
            stale.append(path.relative_to(REPO).as_posix())
    if stale:
        print("stale or extra ICD files: " + ", ".join(sorted(stale)))
        return 1
    print(f"icd: fresh ({len(files)} files)")
    return 0


def main(argv: list[str]) -> int:
    if "--check" in argv:
        return check()
    return write()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
