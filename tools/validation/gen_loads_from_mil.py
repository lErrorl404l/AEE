#!/usr/bin/env python3
"""Build load records from the US military ammunition specifications.

The specifications state a service velocity measured at a fixed distance
from the muzzle, and a pressure limit with a named test method. Neither a
bullet mass nor a barrel length is stated, so those fields stay empty.
Every value enters at grade documented, from the cited specification.

Run:  python3 tools/validation/gen_loads_from_mil.py
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
MIL_FILES = [("mil_specs.json", "mil_specs"), ("mil_specs_more.json", "mil_specs_more")]
DB = DATA / "loads.json"

# The cartridge as named in the specification, mapped to our record.
CARTRIDGE = {
    "5.56x45mm NATO": "556x45_nato",
    "7.62x51mm NATO": "762x51_nato",
    "9x19mm NATO": "9x19",
    ".50 BMG (12.7x99mm NATO)": "50_bmg",
}


def projectile_token(projectile):
    return re.sub(r"[^a-z0-9]+", "_", (projectile or "unknown").lower()).strip("_")


def velocity_reference(notes):
    m = re.search(r"measured\s+([0-9.]+ ?(?:ft|m)[^,.;]*)", notes)
    return m.group(1).strip() if m else ""


def pressure_reference(notes, value):
    if value is None:
        return ""
    for sentence in re.split(r"(?<=[.;])\s+", notes):
        m = re.search(r"(.*?)\bis\s+([0-9.]+)\s*MPa", sentence)
        if m and abs(float(m.group(2)) - value) < 0.05:
            return re.sub(r"^(The|Chamber pressure)\s+", "", m.group(1)).strip()
    return ""


def documented(value, unit, source):
    return {"value": value, "unit": unit, "source": source, "grade": "documented"}


def main():
    by_name = {
        n.lower(): r["cartridge_id"]
        for r in json.loads((DATA / "cartridges.json").read_text(encoding="utf-8"))
        for n in r.get("names", [])
    }
    loads = []
    skipped = []
    for name, source_id in MIL_FILES:
        path = DATA / "sources" / name
        if not path.exists():
            continue
        for doc in json.loads(path.read_text(encoding="utf-8"))["documents"]:
            cid = CARTRIDGE.get(doc["cartridge"]) or by_name.get(
                doc["cartridge"].lower()
            )
            if cid is None:
                skipped.append(doc["cartridge"])
                continue
            projectile = doc.get("projectile") or "unknown"
            values = {
                "cartridge": documented(doc["cartridge"], "name", source_id),
                "projectile": documented(projectile, "designation", source_id),
            }
            if doc.get("muzzle_velocity_ms") is not None:
                values["service_velocity_ms"] = documented(
                    doc["muzzle_velocity_ms"], "m/s", source_id
                )
                ref = velocity_reference(doc.get("notes", ""))
                if ref:
                    values["velocity_reference"] = documented(
                        ref, "reference", source_id
                    )
            if doc.get("pressure_mpa") is not None:
                values["service_pressure_mpa"] = documented(
                    doc["pressure_mpa"], "MPa", source_id
                )
                ref = pressure_reference(doc.get("notes", ""), doc["pressure_mpa"])
                if ref:
                    values["pressure_reference"] = documented(ref, "method", source_id)
            if doc.get("twist_in") is not None:
                values["twist_in"] = documented(
                    doc["twist_in"], "inches per turn", source_id
                )
            loads.append(
                {
                    "load_id": f"{cid}_{projectile_token(projectile)}",
                    "cartridge_id": cid,
                    "projectile": projectile,
                    "note": f"{doc['spec']} ({doc['title']}): {doc.get('notes', '')}",
                    "values": values,
                }
            )
    loads.sort(key=lambda r: r["load_id"])
    DB.write_text(json.dumps(loads, indent=1) + "\n", encoding="utf-8")
    print(
        f"loads: {len(loads)}" + (f", skipped cartridges: {skipped}" if skipped else "")
    )


if __name__ == "__main__":
    main()
