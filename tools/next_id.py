#!/usr/bin/env python3
"""Allocate the next free ADR number or probe tag.  Derive, do not hardcode.

Two identifier sequences in this repository must stay unique and gap-free in
the merged tree:

  * ADR numbers   docs/adr/ADR-NNN-<slug>.md
                  (tools/tests/test_adr_numbers.py)
  * probe tags    the rows of
                  tools/dev-harness/addons/dev/functions/fnc_devProbeManifest.sqf
                  (tools/tests/test_probe_classification.py)

A worker in a git worktree sees only its own committed records, so a plain
glob hands the same next value to every concurrent worker.  The values then
collide at merge.  This tool keeps a reservation registry in the git common
directory, which every worktree of the clone shares.  Each caller on the
machine gets a distinct value.

Call this tool instead of writing a literal number into a plan, a filename or
a commit message.

Usage:
    python3 tools/next_id.py adr          # -> 038
    python3 tools/next_id.py probe        # -> P143
    python3 tools/next_id.py list         # committed and reserved values
    python3 tools/next_id.py release adr 038

The value prints as a bare token, so a shell captures it:

    adr=$(python3 tools/next_id.py adr)

Release a reservation when the work is abandoned, or the number is skipped
and the sequence keeps a gap.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ADR_RE = re.compile(r"^ADR-(\d{3})-")
MANIFEST_RE = re.compile(r'"P(\d{3})"')
PROBE_FILE_RE = re.compile(r"aee_p(\d{3})_")

ADR_DIR = Path("docs/adr")
MANIFEST = Path("tools/dev-harness/addons/dev/functions/fnc_devProbeManifest.sqf")
PROBE_DIR = Path("tests/docker/missions/aee_test.Stratis")
REGISTRY_NAME = "aee-id-reservations.json"


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def repo_root(cwd: Path) -> Path:
    return Path(_git(["rev-parse", "--show-toplevel"], cwd))


def registry_path(cwd: Path) -> Path:
    common = Path(_git(["rev-parse", "--git-common-dir"], cwd))
    if not common.is_absolute():
        common = (cwd / common).resolve()
    return common / REGISTRY_NAME


def committed_adr(root: Path) -> list[int]:
    return sorted(
        int(match.group(1))
        for path in (root / ADR_DIR).glob("ADR-*.md")
        if (match := ADR_RE.match(path.name))
    )


def committed_probe(root: Path) -> list[int]:
    values: set[int] = set()
    manifest = root / MANIFEST
    if manifest.exists():
        values.update(
            int(match.group(1)) for match in MANIFEST_RE.finditer(manifest.read_text())
        )
    probe_dir = root / PROBE_DIR
    if probe_dir.exists():
        for path in probe_dir.iterdir():
            if match := PROBE_FILE_RE.search(path.name):
                values.add(int(match.group(1)))
    return sorted(values)


def load_registry(path: Path) -> dict[str, list[int]]:
    if not path.exists():
        return {"adr": [], "probe": []}
    raw = json.loads(path.read_text())
    return {
        "adr": [int(value) for value in raw.get("adr", [])],
        "probe": [int(value) for value in raw.get("probe", [])],
    }


def save_registry(path: Path, data: dict[str, list[int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def next_free(committed: list[int], reserved: list[int]) -> int:
    return max([*committed, *reserved], default=0) + 1


def allocate(kind: str, root: Path, registry: Path) -> str:
    data = load_registry(registry)
    committed = committed_adr(root) if kind == "adr" else committed_probe(root)
    value = next_free(committed, data[kind])
    data[kind].append(value)
    save_registry(registry, data)
    return f"{value:03d}" if kind == "adr" else f"P{value:03d}"


def release(kind: str, value: str, registry: Path) -> bool:
    data = load_registry(registry)
    number = int(value.lstrip("Pp"))
    if number not in data[kind]:
        return False
    data[kind].remove(number)
    save_registry(registry, data)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Allocate the next free ADR number or probe tag."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("adr", help="print the next free ADR number")
    sub.add_parser("probe", help="print the next free probe tag")
    sub.add_parser("list", help="print the committed and reserved values")
    drop = sub.add_parser("release", help="drop a reservation")
    drop.add_argument("kind", choices=("adr", "probe"))
    drop.add_argument("value")
    args = parser.parse_args(argv)

    cwd = Path.cwd()
    registry = registry_path(cwd)

    if args.command in ("adr", "probe"):
        print(allocate(args.command, repo_root(cwd), registry))
        return 0
    if args.command == "list":
        root = repo_root(cwd)
        data = load_registry(registry)
        print(f"adr   committed={committed_adr(root)} reserved={data['adr']}")
        print(
            f"probe committed={[f'P{n:03d}' for n in committed_probe(root)]} "
            f"reserved={[f'P{n:03d}' for n in data['probe']]}"
        )
        return 0
    if not release(args.kind, args.value, registry):
        print(f"{args.value} is not reserved for {args.kind}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
