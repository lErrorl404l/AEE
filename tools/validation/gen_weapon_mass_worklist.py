#!/usr/bin/env python3
"""Generate the weapon mass worklist.

The weapons that hold no mass are the research backlog: free recoil cannot
be computed for them. This writes them as a tab separated file grouped by
manufacturer, so one catalogue page can cover a family.

The manufacturer comes from the weapon record. When that field is empty the
maker is read from the leading word of the readable name, which is how the
catalogue entry is written ("Colt Canada C7A1"). A row whose maker cannot
be derived is grouped under "unstated" and counted, so the gap is visible
rather than silently buried.

Output is a worklist, not a data capture: it is ignored by version control
and is regenerated on demand.

Run:  python3 tools/validation/gen_weapon_mass_worklist.py
"""

import csv
import json
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
OUT = Path(__file__).parents[1] / "weapon_worklist" / "mass_missing.tsv"

COLUMNS = ["weapon_id", "name", "manufacturer", "cartridge", "twist_mm", "has_source"]

# One maker, one spelling.  The weapon records carry both "Heckler" (from a
# name-derived key) and "Heckler & Koch" (from the manufacturer field), and
# a worklist that splits one maker across two groups sends two researchers
# to the same catalogue.
MAKER_ALIASES = {
    "heckler": "Heckler & Koch",
    "kalashnikov": "Kalashnikov Concern",
    "izhmash": "Kalashnikov Concern",
}


def maker_of(record):
    """The manufacturer, or the leading name word when the field is empty."""
    maker = (record.get("manufacturer") or "").strip()
    if maker:
        return MAKER_ALIASES.get(maker.lower(), maker)
    names = record.get("names") or []
    if not names:
        return ""
    # "Colt Canada C7A1" -> "Colt"; "Aero Precision AR-15" -> "Aero".
    # A two-word maker is common, so the first word is the safe signal and
    # the full name is searchable in the row anyway.
    first = names[0].split()[0] if names[0].split() else ""
    return MAKER_ALIASES.get(first.lower(), first)


def main():
    weapons = json.loads((DATA / "weapons.json").read_text(encoding="utf-8"))
    rows = []
    unstated = 0
    for record in weapons:
        if "mass_kg" in record["values"]:
            continue
        maker = maker_of(record)
        if not maker:
            unstated += 1
        names = record.get("names") or [record["weapon_id"]]
        rows.append(
            {
                "weapon_id": record["weapon_id"],
                "name": names[0],
                "manufacturer": maker,
                "cartridge": record.get("values", {})
                .get("cartridge", {})
                .get("value", ""),
                "twist_mm": record.get("values", {})
                .get("twist_m", {})
                .get("value", ""),
                "has_source": "no",
            }
        )
    rows.sort(key=lambda r: (r["manufacturer"].lower(), r["weapon_id"]))

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    makers = len({r["manufacturer"] for r in rows if r["manufacturer"]})
    print(
        f"mass worklist: {len(rows)} weapons without a mass, "
        f"{makers} manufacturers, {unstated} unstated; wrote {OUT.name}"
    )


if __name__ == "__main__":
    main()
