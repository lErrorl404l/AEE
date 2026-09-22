#!/usr/bin/env python3
"""Add published bullet lengths to the projectile records.

Only manufacturer sources enter. The JBM rows are a tier 5 compilation,
so they are left out until an independent source states the same length.

Run after gen_projectiles.py:
  python3 tools/validation/gen_lengths.py
"""

import json
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
LENGTHS = DATA / "sources" / "bullet_lengths.json"
DB = DATA / "projectiles.json"
GRAIN_TO_G = 0.06479891
SOURCES = {"berger_chart": "berger_bullets", "nosler_catalog": "nosler_bullets"}


def main():
    src = json.loads(LENGTHS.read_text(encoding="utf-8"))
    db = json.loads(DB.read_text(encoding="utf-8"))
    index = {}
    for rec in db:
        values = rec["values"]
        diameter = values.get("diameter_mm", {}).get("value")
        mass = values.get("mass_g", {}).get("value")
        if diameter is None or mass is None:
            continue
        key = (rec.get("manufacturer", "").lower(), round(diameter / 25.4, 3))
        index.setdefault(key, []).append((rec, mass / GRAIN_TO_G))
    added = 0
    skipped = 0
    for row in src["bullets"]:
        source_id = SOURCES.get(row.get("source_id"))
        if not source_id:
            skipped += 1
            continue
        key = (row["manufacturer"].lower(), round(row["diameter_in"], 3))
        for rec, mass_gr in index.get(key, []):
            if abs(mass_gr - row["mass_gr"]) > 0.01 * row["mass_gr"]:
                continue
            if "length_mm" in rec["values"]:
                break
            rec["values"]["length_mm"] = {
                "value": round(row["length_in"] * 25.4, 4),
                "unit": "mm",
                "source": source_id,
                "grade": "claimed",
            }
            added += 1
            break
    DB.write_text(json.dumps(db, indent=1) + "\n", encoding="utf-8")
    print(f"lengths added: {added} (rows from a compilation, left out: {skipped})")


if __name__ == "__main__":
    main()
