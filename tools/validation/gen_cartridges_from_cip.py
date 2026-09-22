#!/usr/bin/env python3
"""Merge the held CIP TDCC register into the cartridge database.

The CIP register is the source of truth for cartridge identity, case
dimensions and pressure. This tool adds every CIP cartridge that is not
yet present, classifies it from its CIP tab, and attaches the CIP
pressure at grade standard. Curated records are matched by name and are
never overwritten.

Run:  python3 tools/validation/gen_cartridges_from_cip.py
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
CIP = DATA / "sources" / "cip" / "cip_tdcc_all_tabs.json"
DB = DATA / "cartridges.json"

# Tab name to (case type, cartridge type).
TABS = {
    "Tab I rimless": ("rimless", "rifle"),
    "Tab II rimmed": ("rimmed", "rifle"),
    "Tab III belted": ("belted", "rifle"),
    "Tab IV pistol/revolver": ("pistol", "pistol"),
    "Tab V rimfire (crusher)": ("rimfire", "rimfire"),
    "Tab V rimfire (transducer)": ("rimfire", "rimfire"),
    "Tab VI industrial": ("industrial", "industrial"),
    "Tab VII shot": ("shot", "shotgun"),
    "Tab VIII alarm": ("alarm", "alarm"),
    "Tab IX dust shot": ("dust shot", "other"),
    "Tab X other weapons": ("other", "other"),
    "Tab XI caseless": ("caseless", "caseless"),
}


def ident(name, taken):
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "unnamed"
    out, n = base, 2
    while out in taken:
        out = f"{base}_{n}"
        n += 1
    return out


def main():
    cip = json.loads(CIP.read_text(encoding="utf-8"))
    db = json.loads(DB.read_text(encoding="utf-8"))
    # A record with no value and no note is not data. Drop generator
    # leftovers so a rerun is idempotent.
    db = [r for r in db if r.get("values") or r.get("note")]

    by_name = {n.lower(): r for r in db for n in r.get("names", [])}
    taken = {r["cartridge_id"] for r in db}
    added = 0
    for tab, rows in cip.items():
        case_type, cart_type = TABS[tab]
        for row in rows:
            name = row["name"]
            # The held register lists every CIP cartridge. A row without a
            # pressure value has no data yet, so it stays in the register
            # and does not enter the database.
            has_pressure = bool(row.get("ptmax_bar"))
            rec = by_name.get(name.lower())
            if rec is None:
                if not has_pressure:
                    continue
                rec = {
                    "cartridge_id": ident(name, taken),
                    "names": [name],
                    "note": "",
                    "values": {},
                }
                taken.add(rec["cartridge_id"])
                by_name[name.lower()] = rec
                db.append(rec)
                added += 1

            rec["classification"] = {
                "cip_tab": tab,
                "case_type": case_type,
                "cartridge_type": cart_type,
                "origin_country": row.get("country", ""),
                "year_created": (row.get("date") or "")[:4],
                "classification_source": "cip_tdcc",
            }

            values = rec["values"]
            if row.get("ptmax_bar") and "max_pressure_mpa" not in values:
                values["max_pressure_mpa"] = {
                    "value": round(row["ptmax_bar"] / 10, 1),
                    "unit": "MPa",
                    "source": "cip_tdcc",
                    "grade": "standard",
                }
                values["pressure_standard"] = {
                    "value": "CIP",
                    "source": "cip_tdcc",
                    "grade": "standard",
                }

    db.sort(key=lambda r: r["cartridge_id"])
    DB.write_text(json.dumps(db, indent=1) + "\n", encoding="utf-8")
    print(f"cartridges: {len(db)} (added {added})")


if __name__ == "__main__":
    main()
