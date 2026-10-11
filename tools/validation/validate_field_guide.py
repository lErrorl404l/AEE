#!/usr/bin/env python3
"""Per-page contract for the engine field guide.

Every ``docs/wiki/field-guide/features/*.qmd`` page must carry:

  - the four contract headings, in this order:
      ``## What works``
      ``## What does not work``
      ``## Limitations``
      ``## Breaks visually``
  - at least one ``{src:<kind>:<ref>}`` citation token per contract section
  - a ``## Sources`` table with a ``verify`` column and at least one row
  - the front-matter ``feature:`` and ``verify:`` fields
  - a resolving ``verify`` reference on every ``## Sources`` row

The ceiling page is checked for its own contract: every "cannot" bullet
names a substitute, and no line makes a pixel claim.

Run: python3 tools/validation/validate_field_guide.py
Exit 0 when every page holds, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs" / "wiki" / "field-guide"
FEATURES = GUIDE / "features"
CEILING = GUIDE / "ceiling.qmd"
VERIFY_PY = REPO / "tests" / "docker" / "verify.py"

CONTRACT = (
    "## What works",
    "## What does not work",
    "## Limitations",
    "## Breaks visually",
)
SOURCES = "## Sources"
EXPECTED_HEADINGS = [h[3:].strip() for h in CONTRACT] + ["Sources"]

TOKEN = re.compile(r"\{src:(pbo|cfg|exe|cmd|adr|probe|script):([^}\s]+)\}")
_H2 = re.compile(r"^##\s+(\S.*?)\s*$")
_VERIFY_KINDS = {"extract", "strings", "test", "probe", "kernel"}
_SUBSTITUTES = ("operator", "visual_diff", "probe", "UNKNOWN")


def _front_matter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
    return fields


def _resolve(cell: str) -> str | None:
    """Return an error string when a verify cell does not resolve, else None."""
    kind, _, ref = cell.partition(":")
    kind = kind.strip().lower()
    ref = ref.strip()
    if kind in ("extract", "strings"):
        return None
    if kind == "test":
        if ref and (REPO / ref).is_file():
            return None
        return f"verify 'test' reference does not exist: {ref or '(none)'}"
    if kind == "kernel":
        if ref and (REPO / ref).is_file():
            return None
        return f"verify 'kernel' reference does not exist: {ref or '(none)'}"
    if kind == "probe":
        if ref and ref in VERIFY_PY.read_text(encoding="utf-8"):
            return None
        return (
            f"verify 'probe' is not gated by tests/docker/verify.py: {ref or '(none)'}"
        )
    return f"unknown verify kind: {cell or '(empty)'}"


def _check_feature(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    errors: list[str] = []

    fields = _front_matter(text)
    for key in ("feature", "verify"):
        if not fields.get(key):
            errors.append(f"front matter is missing '{key}:'")
    if fields.get("verify") and fields["verify"] not in _VERIFY_KINDS:
        errors.append(f"front matter verify is not a kind: {fields['verify']}")

    h2 = [(i, m.group(1)) for i, line in enumerate(lines) if (m := _H2.match(line))]
    names = [name for _, name in h2]
    if names != EXPECTED_HEADINGS:
        errors.append(
            "headings are not exactly the four contract headings in order "
            f"plus ## Sources: {names}"
        )
        return errors

    position = {name: i for i, name in h2}
    bounds = [position[h] for h in EXPECTED_HEADINGS]
    for k, heading in enumerate(EXPECTED_HEADINGS[:-1]):
        body = "\n".join(lines[bounds[k] + 1 : bounds[k + 1]])
        if not TOKEN.search(body):
            errors.append(f"{CONTRACT[k]} carries no {{src:...}} citation token")

    table = [
        line
        for line in lines[position["Sources"] + 1 :]
        if line.strip().startswith("|")
    ]
    if len(table) < 3:
        errors.append("## Sources needs a header row and at least one data row")
        return errors
    header = [cell.strip() for cell in table[0].strip().strip("|").split("|")]
    lowered = [cell.lower() for cell in header]
    if "verify" not in lowered:
        errors.append("## Sources table has no verify column")
        return errors
    verify_col = lowered.index("verify")
    for row in table[2:]:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) != len(header):
            errors.append(
                f"## Sources row has {len(cells)} cells, the header has {len(header)}"
            )
            continue
        problem = _resolve(cells[verify_col])
        if problem:
            errors.append(problem)
    return errors


def _check_ceiling(path: Path) -> list[str]:
    if not path.is_file():
        return ["ceiling.qmd is missing"]
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    marker = "## What no wiki can predict"
    if marker in text:
        section = text.split(marker, 1)[1]
        for line in section.splitlines():
            stripped = line.strip()
            if stripped.startswith("-") and stripped.strip("- ").strip():
                if not any(token in stripped for token in _SUBSTITUTES):
                    errors.append(f"a 'cannot' bullet names no substitute: {stripped}")

    for line in text.splitlines():
        lowered = line.lower()
        if "pixel" in lowered and not any(
            token in lowered for token in ("cannot", "no wiki", "operator")
        ):
            errors.append(f"a pixel line is not a 'cannot': {line.strip()}")
    return errors


def main() -> int:
    problems: dict[str, list[str]] = {}
    pages = sorted(FEATURES.glob("*.qmd"))
    for page in pages:
        errors = _check_feature(page)
        if errors:
            problems[str(page.relative_to(REPO))] = errors
    ceiling_errors = _check_ceiling(CEILING)
    if ceiling_errors:
        problems[str(CEILING.relative_to(REPO))] = ceiling_errors

    if problems:
        for page, errors in problems.items():
            print(f"{page}:")
            for error in errors:
                print(f"  - {error}")
        print(f"field guide: FAIL ({len(problems)} page(s))")
        return 1

    print(f"field guide: PASS ({len(pages)} feature page(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
