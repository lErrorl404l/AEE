#!/usr/bin/env python3
"""Merge the held cannon, autocannon and heavy machine gun loads.

The military ingest rebuilds loads.json from the small-arms specification
set, so a cannon or grenade load that a data sheet defines leaves the
table on every build. Those loads are held in
data/ballistics/sources/loads_cannon.json, with the source each value
cites. This tool merges them back.

A load that the ingest already holds is left alone. The merge is
idempotent, so a second build writes the same bytes.

Run after gen_loads_from_velocity.py:
  python3 tools/validation/gen_loads_from_cannon.py
"""

import json
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources" / "loads_cannon.json"
DB = DATA / "loads.json"


def main():
    held = json.loads(SRC.read_text(encoding="utf-8"))["loads"]
    loads = json.loads(DB.read_text(encoding="utf-8"))
    index = {r["load_id"]: r for r in loads}
    added = 0
    for record in held:
        if record["load_id"] in index:
            continue
        index[record["load_id"]] = record
        added += 1
    out = sorted(index.values(), key=lambda r: r["load_id"])
    DB.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"loads: {len(out)} (cannon loads restored: {added})")


if __name__ == "__main__":
    main()
