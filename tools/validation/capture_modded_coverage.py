#!/usr/bin/env python3
"""Capture the modded per-class resolution lock from a installed-content scan.

`data/munition/modded_coverage.json` is a regression lock: every modded
CfgWeapons class the weapon and munition tables score, and the catalogue row
the runtime ladder reaches for it. This tool derives it from the same
measurement the coverage report uses, so the lock and the report cannot drift.

Run:
    python3 tools/validation/capture_modded_coverage.py /tmp/all.jsonl
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

REPO = Path(__file__).parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import report_match_coverage as coverage  # noqa: E402

DEFAULT_OUT = REPO / "data" / "munition" / "modded_coverage.json"
TABLES = ("small arms", "carried launchers", "vehicle armament")


def _reason(trace: dict) -> str:
    """Why a munition class resolves to nothing, from the ladder's own trace."""
    layer = trace.get("layer")
    if not layer:
        return "No layer names it: no mapped class, alias or keyword of the query reaches one entry."
    tied = ", ".join(sorted(trace.get("candidates", [])))
    return (
        f"The {layer} layer ties between {tied}, and the runtime refuses a tie "
        f"rather than guessing which store the text means."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("scan", type=Path)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--install")
    args = ap.parse_args()
    if not args.scan.is_file():
        raise SystemExit(f"no scan at {args.scan}")

    previous = {}
    if args.out.is_file():
        previous = json.loads(args.out.read_text(encoding="utf-8"))

    scanned = [
        json.loads(line)
        for line in args.scan.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    scanned = [row for row in scanned if row.get("fmt") == "bin"]
    install = coverage.install_dir(args.install)
    base = coverage.base_sources(install)
    result = coverage.measure(scanned, base)

    tables = {}
    for label in TABLES:
        table = result["tables"][coverage.slug(label)]
        rows = [
            [name, display, decided]
            for name, display, decided, source in table["decided"]
            if source.lower() not in base
        ]
        tables[label] = {
            "resolved": sum(1 for row in rows if row[2]),
            "total": len(rows),
            "rows": rows,
        }

    reasons = {}
    for label in TABLES:
        table = result["tables"][coverage.slug(label)]
        for name, display, decided, source in table["decided"]:
            if decided is not None or source.lower() in base:
                continue
            trace = {}
            if label == "vehicle armament":
                coverage.matcher(
                    coverage.munition_rows(coverage.MUNITION_TABLE), trace=trace
                )(name, display)
            reasons[name] = _reason(trace)

    payload = {
        "note": previous.get("note", ""),
        "captured": datetime.date.today().isoformat(),
        "base_game_pbos": sorted(base),
        "tables": tables,
        "excluded_equipment": {
            kind: sorted([cls, display] for cls, display in members)
            for kind, members in result["excluded"].items()
        },
        "unresolved_reasons": reasons,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    for label in TABLES:
        table = tables[label]
        print(f"{label}: {table['resolved']}/{table['total']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
