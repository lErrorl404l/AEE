#!/usr/bin/env python3
"""Export the verified ballistics database as CSV, sorted and searchable.

One row per cartridge, with its classification, its measured values and
the source grade behind each one. Use --find to locate a round by any
name or alias.

Examples:
  python3 tools/validation/export_ballistics_csv.py --sort calibre
  python3 tools/validation/export_ballistics_csv.py --find "300 norma"
  python3 tools/validation/export_ballistics_csv.py --out cartridges.csv
"""

import argparse
import csv
import json
import sys
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"

FIELDS = [
    "cartridge_id",
    "name",
    "aliases",
    "cartridge_type",
    "case_type",
    "cip_tab",
    "origin_country",
    "year_created",
    "calibre_mm",
    "bore_mm",
    "case_length_mm",
    "max_pressure_mpa",
    "pressure_standard",
    "twist_m",
    "grooves",
    "grades",
    "note",
]

PROJECTILE_FIELDS = [
    "projectile_id",
    "name",
    "aliases",
    "manufacturer",
    "mass_g",
    "diameter_mm",
    "bc_g1",
    "bc_g7",
    "drag_model",
    "sectional_density",
    "required_twist_m",
    "grades",
    "note",
]


def flatten(rec):
    values = rec.get("values", {})
    cls = rec.get("classification", {})

    def val(field):
        entry = values.get(field)
        return entry["value"] if entry else ""

    grades = sorted({e.get("grade", "") for e in values.values()})
    names = rec.get("names", [])
    return {
        "cartridge_id": rec.get("cartridge_id", ""),
        "name": names[0] if names else "",
        "aliases": " | ".join(names[1:]),
        "cartridge_type": cls.get("cartridge_type", ""),
        "case_type": cls.get("case_type", ""),
        "cip_tab": cls.get("cip_tab", ""),
        "origin_country": cls.get("origin_country", ""),
        "year_created": cls.get("year_created", ""),
        "calibre_mm": val("calibre_mm"),
        "bore_mm": val("bore_mm"),
        "case_length_mm": val("case_length_mm"),
        "max_pressure_mpa": val("max_pressure_mpa"),
        "pressure_standard": val("pressure_standard"),
        "twist_m": val("standard_twist_m"),
        "grooves": val("grooves"),
        "grades": ",".join(grades),
        "note": rec.get("note", ""),
    }


def flatten_projectile(rec):
    values = rec.get("values", {})

    def val(field):
        entry = values.get(field)
        return entry["value"] if entry else ""

    grades = sorted({e.get("grade", "") for e in values.values()})
    names = rec.get("names", [])
    return {
        "projectile_id": rec.get("projectile_id", ""),
        "name": names[0] if names else "",
        "aliases": " | ".join(names[1:]),
        "manufacturer": rec.get("manufacturer", ""),
        "mass_g": val("mass_g"),
        "diameter_mm": val("diameter_mm"),
        "bc_g1": val("bc_g1"),
        "bc_g7": val("bc_g7"),
        "drag_model": val("drag_model"),
        "sectional_density": val("sectional_density"),
        "required_twist_m": val("required_twist_m"),
        "grades": ",".join(grades),
        "note": rec.get("note", ""),
    }


def num(row, key):
    try:
        return float(row[key])
    except (TypeError, ValueError):
        return 1e9


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--kind", choices=["cartridges", "projectiles"], default="cartridges"
    )
    ap.add_argument("--sort", choices=["name", "calibre", "type"], default="calibre")
    ap.add_argument("--find", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    if args.kind == "projectiles":
        fields = PROJECTILE_FIELDS
        rows = [
            flatten_projectile(r)
            for r in json.loads((DATA / "projectiles.json").read_text(encoding="utf-8"))
        ]
        id_key = "projectile_id"
    else:
        fields = FIELDS
        rows = [
            flatten(r)
            for r in json.loads((DATA / "cartridges.json").read_text(encoding="utf-8"))
        ]
        id_key = "cartridge_id"

    if args.find:
        needle = args.find.lower()
        rows = [
            r
            for r in rows
            if needle in " ".join([r[id_key], r["name"], r["aliases"]]).lower()
        ]
        if not rows:
            print(f"no entry matches {args.find!r}", file=sys.stderr)
            return 1

    if args.sort == "name":
        rows.sort(key=lambda r: r["name"].lower())
    elif args.sort == "type":
        if args.kind == "projectiles":
            rows.sort(key=lambda r: (r["manufacturer"], r["name"].lower()))
        else:
            rows.sort(
                key=lambda r: (r["cartridge_type"], r["case_type"], r["name"].lower())
            )
    elif args.kind == "projectiles":
        rows.sort(
            key=lambda r: (num(r, "diameter_mm"), num(r, "mass_g"), r["name"].lower())
        )
    else:
        rows.sort(
            key=lambda r: (
                num(r, "calibre_mm"),
                num(r, "case_length_mm"),
                r["name"].lower(),
            )
        )

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {len(rows)} rows to {args.out}")
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
