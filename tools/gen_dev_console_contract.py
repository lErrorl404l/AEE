#!/usr/bin/env python3
"""Generate the AEE dev console command contract (ADR-034, ADR-035).

The dev console has three fixed sets, and each has exactly one source:

  * the **extension command set** the native `aee_dev` extension registers in
    `tools/dev-harness/extension/src/lib.rs` (`init()`), which SQF addresses as
    `"aee_dev" callExtension "<name>"`;
  * the **console verb table** in `fnc_devVerbs.sqf`, the operations the
    dispatcher accepts;
  * the **`AEE_DEV_FUNCS` whitelist** in `fnc_devFuncs.sqf`, the only function
    names `callfunc` may run.

This generator reads those sources and renders the contract into the marked
block of `docs/wiki/research/dev-console-contract.md`.  The doc block is a
projection, never a second copy: a source change that is not regenerated fails
`--check`, so the two lists cannot drift.

Run:
    python3 tools/gen_dev_console_contract.py           # update the doc block
    python3 tools/gen_dev_console_contract.py --check   # fail on drift
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
LIB = ROOT / "tools" / "dev-harness" / "extension" / "src" / "lib.rs"
VERBS = (
    ROOT / "tools" / "dev-harness" / "addons" / "dev" / "functions" / "fnc_devVerbs.sqf"
)
FUNCS = (
    ROOT / "tools" / "dev-harness" / "addons" / "dev" / "functions" / "fnc_devFuncs.sqf"
)
DOC = ROOT / "docs" / "wiki" / "research" / "dev-console-contract.md"

BEGIN = "<!-- BEGIN GENERATED: dev console contract -->"
END = "<!-- END GENERATED: dev console contract -->"

# A registered extension command: `.command("name", handler)`.  The name may
# sit on the next line after the call, so the gap is whitespace, not a space.
COMMAND_RE = re.compile(r'\.command\(\s*"([^"]+)"')
STRING_RE = re.compile(r'"([^"]*)"')


def strip_comments(text: str) -> str:
    """Blank out line and block comments so a prose string is not a hit."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extension_commands() -> list[str]:
    """The extension command names, sorted, from the Rust registration."""
    return sorted(set(COMMAND_RE.findall(strip_comments(_read(LIB)))))


def console_verbs() -> list[str]:
    """The console verb table, in source order, from `fnc_devVerbs.sqf`."""
    return STRING_RE.findall(strip_comments(_read(VERBS)))


def console_funcs() -> list[str]:
    """The `AEE_DEV_FUNCS` whitelist, in source order, from `fnc_devFuncs.sqf`."""
    return STRING_RE.findall(strip_comments(_read(FUNCS)))


def audit() -> list[str]:
    """Return a list of defects (empty when the sources are readable)."""
    errors: list[str] = []
    for path in (LIB, VERBS, FUNCS):
        if not path.is_file():
            errors.append(f"{path.relative_to(ROOT)} is missing")
    if not errors and not extension_commands():
        errors.append("no extension commands found (lib.rs registration scan is empty)")
    if not errors and not console_verbs():
        errors.append("no console verbs found (fnc_devVerbs.sqf scan is empty)")
    if not errors and not console_funcs():
        errors.append("no whitelist names found (fnc_devFuncs.sqf scan is empty)")
    return errors


def _render_list(names: list[str]) -> list[str]:
    return [f"- `{name}`" for name in names] + [""]


def build_block() -> str:
    commands = extension_commands()
    verbs = console_verbs()
    funcs = console_funcs()

    lines: list[str] = [BEGIN, ""]

    lines.append(f"### Extension commands ({len(commands)})")
    lines.append("")
    lines.append(
        "Registered by `init()` in `tools/dev-harness/extension/src/lib.rs`. SQF "
        'addresses one as `"aee_dev" callExtension "<name>"`.'
    )
    lines.append("")
    lines += _render_list(commands)

    lines.append(f"### Console verb table ({len(verbs)})")
    lines.append("")
    lines.append(
        "The operations `fnc_devExec.sqf` accepts, published as `aee_dev_verbs` "
        "by `fnc_devVerbs.sqf`. An operation outside the table is refused."
    )
    lines.append("")
    lines += _render_list(verbs)

    lines.append(f"### Console function whitelist (`AEE_DEV_FUNCS`) ({len(funcs)})")
    lines.append("")
    lines.append(
        "The only function names the `callfunc` verb may run, published as "
        "`aee_dev_funcs` by `fnc_devFuncs.sqf`. A name outside the set is refused."
    )
    lines.append("")
    lines += _render_list(funcs)

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
            print(f"dev console contract: {error}")
        print("dev console contract: FAIL")
        return 1

    if not DOC.is_file():
        print(f"dev console contract: {DOC.relative_to(ROOT)} is missing")
        return 1

    block = build_block()
    doc = _read(DOC)
    present = current_block(doc)
    if present is None:
        print(f"dev console contract: markers missing from {DOC.relative_to(ROOT)}")
        return 1

    if args.check:
        if present != block:
            print("dev console contract: doc block is stale (run without --check)")
            return 1
        print(
            f"dev console contract: PASS ({len(extension_commands())} commands, "
            f"{len(console_verbs())} verbs, {len(console_funcs())} whitelist names)"
        )
        return 0

    DOC.write_text(doc.replace(present, block), encoding="utf-8")
    print(f"dev console contract: wrote {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
