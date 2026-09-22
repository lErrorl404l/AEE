#!/usr/bin/env python3
"""Unlock the NATO chamberings with the held EPVAT documents.

AEP-97 Vol 12 and UK Def Stan 05-101 Part 1 are primary copies and are
held. They give the EPVAT service pressure (mean plus three standard
deviations) and the weapon proof pressure per calibre.

The NATO chambering is a different cartridge from its civilian
equivalent, so the value lands on the NATO record, not on .223
Remington or .308 Winchester. Where a cartridge already holds a value
from another standard, the disagreement is recorded, never merged.

Run after gen_cartridges_from_saami.py:
  python3 tools/validation/gen_cartridges_nato.py
"""

import json
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
EPVAT = DATA / "sources" / "nato_epvat.json"
DB = DATA / "cartridges.json"
CONFLICTS = DATA / "conflicts.json"

MAP = {
    "5.56x45mm NATO": "556x45_nato",
    "7.62x51mm NATO": "762x51_nato",
    "9x19mm NATO": "9x19",
    "12.7x99mm NATO": "50_bmg",
}


def standard(value, unit):
    return {"value": value, "unit": unit, "source": "nato_epvat", "grade": "standard"}


def main():
    docs = json.loads(EPVAT.read_text(encoding="utf-8"))["documents"]
    db = json.loads(DB.read_text(encoding="utf-8"))
    by_id = {r["cartridge_id"]: r for r in db}
    conflicts = [
        c
        for c in json.loads(CONFLICTS.read_text(encoding="utf-8"))
        if c.get("source_b") != "nato_epvat"
    ]
    upgraded = 0
    for doc in docs:
        rec = by_id.get(MAP.get(doc["calibre"]))
        if rec is None:
            continue
        values = rec["values"]
        service = doc.get("service_pressure_mpa")
        if service is not None:
            existing = values.get("max_pressure_mpa")
            if existing is None or existing.get("grade") == "unverified":
                values["max_pressure_mpa"] = standard(service, "MPa")
                values["pressure_standard"] = standard("NATO EPVAT", "name")
                upgraded += 1
            elif abs(existing["value"] - service) > 0.01 * existing["value"]:
                conflicts.append(
                    {
                        "entity": rec["cartridge_id"],
                        "field": "max_pressure_mpa",
                        "value_a": existing["value"],
                        "source_a": existing["source"],
                        "value_b": service,
                        "source_b": "nato_epvat",
                        "resolution": "Kept the existing standard value. A CIP or SAAMI pressure "
                        "and a NATO EPVAT pressure use different test methods.",
                        "rule_applied": "Record both. Do not average.",
                        "date": "2026-09-22",
                    }
                )
        if doc.get("proof_pressure_mpa") is not None:
            values.setdefault(
                "proof_pressure_mpa", standard(doc["proof_pressure_mpa"], "MPa")
            )

    # A held service specification states the intended barrel twist for
    # its cartridge. M855 is one turn in seven inches. It upgrades a
    # twist that is otherwise unverified.
    mil_map = {"5.56x45mm NATO": "556x45_nato", "7.62x51mm NATO": "762x51_nato"}
    for filename, source_id in (
        ("mil_specs.json", "mil_specs"),
        ("mil_specs_more.json", "mil_specs_more"),
    ):
        path = DATA / "sources" / filename
        if not path.exists():
            continue
        for doc in json.loads(path.read_text(encoding="utf-8"))["documents"]:
            if doc.get("twist_in") is None:
                continue
            rec = by_id.get(mil_map.get(doc["cartridge"]))
            if rec is None:
                continue
            existing = rec["values"].get("standard_twist_m")
            if existing is None or existing.get("grade") == "unverified":
                rec["values"]["standard_twist_m"] = {
                    "value": round(doc["twist_in"] * 0.0254, 4),
                    "unit": "m per turn",
                    "source": source_id,
                    "grade": "documented",
                }

    DB.write_text(json.dumps(db, indent=1) + "\n", encoding="utf-8")
    CONFLICTS.write_text(json.dumps(conflicts, indent=1) + "\n", encoding="utf-8")
    print(f"NATO records upgraded: {upgraded}, conflicts: {len(conflicts)}")


if __name__ == "__main__":
    main()
