#!/usr/bin/env python3
"""Split the weapon verification worklist into research batches.

The worklist is the set of weapons whose barrel twist differs from the
held chambering standard. Those are the only weapons that need their own
entry, because every other weapon is covered by the standard.

The batches are grouped by manufacturer, so one catalogue page often
covers several variants of the same family. Each batch is a tab separated
file with a header.

Run:  python3 tools/validation/gen_weapon_worklist.py
"""

import csv
import json
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
OUT = Path(__file__).parents[1] / "weapon_worklist"
LEADS = DATA / "sources" / "weapon_leads.json"
BATCH_SIZE = 18

COLUMNS = [
    "weapon_id",
    "name",
    "manufacturer",
    "cartridge",
    "corpus_twist_mm",
    "standard_twist_mm",
]


def main():
    leads = json.loads(LEADS.read_text(encoding="utf-8"))["leads"]
    wanted = [
        lead
        for lead in leads
        if lead["verdict"] == "differs_from_standard" and not lead.get("verified")
    ]
    # The chamberings in which we hold no standard. Filling one covers
    # every weapon in that chambering, so this list is worth more than
    # the weapon list.
    chamberings = {}
    for lead in leads:
        if lead["verdict"] == "no_standard":
            chamberings.setdefault(lead["calibre_key"], lead)
    unique = {}
    for lead in wanted:
        unique.setdefault(lead["weapon_id"], lead)
    ordered = sorted(
        unique.values(),
        key=lambda lead: (lead["manufacturer"].lower(), lead["weapon_id"]),
    )
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("batch_*.tsv"):
        stale.unlink()

    batches = [ordered[i : i + BATCH_SIZE] for i in range(0, len(ordered), BATCH_SIZE)]
    for index, batch in enumerate(batches, start=1):
        path = OUT / f"batch_{index:02d}.tsv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(COLUMNS)
            for lead in batch:
                writer.writerow(
                    [
                        lead["weapon_id"],
                        lead["names"][0],
                        lead["manufacturer"],
                        lead["cartridge"],
                        round(lead["twist_m"] * 1000, 2),
                        round((lead["standard_twist_m"] or 0) * 1000, 2),
                    ]
                )
        print(
            f"{path.name}: {len(batch)} weapons, "
            f"{batch[0]['manufacturer']} to {batch[-1]['manufacturer']}"
        )
    path = OUT / "chamberings.tsv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["chambering", "cartridge_name", "corpus_twist_mm"])
        for lead in sorted(chamberings.values(), key=lambda item: item["calibre_key"]):
            writer.writerow([lead["calibre_key"], lead["cartridge"],
                             round(lead["twist_m"] * 1000, 2)])
    print(f"weapons to verify: {len(ordered)}, batches: {len(batches)}, "
          f"chamberings without a standard: {len(chamberings)}")


if __name__ == "__main__":
    main()
