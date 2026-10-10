#!/usr/bin/env python3
"""Generate the magazine loaded-mass projection (ADR-037).

The corpus data/ballistics/sources/magazine_mass.json holds the published
magazine masses. A magazine is weighed LOADED, not empty. The loaded mass
is the held ``loaded_mass_g`` where it is held; otherwise it is DERIVED from
the held empty mass plus the held round mass for the chambering:

    loaded_mass_g = empty_mass_g + capacity * round_mass_g

The round mass comes from the ``cases`` array, keyed by the chambering. A
record with neither a loaded mass nor an empty mass is a lead and yields no
row. No number is invented and no engine value is copied.

The projection is grouped by the same ``calibre_key`` plus capacity the
runtime resolver (tools/validation/gen_runtime_magazines.py) uses, so the
engine mass and the scripted load model share one projection.

Run:  python3 tools/validation/gen_magazine_masses.py
      python3 tools/validation/gen_magazine_masses.py --check
Exit 0 when fresh, 1 when stale or missing under --check.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Sequence

REPO = Path(__file__).parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools import schemas  # noqa: E402
from tools.validation.gen_runtime_magazines import calibre_key  # noqa: E402

BALL = REPO / "data" / "ballistics"
SOURCE = BALL / "sources" / "magazine_mass.json"
OUT = BALL / "magazine_masses.json"

SCHEMA = schemas.BALLISTICS_MAGAZINE_MASS


def case_key(cartridge: str) -> str:
    """The chambering key of a case record, ignoring the variant in brackets."""
    return calibre_key(cartridge.split("(")[0])


def round_masses(cases: Sequence[dict[str, object]]) -> dict[str, dict[str, object]]:
    """Return the held round mass per chambering key.

    Several cases can share a chambering; the projection keeps the median of
    their held round masses and the source of the case that carries it, so no
    number is invented.
    """
    grouped: dict[str, list[tuple[float, str, str]]] = defaultdict(list)
    for case in cases:
        mass = case.get("round_mass_g")
        if not isinstance(mass, (int, float)) or isinstance(mass, bool):
            continue
        source = case.get("source_id")
        cartridge = case.get("cartridge")
        if not isinstance(source, str) or not isinstance(cartridge, str):
            continue
        grouped[case_key(cartridge)].append((float(mass), source, cartridge))
    out: dict[str, dict[str, object]] = {}
    for key, rows in grouped.items():
        values = [row[0] for row in rows]
        median = statistics.median(values)
        representative = min(rows, key=lambda row: (abs(row[0] - median), row[1]))
        out[key] = {
            "round_mass_g": median,
            "source_id": representative[1],
            "cartridge": representative[2],
        }
    return out


def build() -> dict[str, object]:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    sources = payload["sources"]
    magazines = payload["magazines"]
    cases = payload["cases"]

    grade_of = {str(source["source_id"]): str(source["grade"]) for source in sources}
    rounds = round_masses(cases)

    rows: list[dict[str, object]] = []
    leads: list[dict[str, object]] = []
    for record in magazines:
        item = str(record["item"])
        chambering = str(record["chambering"])
        capacity = int(record["capacity"])
        cal = calibre_key(chambering)
        loaded = record.get("loaded_mass_g")
        if loaded is not None:
            rows.append(
                {
                    "item": item,
                    "chambering": chambering,
                    "capacity": capacity,
                    "calibre_key": cal,
                    "loaded_mass_g": float(loaded),
                    "basis": "published",
                    "source_id": str(record["source_id"]),
                    "locator": "loaded_mass_g",
                    "grade": grade_of[str(record["source_id"])],
                }
            )
            continue
        empty = record.get("empty_mass_g")
        held_round = rounds.get(cal)
        if empty is not None and held_round is not None:
            round_g = float(held_round["round_mass_g"])
            rows.append(
                {
                    "item": item,
                    "chambering": chambering,
                    "capacity": capacity,
                    "calibre_key": cal,
                    "loaded_mass_g": float(empty) + capacity * round_g,
                    "basis": "derived",
                    "source_id": str(held_round["source_id"]),
                    "locator": f"empty_mass_g + {capacity} * round_mass_g ({held_round['cartridge']})",
                    "grade": "derived",
                }
            )
            continue
        leads.append(
            {
                "item": item,
                "chambering": chambering,
                "capacity": capacity,
                "reason": "no loaded mass and no derivable round mass",
            }
        )

    grouped: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["calibre_key"]), int(row["capacity"]))].append(row)
    groups: list[dict[str, object]] = []
    for (cal, capacity), members in sorted(grouped.items()):
        ordered = sorted(
            members, key=lambda row: (float(row["loaded_mass_g"]), str(row["item"]))
        )
        median = statistics.median([float(row["loaded_mass_g"]) for row in ordered])
        representative = ordered[(len(ordered) - 1) // 2]
        groups.append(
            {
                "calibre_key": cal,
                "capacity": capacity,
                "round_mass_g": rounds.get(cal, {}).get("round_mass_g"),
                "loaded_mass_g": median,
                "count": len(ordered),
                "basis": representative["basis"],
                "source_id": representative["source_id"],
                "locator": representative["locator"],
                "grade": representative["grade"],
            }
        )

    return {
        "schema": SCHEMA,
        "note": (
            "The magazine loaded-mass projection. Generated by "
            "tools/validation/gen_magazine_masses.py from "
            "data/ballistics/sources/magazine_mass.json. Do not edit by hand. "
            "A magazine is weighed loaded. The round masses come from the held "
            "cases array, keyed by the chambering."
        ),
        "rows": rows,
        "groups": groups,
        "leads": leads,
    }


def render(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=1, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the magazine loaded-mass projection."
    )
    parser.add_argument(
        "--check", action="store_true", help="verify freshness; write nothing"
    )
    args = parser.parse_args(argv)

    try:
        text = render(build())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"magazine masses: cannot build: {exc}")
        return 1

    if args.check:
        if not OUT.is_file():
            print(f"magazine masses: {OUT} is missing; run the generator")
            return 1
        if OUT.read_text(encoding="utf-8") != text:
            print(f"magazine masses: {OUT} is stale; run the generator")
            return 1
        payload = json.loads(text)
        print(
            f"magazine masses: {len(payload['rows'])} rows, "
            f"{len(payload['groups'])} groups, {len(payload['leads'])} leads (fresh)"
        )
        return 0

    OUT.write_text(text, encoding="utf-8")
    payload = json.loads(text)
    print(
        f"magazine masses: wrote {OUT.name} ({len(payload['rows'])} rows, "
        f"{len(payload['groups'])} groups, {len(payload['leads'])} leads)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
