#!/usr/bin/env python3
"""The reproducible extraction harness for the engine field guide.

It reads the cited corpus from the game install, names each source by its PBO
and entry (never by a path on one machine), and writes a scratch tree plus
``manifest.json``.  ``--check`` re-runs the extraction and reports drift.

Modes:

    build                       build manifest.json from the target list
    --check                     re-run and compare against manifest.json
    pbo <pbo> <entry>           extract one entry and print its byte size
    derapify <pbo> <entry>      derapify a config entry to the scratch tree
    strings <binary> <regex>    count the distinct matching strings
    decomp <binary> <function>  decompile one named function (targeted r2)

The game install root comes from ``ARMA3_GAME_ROOT``.  The scratch tree comes
from ``AEE_FG_SCRATCH`` (default ``/tmp/opencode/fg-scratch``).

Run from the repo root:

    ARMA3_GAME_ROOT="/path/to/Arma 3" python3 tools/field-guide/extract.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "tools" / "field-guide" / "manifest.json"
ROOT_ENV = "ARMA3_GAME_ROOT"
SCRATCH_ENV = "AEE_FG_SCRATCH"
DEFAULT_SCRATCH = Path("/tmp/opencode/fg-scratch")
STRINGS_MIN_LEN = 4

# The cited corpus.  A page cites a PBO entry, a config key, an exe fact or a
# command; the harness reproduces each from the game install.
TARGETS: list[dict[str, str]] = [
    {"kind": "pbo", "pbo": "Dta/bin.pbo", "entry": "config.bin"},
    {"kind": "derapify", "pbo": "Dta/bin.pbo", "entry": "config.bin"},
    {"kind": "pbo", "pbo": "Addons/ui_f.pbo", "entry": "config.bin"},
    {"kind": "derapify", "pbo": "Addons/ui_f.pbo", "entry": "config.bin"},
    {"kind": "strings", "binary": "arma3_x64.exe", "regex": "^Cfg[A-Z]"},
]


def _die(message: str) -> None:
    print(f"extract: {message}", file=sys.stderr)
    sys.exit(1)


def _root() -> Path:
    root = os.environ.get(ROOT_ENV, "").strip()
    if not root:
        _die(f"{ROOT_ENV} is not set; name the game install root")
    path = Path(root)
    if not path.is_dir():
        _die(f"the game install root does not exist: {root}")
    return path


def _scratch() -> Path:
    scratch = Path(os.environ.get(SCRATCH_ENV, str(DEFAULT_SCRATCH)))
    scratch.mkdir(parents=True, exist_ok=True)
    return scratch


def _cat(root: Path, pbo: str, entry: str) -> bytes:
    source = root / pbo
    if not source.is_file():
        _die(f"PBO not found: {pbo}")
    result = subprocess.run(["armake", "cat", str(source), entry], capture_output=True)
    if result.returncode != 0 or not result.stdout:
        _die(f"armake cat failed for {pbo}:{entry}")
    return result.stdout


def extract_pbo(root: Path, pbo: str, entry: str, scratch: Path) -> bytes:
    data = _cat(root, pbo, entry)
    target = scratch / Path(pbo).name
    target.mkdir(parents=True, exist_ok=True)
    (target / Path(entry).name).write_bytes(data)
    return data


def derapify(root: Path, pbo: str, entry: str, scratch: Path) -> str:
    data = _cat(root, pbo, entry)
    result = subprocess.run(["armake", "derapify"], input=data, capture_output=True)
    if result.returncode != 0 or not result.stdout:
        _die(f"armake derapify failed for {pbo}:{entry}")
    text = result.stdout.decode("utf-8", "replace")
    target = scratch / Path(pbo).name
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{Path(entry).name}.cpp").write_text(text, encoding="utf-8")
    return text


def extract_strings(root: Path, binary: str, regex: str) -> list[str]:
    source = root / binary
    if not source.is_file():
        _die(f"binary not found: {binary}")
    result = subprocess.run(
        ["strings", "-n", str(STRINGS_MIN_LEN), str(source)], capture_output=True
    )
    pattern = re.compile(regex)
    text = result.stdout.decode("utf-8", "replace")
    return sorted({line for line in text.splitlines() if pattern.search(line)})


def _resolve_function(source: Path, function: str) -> str:
    if function.startswith("0x"):
        return function
    result = subprocess.run(
        ["r2", "-q", "-e", "scr.color=0", "-c", f"is~{function}", str(source)],
        capture_output=True,
    )
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split()
        tokens = [token for token in parts if token.startswith("0x")]
        if tokens:
            # The last 0x token is the virtual address r2 seeks to.
            return tokens[-1]
    _die(f"function not found in {source.name}: {function}")


def decompile(root: Path, binary: str, function: str) -> str:
    source = root / binary
    if not source.is_file():
        _die(f"binary not found: {binary}")
    address = _resolve_function(source, function)
    result = subprocess.run(
        [
            "r2",
            "-q",
            "-e",
            "scr.color=0",
            "-c",
            f"s {address}; af; pdg",
            str(source),
        ],
        capture_output=True,
    )
    text = result.stdout.decode("utf-8", "replace")
    if not text.strip():
        _die(f"decomp returned nothing for {function}")
    return text


def _target_entry(
    target: dict[str, str], root: Path, scratch: Path
) -> dict[str, object]:
    kind = target["kind"]
    if kind == "pbo":
        data = extract_pbo(root, target["pbo"], target["entry"], scratch)
        return {
            "kind": kind,
            "pbo": target["pbo"],
            "entry": target["entry"],
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "command": f"armake cat {target['pbo']} {target['entry']}",
        }
    if kind == "derapify":
        text = derapify(root, target["pbo"], target["entry"], scratch)
        data = text.encode("utf-8")
        return {
            "kind": kind,
            "pbo": target["pbo"],
            "entry": target["entry"],
            "size": len(data),
            "lines": text.count("\n") + 1,
            "sha256": hashlib.sha256(data).hexdigest(),
            "command": f"armake cat {target['pbo']} {target['entry']} | armake derapify",
        }
    if kind == "strings":
        hits = extract_strings(root, target["binary"], target["regex"])
        return {
            "kind": kind,
            "binary": target["binary"],
            "regex": target["regex"],
            "count": len(hits),
            "command": f"strings -n {STRINGS_MIN_LEN} {target['binary']} | grep -E {target['regex']}",
        }
    if kind == "decomp":
        text = decompile(root, target["binary"], target["function"])
        data = text.encode("utf-8")
        return {
            "kind": kind,
            "binary": target["binary"],
            "function": target["function"],
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "command": f"r2 -q -e scr.color=0 -c 's <addr>; af; pdg' {target['binary']}",
        }
    _die(f"unknown target kind: {kind}")
    return {}


def _key(entry: dict[str, object]) -> tuple[str, str, str]:
    return (
        str(entry["kind"]),
        str(entry.get("pbo") or entry.get("binary")),
        str(entry.get("entry") or entry.get("regex") or entry.get("function")),
    )


def build_manifest() -> dict[str, object]:
    root = _root()
    scratch = _scratch()
    entries = [_target_entry(target, root, scratch) for target in TARGETS]
    return {"schema": 1, "targets": entries}


def build() -> int:
    manifest = build_manifest()
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(manifest['targets'])} target(s) to {MANIFEST}")
    return 0


def check() -> int:
    if not MANIFEST.exists():
        print(f"missing: {MANIFEST}")
        return 1
    recorded = {
        _key(entry): entry
        for entry in json.loads(MANIFEST.read_text(encoding="utf-8"))["targets"]
    }
    current = {_key(entry): entry for entry in build_manifest()["targets"]}
    drift: list[str] = []
    for key in sorted(set(recorded) | set(current)):
        if key not in current:
            drift.append(f"missing now: {key}")
            continue
        if key not in recorded:
            drift.append(f"new target: {key}")
            continue
        for field in ("size", "sha256", "count", "lines"):
            old = recorded[key].get(field)
            new = current[key].get(field)
            if old != new:
                drift.append(f"{key}: {field} {old} -> {new}")
    if drift:
        for line in drift:
            print(line)
        print(f"drift: {len(drift)} change(s)")
        return 1
    print(f"fresh: {MANIFEST} ({len(current)} target(s))")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="re-run and compare")
    parser.add_argument("mode", nargs="?", help="build, pbo, derapify, strings, decomp")
    parser.add_argument("args", nargs="*")
    parsed = parser.parse_args(argv)

    if parsed.check:
        return check()

    mode = parsed.mode or "build"
    root = _root()
    scratch = _scratch()

    if mode == "build":
        return build()
    if mode == "pbo" and len(parsed.args) == 2:
        data = extract_pbo(root, parsed.args[0], parsed.args[1], scratch)
        print(f"{parsed.args[0]}:{parsed.args[1]} {len(data)} bytes")
        return 0
    if mode == "derapify" and len(parsed.args) == 2:
        text = derapify(root, parsed.args[0], parsed.args[1], scratch)
        print(f"{parsed.args[0]}:{parsed.args[1]} {text.count(chr(10)) + 1} lines")
        return 0
    if mode == "strings" and len(parsed.args) == 2:
        hits = extract_strings(root, parsed.args[0], parsed.args[1])
        print(f"{len(hits)} distinct strings")
        return 0
    if mode == "decomp" and len(parsed.args) == 2:
        print(decompile(root, parsed.args[0], parsed.args[1]))
        return 0

    parser.error(f"unknown mode or wrong arguments: {mode} {parsed.args}")


if __name__ == "__main__":
    sys.exit(main())
