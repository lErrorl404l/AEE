#!/usr/bin/env python3
"""Integrate the values found by research.

Three research outputs feed this tool:

1. bc_found.json: real coefficients found from measured sources, for
   bullets where the database held only a derived value.
2. bullet_lengths_found.json: published bullet lengths from manufacturer
   sources. They replace any length matched by weight alone, which could
   attach the wrong length to a bullet of the same weight.
3. pressure_found.json: real pressures for the cartridges whose register
   row carried none.

A found value always beats a derived one, and a manufacturer length
always beats a weight-only match.

Run after gen_bc_corroboration.py and gen_derived_bc.py:
  python3 tools/validation/gen_found_data.py
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
PROJ = DATA / "projectiles.json"
CART = DATA / "cartridges.json"

# Every CIP datasheet belongs to the one held CIP source.
PRESSURE_SOURCE = {"saami_z299_2": "saami_z299_2"}


def norm(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def source_for(source_id):
    if source_id.startswith("cip_"):
        return "cip_tdcc"
    return PRESSURE_SOURCE.get(source_id, source_id)


def load(name):
    return json.loads((SRC / f"{name}.json").read_text(encoding="utf-8"))


def match_projectile(rows, manufacturer, diameter_in, mass_gr, designation=""):
    """The best record for a found bullet: same maker and diameter, mass
    inside one percent, and the longest shared name token wins."""
    want = norm(designation)
    best, best_score = None, -1
    for rec in rows:
        if rec.get("manufacturer", "").lower() != manufacturer.lower():
            continue
        values = rec["values"]
        diameter = values.get("diameter_mm", {}).get("value")
        mass = values.get("mass_g", {}).get("value")
        if diameter is None or mass is None:
            continue
        if round(diameter / 25.4, 3) != round(diameter_in, 3):
            continue
        if abs(mass / 0.06479891 - mass_gr) > 0.01 * mass_gr:
            continue
        name = norm(rec.get("names", [""])[0])
        score = (
            100
            if want and want == name
            else len(
                set(re.findall(r"[a-z0-9]{4,}", name))
                & set(re.findall(r"[a-z0-9]{4,}", want))
            )
        )
        if score > best_score:
            best, best_score = rec, score
    return best


def main():
    projectiles = json.loads(PROJ.read_text(encoding="utf-8"))
    added_bc = 0
    for row in load("bc_found")["bullets"]:
        rec = match_projectile(
            projectiles,
            row["manufacturer"],
            row["diameter_in"],
            row["mass_gr"],
            row.get("designation", ""),
        )
        if rec is None:
            continue
        for field in ("bc_g1", "bc_g7"):
            found = row.get(field)
            existing = rec["values"].get(field)
            if found is None:
                continue
            # A found value replaces a derived one, and fills a gap.
            if existing is None or existing.get("grade") == "derived":
                rec["values"][field] = {
                    "value": found,
                    "source": row["source_id"],
                    "grade": "measured",
                }
                added_bc += 1

    # Lengths: a part or a full name match beats the weight-only match.
    added_len = 0
    for row in load("bullet_lengths_found")["bullets"]:
        rec = match_projectile(
            projectiles,
            row["manufacturer"],
            row["diameter_in"],
            row["mass_gr"],
            row.get("designation", ""),
        )
        if rec is None or row.get("length_in") is None:
            continue
        rec["values"]["length_mm"] = {
            "value": round(row["length_in"] * 25.4, 4),
            "unit": "mm",
            "source": {
                "berger_chart": "berger_bullets",
                "nosler_catalog": "nosler_bullets",
            }.get(row["source_id"], row["source_id"]),
            "grade": "claimed",
        }
        added_len += 1

    PROJ.write_text(json.dumps(projectiles, indent=1) + "\n", encoding="utf-8")

    cartridges = json.loads(CART.read_text(encoding="utf-8"))
    by_name = {norm(n): r for r in cartridges for n in r.get("names", [])}
    added_press = 0
    for row in load("pressure_found")["cartridges"]:
        rec = by_name.get(norm(row["cartridge"]))
        if rec is None or row.get("map_mpa") is None:
            continue
        if "max_pressure_mpa" in rec["values"]:
            continue
        source_id = source_for(row["source_id"])
        rec["values"]["max_pressure_mpa"] = {
            "value": row["map_mpa"],
            "unit": "MPa",
            "source": source_id,
            "grade": "standard",
        }
        rec["values"]["pressure_standard"] = {
            "value": row["standard"],
            "source": source_id,
            "grade": "standard",
        }
        added_press += 1
    # Twist: a held standard states the reference twist for the
    # cartridge. It replaces a value that no source holds, and it is the
    # chambering standard, not a measurement of a specific barrel.
    added_twist = 0
    twist_file = SRC / "twist_found.json"
    if twist_file.exists():
        by_id = {r["cartridge_id"]: r for r in cartridges}
        for row in json.loads(twist_file.read_text(encoding="utf-8"))["twists"]:
            rec = by_id.get(row["cartridge_id"])
            if rec is None:
                continue
            existing = rec["values"].get("standard_twist_m")
            # A held standard upgrades a weaker claim, and fills a gap.
            if existing is not None and existing.get("grade") not in (
                "unverified",
                "documented",
                "claimed",
            ):
                continue
            source_id = row["source_id"]
            rec["values"]["standard_twist_m"] = {
                "value": row["twist_m"],
                "unit": "m per turn",
                "source": source_id,
                "grade": "standard",
            }
            if row.get("grooves") and "grooves" not in rec["values"]:
                rec["values"]["grooves"] = {
                    "value": row["grooves"],
                    "unit": "count",
                    "source": source_id,
                    "grade": "standard",
                }
            note = rec.get("note", "")
            rec["note"] = (note + " " if note else "") + (
                f"Reference twist from the held standard: {row['note']}"
            )
            added_twist += 1

    # Smoothbore: a shot cartridge has no rifling, so its twist is zero.
    # The CIP register is a tier 1 source, so the grade is standard. An
    # earlier run may have written the value at a weaker grade.
    for rec in cartridges:
        case_type = rec.get("classification", {}).get("case_type", "")
        if case_type not in ("shot", "dust shot"):
            continue
        existing = rec["values"].get("standard_twist_m")
        if existing is not None:
            if (
                existing.get("value") == 0
                and existing.get("source") == "cip_tdcc"
                and existing.get("grade") != "standard"
            ):
                existing["grade"] = "standard"
                added_twist += 1
            continue
        rec["values"]["standard_twist_m"] = {
            "value": 0,
            "unit": "m per turn",
            "source": "cip_tdcc",
            "grade": "standard",
        }
        added_twist += 1

    cartridges.sort(key=lambda r: r["cartridge_id"])
    CART.write_text(json.dumps(cartridges, indent=1) + "\n", encoding="utf-8")

    print(
        f"found coefficients merged: {added_bc}, lengths merged: {added_len}, "
        f"pressures merged: {added_press}, twists merged: {added_twist}"
    )


if __name__ == "__main__":
    main()
