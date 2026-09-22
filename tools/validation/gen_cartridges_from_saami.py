#!/usr/bin/env python3
"""Add the SAAMI cartridges that the CIP register does not cover.

SAAMI Z299.3 and Z299.4 are tier 1 standards and are held. Where CIP
already covers a cartridge the SAAMI value is not entered, because the
two standards measure pressure by different methods. A SAAMI pressure
is not comparable with a CIP pressure, so the two are never merged.

Run:  python3 tools/validation/gen_cartridges_from_saami.py
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SAAMI = DATA / "sources" / "saami_pressure.json"
DB = DATA / "cartridges.json"

CASE_TYPE = {"Z299.3": ("pistol", "pistol"), "Z299.4": ("rimless", "rifle")}


def norm(text):
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def main():
    src = json.loads(SAAMI.read_text(encoding="utf-8"))
    db = json.loads(DB.read_text(encoding="utf-8"))
    by_name = {norm(n): r for r in db for n in r.get("names", [])}
    taken = {r["cartridge_id"] for r in db}
    added = 0
    for row in src["cartridges"]:
        if norm(row["cartridge"]) in by_name:
            continue
        base = (
            re.sub(r"[^a-z0-9]+", "_", row["cartridge"].lower()).strip("_") or "unnamed"
        )
        cid, n = base, 2
        while cid in taken:
            cid = f"{base}_{n}"
            n += 1
        taken.add(cid)
        case_type, cart_type = CASE_TYPE.get(row["standard"], ("rimless", "rifle"))
        db.append(
            {
                "cartridge_id": cid,
                "names": [row["cartridge"]],
                "case_family": "",
                "note": "Added from SAAMI. Not in the CIP register.",
                "classification": {
                    "cip_tab": f"SAAMI {row['standard']}",
                    "case_type": case_type,
                    "cartridge_type": cart_type,
                    "origin_country": "United states",
                    "year_created": "",
                    "classification_source": "saami_pressure",
                },
                "values": {
                    "max_pressure_mpa": {
                        "value": row["map_mpa"],
                        "unit": "MPa",
                        "source": "saami_pressure",
                        "grade": "standard",
                    },
                    "pressure_standard": {
                        "value": "SAAMI",
                        "source": "saami_pressure",
                        "grade": "standard",
                    },
                },
            }
        )
        added += 1
    db.sort(key=lambda r: r["cartridge_id"])
    DB.write_text(json.dumps(db, indent=1) + "\n", encoding="utf-8")
    print(f"cartridges: {len(db)} (added from SAAMI: {added})")


if __name__ == "__main__":
    main()
