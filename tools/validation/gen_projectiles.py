#!/usr/bin/env python3
"""Build projectile records from the parsed bullet sources.

Hornady, Berger, Sierra, Nosler and Lapua values are manufacturer
claims. Applied Ballistics is an independent source, so a bullet weight
that both a manufacturer and Applied Ballistics list is raised to grade
corroborated.

A diameter taken from a calibre label is a derivation, so it carries the
mapping as its formula. A diameter published by the manufacturer is a
claim.

Run:  python3 tools/validation/gen_projectiles.py
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
DB = DATA / "projectiles.json"

GRAIN_TO_G = 0.06479891

# A ballistic coefficient is only meaningful against the drag model it
# was measured with. The field name states the model, and the entry states
# the basis: a maker catalogue value is a secondary claim and says so.
BC_MODEL = {"bc_g1": "G1", "bc_g7": "G7"}
MAKER_BASIS = "maker_published_secondary"
FAMILY = {
    "eld match": ("ELDM", "ELD-M"),
    "eld-x": ("ELDX", "ELD-X"),
    "a-tip": ("ATIP", "A-Tip"),
    "eld-vt": ("ELDVT", "ELD-VT"),
}
DIAMETER_NOTE = "standard bullet diameter for the calibre label"

# The four manufacturer catalogs that share one input schema.
CATALOGS = [
    ("berger_bullets", "Berger"),
    ("sierra_bullets", "Sierra"),
    ("nosler_bullets", "Nosler"),
    ("lapua_bullets", "Lapua"),
]


def source_editions():
    """Return the edition a source states, keyed by source id."""
    registry = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    return {
        s["source_id"]: s.get("edition") or s.get("published", "")
        for s in registry
    }


def bc_model(values):
    """Return the drag model the held coefficients actually use."""
    models = [BC_MODEL[f] for f in ZBC_ORDER if values.get(f)]
    return " and ".join(models)


ZBC_ORDER = ("bc_g1", "bc_g7")


def mark_coefficients(values, editions):
    """State the drag model, the basis and the edition on every coefficient."""
    for field, model in BC_MODEL.items():
        entry = values.get(field)
        if entry is None:
            continue
        entry["drag_model"] = model
        entry["basis"] = MAKER_BASIS
        entry["edition"] = editions.get(entry.get("source"), "")


def hornady_aliases(mass, family, twist_in):
    code, dash = FAMILY[family.lower()]
    names = [f"{mass}{code}", f"{mass} {dash}", f"{mass}gr {dash}"]
    if twist_in:
        names.append(f"{mass}{code} {twist_in:g}in")
    return names


def clean_name(name, twist_in):
    name = re.sub(r"(Match|X|Tip|VT)(\d)", r"\1 (\2", name)
    name = re.sub(r"\s+", " ", name).strip()
    if twist_in:
        name = re.sub(r"1 in [0-9.]+.*$", "", name).strip()
        name = name.rstrip("( ").strip()
        name = f'{name} (1 in {twist_in:g}" twist)'
    return name


def hornady_records():
    src = json.loads((SRC / "hornady_bc.json").read_text(encoding="utf-8"))
    editions = source_editions()
    out = []
    for b in src["bullets"]:
        if not b["diameter_mm"]:
            continue
        family = b["family"].lower()
        cal = re.sub(r"[^0-9a-z]", "", b["calibre_label"].lower())
        twist = f"_t{('%g' % b['twist_in']).replace('.', 'p')}" if b["twist_in"] else ""
        pid = f"hornady_{FAMILY[family][0].lower()}_{cal}_{int(b['mass_gr'])}{twist}"
        diameter_in = b["diameter_mm"] / 25.4
        values = {
            "mass_g": {
                "value": b["mass_g"],
                "unit": "g",
                "source": "hornady_bc",
                "grade": "claimed",
            },
            "diameter_mm": {
                "value": b["diameter_mm"],
                "unit": "mm",
                "formula": DIAMETER_NOTE,
                "source": "hornady_bc",
                "grade": "derived",
            },
        }
        for field in ZBC_ORDER:
            if b.get(field) is not None:
                values[field] = {
                    "value": b[field],
                    "source": "hornady_bc",
                    "grade": "claimed",
                }
        values["drag_model"] = {
            "value": bc_model(values),
            "source": "hornady_bc",
            "grade": "claimed",
        }
        values["sectional_density"] = {
            "value": round((b["mass_gr"] / 7000) / (diameter_in**2), 4),
            "formula": "SD = (mass_gr / 7000) / (diameter_in ^ 2)",
            "source": "hornady_bc",
            "grade": "derived",
        }
        mark_coefficients(values, editions)
        out.append(
            {
                "projectile_id": pid,
                "names": [clean_name(b["published_name"], b["twist_in"])]
                + hornady_aliases(int(b["mass_gr"]), b["family"], b["twist_in"]),
                "manufacturer": "Hornady",
                "note": ""
                if not b["twist_in"]
                else f"BC published for a 1 in {b['twist_in']:g} inch twist.",
                "values": values,
            }
        )
    return out


def catalog_records(source_id, maker):
    src = json.loads((SRC / f"{source_id}.json").read_text(encoding="utf-8"))
    editions = source_editions()
    out = []
    for b in src["bullets"]:
        if not b.get("diameter_in") or not b.get("mass_gr"):
            continue
        values = {
            "mass_g": {
                "value": round(b["mass_gr"] * GRAIN_TO_G, 4),
                "unit": "g",
                "source": source_id,
                "grade": "claimed",
            },
            "diameter_mm": {
                "value": round(b["diameter_in"] * 25.4, 4),
                "unit": "mm",
                "source": source_id,
                "grade": "claimed",
            },
        }
        for field, key in (
            ("bc_g1", "bc_g1"),
            ("bc_g7", "bc_g7"),
            ("sectional_density", "sectional_density"),
        ):
            if b.get(key) is not None:
                values[field] = {
                    "value": b[key],
                    "source": source_id,
                    "grade": "claimed",
                }
        if b.get("min_twist_in") is not None:
            values["min_twist_m"] = {
                "value": round(b["min_twist_in"] * 0.0254, 4),
                "unit": "m per turn",
                "source": source_id,
                "grade": "claimed",
            }
        if b.get("length_in") is not None:
            values["length_mm"] = {
                "value": round(b["length_in"] * 25.4, 4),
                "unit": "mm",
                "source": source_id,
                "grade": "claimed",
            }
        mark_coefficients(values, editions)
        if any(values.get(f) for f in ZBC_ORDER):
            values["drag_model"] = {
                "value": bc_model(values),
                "source": source_id,
                "grade": "claimed",
            }
        out.append(
            {
                "projectile_id": f"{maker.lower()}_{b['part']}",
                "names": [b["description"]],
                "manufacturer": maker,
                "note": f"{maker} catalog bullet specification.",
                "values": values,
            }
        )
    return out


def ab_index():
    src = json.loads((SRC / "ab_bullet_library.json").read_text(encoding="utf-8"))
    index = {}
    for b in src["bullets"]:
        key = (b["manufacturer"].lower(), round(b["diameter_in"], 3))
        index.setdefault(key, []).append(b["mass_gr"])
    return index


def corroborate(records, index):
    hits = 0
    for rec in records:
        values = rec["values"]
        mass = values.get("mass_g", {}).get("value")
        diameter = values.get("diameter_mm", {}).get("value")
        if mass is None or diameter is None:
            continue
        maker = rec.get("manufacturer", "").lower()
        candidates = index.get((maker, round(diameter / 25.4, 3)), [])
        mass_gr = mass / GRAIN_TO_G
        if any(abs(m - mass_gr) <= 0.005 * mass_gr for m in candidates):
            values["mass_g"]["grade"] = "corroborated"
            values["mass_g"]["corroborated_by"] = ["ab_bullet_library"]
            # Applied Ballistics is the primary source for what its
            # library states. Version 925 states identity, mass and
            # diameter; it states no coefficient, so the maker remains
            # the basis for the BC and the record says so.
            rec["applied_ballistics"] = {
                "library": "Applied Ballistics bullet library",
                "version": "925",
                "covers": "identity and mass",
                "bc_covered": False,
            }
            hits += 1
    return hits


def main():
    existing = json.loads(DB.read_text(encoding="utf-8")) if DB.exists() else []
    prefixes = ("hornady_", "berger_", "sierra_", "nosler_", "lapua_")
    existing = [r for r in existing if not r["projectile_id"].startswith(prefixes)]
    records = hornady_records()
    for source_id, maker in CATALOGS:
        records += catalog_records(source_id, maker)
    hits = corroborate(records, ab_index())
    merged = {r["projectile_id"]: r for r in existing}
    for rec in records:
        merged.setdefault(rec["projectile_id"], rec)
    out = sorted(merged.values(), key=lambda r: r["projectile_id"])
    DB.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"projectiles: {len(out)} (weights corroborated: {hits})")


if __name__ == "__main__":
    main()
