#!/usr/bin/env python3
"""Add manufacturer velocity loads, each with its test barrel length.

Hornady and Lapua publish a muzzle velocity per load and state the test
barrel. Each row becomes an mv_anchors entry, a barrel length against a
velocity. The values are manufacturer claims.

Run after gen_loads_from_mil.py, which rebuilds the loads table:
  python3 tools/validation/gen_loads_from_velocity.py
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
DB = DATA / "loads.json"
FILES = [
    ("hornady_velocity", "hornady_velocity.json"),
    ("lapua_velocity", "lapua_velocity.json"),
]


def norm(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def token(text):
    return re.sub(r"[^a-z0-9]+", "_", (text or "unknown").lower()).strip("_")


def main():
    cart_by_name = {}
    for rec in json.loads((DATA / "cartridges.json").read_text(encoding="utf-8")):
        for name in rec.get("names", []):
            cart_by_name[norm(name)] = rec["cartridge_id"]

    loads = json.loads(DB.read_text(encoding="utf-8")) if DB.exists() else []
    index = {r["load_id"]: r for r in loads}
    added = 0
    skipped = 0
    for source_id, filename in FILES:
        path = DATA / "sources" / filename
        if not path.exists():
            continue
        for row in json.loads(path.read_text(encoding="utf-8"))["loads"]:
            cid = cart_by_name.get(norm(row["cartridge"]))
            if cid is None:
                skipped += 1
                continue
            load_id = f"{cid}_{token(row['projectile'])}"
            rec = index.get(load_id)
            if rec is None:
                rec = {
                    "load_id": load_id,
                    "cartridge_id": cid,
                    "projectile": row["projectile"],
                    "note": "",
                    "values": {
                        "cartridge": {
                            "value": row["cartridge"],
                            "unit": "name",
                            "source": source_id,
                            "grade": "claimed",
                        },
                        "projectile": {
                            "value": row["projectile"],
                            "unit": "designation",
                            "source": source_id,
                            "grade": "claimed",
                        },
                    },
                }
                index[load_id] = rec
                loads.append(rec)
                added += 1
            anchors = rec["values"].get("mv_anchors", {}).get("value", [])
            if row.get("barrel_mm") is not None and row.get("velocity_ms") is not None:
                anchors.append(
                    {"barrel_mm": row["barrel_mm"], "mv_ms": row["velocity_ms"]}
                )
            rec["values"]["mv_anchors"] = {
                "value": anchors,
                "unit": "mm, m/s",
                "source": source_id,
                "grade": "claimed",
            }
    loads.sort(key=lambda r: r["load_id"])
    DB.write_text(json.dumps(loads, indent=1) + "\n", encoding="utf-8")
    print(
        f"loads: {len(loads)} (from velocity tables: {added}, "
        f"unresolved cartridges: {skipped})"
    )


if __name__ == "__main__":
    main()
