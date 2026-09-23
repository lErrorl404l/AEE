#!/usr/bin/env python3
"""Report the chamberings the weapon catalogue cannot resolve.

The weapon record keeps one cartridge_id. Where the maker's chambering
string does not reach a register record, the id stays empty and the
weapon falls back to its own twist alone. This tool writes the gap so the
research has a target, and records the candidates a near miss reached.

Two statuses:

  ambiguous             the string reaches more than one register record.
                        Two records claim one key, or the maker string
                        names several chamberings. A human decides, or
                        the register duplicates are merged.
  absent_from_register  no record states this chambering. It needs a new
                        record from CIP, SAAMI or an equivalent standard.

Run after gen_chambering_aliases is applied and before the designations:

  python3 tools/validation/gen_chambering_gaps.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import chambering  # noqa: E402  - shared canonical form

DATA = Path(__file__).parents[2] / "data" / "ballistics"
WEAPONS = DATA / "weapons.json"
CARTRIDGES = DATA / "cartridges.json"
OUT_JSON = DATA / "sources" / "chambering_gaps.json"
OUT_MD = DATA / "CHAMBERING_GAPS.md"


def main():
    weapons = json.loads(WEAPONS.read_text(encoding="utf-8"))
    cartridges = json.loads(CARTRIDGES.read_text(encoding="utf-8"))
    index = chambering.build_index(cartridges)
    aliases = chambering.load_aliases()

    gaps = defaultdict(lambda: {"weapons": [], "candidates": set()})
    resolved = 0
    for record in weapons:
        if record.get("cartridge_id"):
            resolved += 1
            continue
        # The record is blank, so it is a gap whatever the string resolves
        # to on its own. A standalone hit that the join did not apply is
        # still a blank id the consumer cannot use.
        text = record.get("values", {}).get("cartridge", {}).get("value", "")
        _cid, candidates = chambering.resolve(text, index, aliases)
        entry = gaps[text or "(blank)"]
        entry["weapons"].append(record["weapon_id"])
        entry["candidates"].update(candidates)

    rows = []
    for text, entry in sorted(gaps.items()):
        candidates = sorted(entry["candidates"])
        rows.append(
            {
                "chambering": text,
                "canonical_key": chambering.canonical(text),
                "weapons": sorted(entry["weapons"]),
                "count": len(entry["weapons"]),
                "status": "ambiguous" if candidates else "absent_from_register",
                "candidate_ids": candidates,
                "note": "",
            }
        )
    rows.sort(key=lambda r: (-r["count"], r["chambering"]))

    OUT_JSON.write_text(
        json.dumps(
            {
                "retrieved": "2026-09-23",
                "weapons_resolved": resolved,
                "weapons_unresolved": sum(r["count"] for r in rows),
                "gaps": rows,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    ambiguous = [r for r in rows if r["status"] == "ambiguous"]
    absent = [r for r in rows if r["status"] == "absent_from_register"]
    lines = [
        "# Chambering gaps",
        "",
        "The weapon records whose chambering does not reach a cartridge",
        "record. Each needs either a decision or a new sourced record. The",
        "register is the source of the standard twist, so a weapon here",
        "falls back to its own twist alone.",
        "",
        f"- Weapons joined to a cartridge record: {resolved}",
        f"- Weapons unresolved: {sum(r['count'] for r in rows)}",
        f"- Distinct unresolved chamberings: {len(rows)}",
        f"- Ambiguous: {len(ambiguous)}",
        f"- Absent from the register: {len(absent)}",
        "",
        "## Ambiguous",
        "",
        "Two register records claim one key, or the maker name lists several",
        "chamberings. A decision is needed. Nothing is guessed.",
        "",
    ]
    for row in ambiguous:
        lines.append(f"- `{row['chambering']}` ({row['count']} weapons)")
        lines.append(f"  - candidates: {', '.join(row['candidate_ids'])}")
    lines += [
        "",
        "## Absent from the register",
        "",
        "A new record is needed,",
        "with a held source.",
        "",
    ]
    for row in absent:
        lines.append(f"- `{row['chambering']}` ({row['count']} weapons)")

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"chambering gaps: {len(rows)} distinct, "
        f"{sum(r['count'] for r in rows)} weapons "
        f"({len(ambiguous)} ambiguous, {len(absent)} absent); "
        f"joined {resolved}"
    )


if __name__ == "__main__":
    main()
