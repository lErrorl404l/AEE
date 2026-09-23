#!/usr/bin/env python3
"""Merge the held SAAMI and C.I.P. reference twists into the cartridge DB.

A reference twist is the rate the standards body registers for the
cartridge, and it is the chambering standard that every weapon inherits
until the weapon's own barrel is identified.

Three jobs:

  1. Register the sources of the SAAMI and the extra chambering twists.
  2. Create the cartridge records that no register we parsed holds yet:
     20 gauge, .410 bore, .32 ACP, 7.7x58mm Arisaka, .50 Beowulf,
     40x46mm SR and 40x53mm.
  3. Merge every reference twist. An existing value is kept and a
     disagreement is recorded, never averaged.

Run:  python3 tools/validation/gen_cartridge_standards.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gen_weapons import classify  # noqa: E402  - shared source grading

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
CART = DATA / "cartridges.json"
SOURCES = DATA / "sources.json"
CONFLICTS = DATA / "conflicts.json"

# The scope of each standards body's reference twist. SAAMI registers a
# pistol and a rifle test barrel separately, and the two can differ.
SCOPE_FIELD = {
    "saami_z299_3": "standard_twist_pistol_m",
    "saami_z299_4": "standard_twist_rifle_m",
}

# A source the general classifier would grade too weakly, or too strongly.
TIER_OVERRIDES = {
    "coe_1945_part2": (3, "manual", "documented"),
    # A Chinese technical publication, not a maker page.
    "firearmsworld_qbz951": (3, "manual", "documented"),
}

# The twist rows name a chambering; this maps it to our record.
CHAMBERING_TO_ID = {
    "7.63x25mm Mauser": "7_63_mauser",
    "7.65x17mm Browning (.32 ACP)": "32_acp",
    "40x46mm SR (M203)": "40x46_sr",
    "40x53mm (Mk 19)": "40x53",
    "7.7x58mm Arisaka (Type 99)": "77x58_arisaka",
    ".50 Beowulf (12.7x42mm)": "50_beowulf",
    "20 gauge": "20_gauge",
    ".410 bore": "410_bore",
}

# A SAAMI alias that does not match our own spelling.
ALIAS_TO_ID = {
    "45automatic": "45_acp",
    "45auto": "45_acp",
    "9mmluger": "9_x_19",
    "9x19": "9_x_19",
    "380automatic": "380_automatic",
    "380auto": "380_automatic",
    "40smithwesson": "40_smith_wesson",
    "40sw": "40_smith_wesson",
    "32automatic": "32_acp",
    "32auto": "32_acp",
    "22longrifle": "22_long_rifle",
    "222": "222_remington",
    "38special": "38_special",
    "357magnum": "357_magnum",
    "44magnum": "44_magnum",
    "50actionexpress": "50_ae",
    "50ae": "50_ae",
    "454casull": "454_casull",
    "429de": "429_desert_eagle",
    "7mmprc": "7mm_prc",
}

# The cartridges no register we parsed holds. Each value cites a held
# source. barrel_mm and bullet data are not invented here.
NEW_CARTRIDGES = [
    {
        "cartridge_id": "20_gauge",
        "names": ["20 Gauge", "20/70"],
        "case_family": "20 gauge",
        "classification": {
            "cip_tab": "Tab VII shot",
            "case_type": "shot",
            "cartridge_type": "shotgun",
            "origin_country": "FR EN DE",
            "year_created": "",
            "classification_source": "cip_tdcc",
        },
        "note": "Shot cartridge. Smoothbore, so the reference twist is zero.",
        "values": {
            "case_length_mm": {
                "value": 70.0,
                "unit": "mm",
                "source": "cip_tdcc",
                "grade": "standard",
            },
            "standard_twist_m": {
                "value": 0,
                "unit": "m per turn",
                "source": "cip_tdcc",
                "grade": "standard",
            },
        },
    },
    {
        "cartridge_id": "410_bore",
        "names": [".410 Bore", "410/70"],
        "case_family": "410",
        "classification": {
            "cip_tab": "Tab VII shot",
            "case_type": "shot",
            "cartridge_type": "shotgun",
            "origin_country": "FR EN DE",
            "year_created": "",
            "classification_source": "cip_tdcc",
        },
        "note": "Shot cartridge. Smoothbore in the C.I.P. register, so the reference twist is zero.",
        "values": {
            "case_length_mm": {
                "value": 70.0,
                "unit": "mm",
                "source": "cip_tdcc",
                "grade": "standard",
            },
            "standard_twist_m": {
                "value": 0,
                "unit": "m per turn",
                "source": "cip_tdcc",
                "grade": "standard",
            },
        },
    },
    {
        "cartridge_id": "32_acp",
        "names": ["7.65x17mm Browning", ".32 ACP"],
        "case_family": "",
        "classification": {
            "cip_tab": "Tab IV pistol/revolver",
            "case_type": "pistol",
            "cartridge_type": "pistol",
            "origin_country": "BE US",
            "year_created": "1899",
            "classification_source": "cip_tdcc",
        },
        "note": "Added from the C.I.P. register. Used by the vz.61 Skorpion.",
        "values": {
            "standard_twist_m": {
                "value": 0.25,
                "unit": "m per turn",
                "source": "cip_tdcc",
                "grade": "standard",
            },
            "grooves": {
                "value": 6,
                "unit": "count",
                "source": "cip_tdcc",
                "grade": "standard",
            },
        },
    },
    {
        "cartridge_id": "77x58_arisaka",
        "names": ["7.7x58mm Arisaka", "7.7 mm Type 99"],
        "case_family": "",
        "classification": {
            "cip_tab": "",
            "case_type": "rifle",
            "cartridge_type": "rifle",
            "origin_country": "Japan",
            "year_created": "1939",
            "classification_source": "coe_1945_part2",
        },
        "note": "Japanese service cartridge. Not in the C.I.P. or SAAMI registers.",
        "values": {
            "standard_twist_m": {
                "value": 0.254,
                "unit": "m per turn",
                "source": "coe_1945_part2",
                "grade": "documented",
            },
            "grooves": {
                "value": 4,
                "unit": "count",
                "source": "coe_1945_part2",
                "grade": "documented",
            },
        },
    },
    {
        "cartridge_id": "50_beowulf",
        "names": [".50 Beowulf", "12.7x42mm"],
        "case_family": "",
        "classification": {
            "cip_tab": "",
            "case_type": "rimless",
            "cartridge_type": "rifle",
            "origin_country": "United states",
            "year_created": "2001",
            "classification_source": "alexander_arms_beowulf",
        },
        "note": "Alexander Arms cartridge. Not in the C.I.P. or SAAMI registers.",
        "values": {
            "standard_twist_m": {
                "value": 0.508,
                "unit": "m per turn",
                "source": "alexander_arms_beowulf",
                "grade": "claimed",
            },
        },
    },
    {
        "cartridge_id": "40x46_sr",
        "names": ["40x46mm SR", "40 mm M203"],
        "case_family": "",
        "classification": {
            "cip_tab": "",
            "case_type": "grenade",
            "cartridge_type": "grenade",
            "origin_country": "United states",
            "year_created": "1960",
            "classification_source": "lmt_m203",
        },
        "note": "Low pressure grenade cartridge. The launcher barrel is rifled.",
        "values": {
            "standard_twist_m": {
                "value": 1.2192,
                "unit": "m per turn",
                "source": "lmt_m203",
                "grade": "claimed",
            },
        },
    },
    {
        "cartridge_id": "58x42",
        "names": ["5.8x42mm", "DBP87"],
        "case_family": "",
        "classification": {
            "cip_tab": "",
            "case_type": "rifle",
            "cartridge_type": "rifle",
            "origin_country": "China",
            "year_created": "1987",
            "classification_source": "firearmsworld_qbz951",
        },
        "note": (
            "Chinese service cartridge. The QBZ-95-1 changed the twist from "
            "240 mm to 210 mm, so the original rate is the chambering "
            "standard and the later rate is a weapon-level value."
        ),
        "values": {
            "standard_twist_m": {
                "value": 0.24,
                "unit": "m per turn",
                "source": "firearmsworld_qbz951",
                "grade": "documented",
            },
            "grooves": {
                "value": 4,
                "unit": "count",
                "source": "firearmsworld_qbz951",
                "grade": "documented",
            },
        },
    },
    {
        "cartridge_id": "7mm_prc",
        "names": ["7mm PRC", "7 mm Precision Rifle Cartridge"],
        "case_family": "",
        "classification": {
            "cip_tab": "",
            "case_type": "beltless magnum",
            "cartridge_type": "rifle",
            "origin_country": "United states",
            "year_created": "2022",
            "classification_source": "saami_z299_4",
        },
        "note": "SAAMI registered 2022. Not in the C.I.P. register.",
        "values": {
            "standard_twist_m": {
                "value": 0.2032,
                "unit": "m per turn",
                "source": "saami_z299_4",
                "grade": "standard",
            },
            "grooves": {
                "value": 6,
                "unit": "count",
                "source": "saami_z299_4",
                "grade": "standard",
            },
        },
    },
    {
        "cartridge_id": "40x53",
        "names": ["40x53mm", "40 mm Mk 19"],
        "case_family": "",
        "classification": {
            "cip_tab": "",
            "case_type": "grenade",
            "cartridge_type": "grenade",
            "origin_country": "United states",
            "year_created": "1966",
            "classification_source": "us_army_tm9_1010_230_10",
        },
        "note": "High pressure grenade cartridge. The launcher barrel is rifled.",
        "values": {
            "standard_twist_m": {
                "value": 1.2192,
                "unit": "m per turn",
                "source": "us_army_tm9_1010_230_10",
                "grade": "documented",
            },
        },
    },
]


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def saami_aliases(name):
    """A SAAMI row names several aliases; return each one."""
    out = []
    for part in re.split(r"[/\[\]()]", name or ""):
        part = part.strip()
        if not part or part.lower().startswith("notice"):
            continue
        out.append(part)
        base = re.sub(r"\+\s*p$", "", part, flags=re.I).strip()
        if base and base != part:
            out.append(base)
    return out


def register_sources(files, sources, known):
    added = 0
    for path in files:
        if not path.exists():
            continue
        for source in json.loads(path.read_text(encoding="utf-8")).get("sources", []):
            sid = source["source_id"]
            if sid in known:
                # An override is authoritative even for a source that an
                # earlier run registered at another tier.
                if sid in TIER_OVERRIDES:
                    tier, kind, _ = TIER_OVERRIDES[sid]
                    for existing in sources:
                        if existing["source_id"] == sid:
                            existing["tier"] = tier
                            existing["type"] = kind
                continue
            if sid in TIER_OVERRIDES:
                tier, kind, _ = TIER_OVERRIDES[sid]
            else:
                tier, kind, _ = classify(source)
            sources.append(
                {
                    "source_id": sid,
                    "tier": tier,
                    "type": kind,
                    "title": source.get("title", sid),
                    "edition": "",
                    "identifier": sid,
                    "locator": "reference twist",
                    "published": "",
                    "retrieved": "2026-09-22",
                    "url": source.get("url", ""),
                    "licence": "public domain"
                    if tier <= 3
                    else "standards body published data",
                    "primary_held": bool(source.get("sha256")),
                    "note": "Chambering standard."
                    + ("" if source.get("sha256") else " Cited but not held."),
                }
            )
            known.add(sid)
            added += 1
    return added


def main():
    cartridges = json.loads(CART.read_text(encoding="utf-8"))
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    known = {s["source_id"] for s in sources}
    conflicts = json.loads(CONFLICTS.read_text(encoding="utf-8"))

    added_sources = register_sources(
        [
            SRC / "saami_twists.json",
            SRC / "chambering_twists_extra.json",
            SRC / "chambering_twists_foreign.json",
            SRC / "chambering_twists_new.json",
        ],
        sources,
        known,
    )

    by_id = {c["cartridge_id"]: c for c in cartridges}
    added_records = 0
    for record in NEW_CARTRIDGES:
        if record["cartridge_id"] in by_id:
            continue
        cartridges.append(record)
        by_id[record["cartridge_id"]] = record
        added_records += 1

    by_name = {}
    for record in cartridges:
        for name in record.get("names", []):
            by_name.setdefault(normalise(name), record)

    grades = {
        s["source_id"]: (
            "standard"
            if s["tier"] == 1
            else "documented"
            if s["tier"] in (2, 3)
            else "claimed"
        )
        for s in sources
    }

    merged = disagreed = unmatched = 0
    for path, key in (
        (SRC / "saami_twists.json", "cartridge"),
        (SRC / "chambering_twists_extra.json", "chambering"),
        (SRC / "chambering_twists_new.json", "chambering"),
    ):
        if not path.exists():
            continue
        for row in json.loads(path.read_text(encoding="utf-8"))["twists"]:
            if key == "chambering":
                # A chambering capture may file the name under any of the
                # labels the sets use.
                names = [
                    row.get("chambering")
                    or row.get("cartridge")
                    or row.get("chambering_id")
                    or ""
                ]
            else:
                names = saami_aliases(row.get("cartridge", ""))
            if not any(names):
                unmatched += 1
                continue
            record = None
            if key == "chambering":
                record = by_id.get(CHAMBERING_TO_ID.get(names[0], ""))
            if record is None:
                for alias in names:
                    hit = by_name.get(normalise(alias)) or by_id.get(
                        ALIAS_TO_ID.get(normalise(alias), "")
                    )
                    if hit:
                        record = hit
                        break
            if record is None:
                unmatched += 1
                continue
            source_id = row["source_id"]
            grade = grades.get(source_id, "claimed")
            millimetres = row.get("twist_mm")
            if millimetres is None and row.get("twist_in"):
                millimetres = round(float(row["twist_in"]) * 25.4, 2)
            if millimetres is None:
                unmatched += 1
                continue
            if row.get("smoothbore"):
                millimetres = 0
            value = round(float(millimetres) / 1000, 5)
            # A pistol and a rifle standard can both register a cartridge,
            # so each value is kept in its own scope. The generic value is
            # derived after the loop from the arm type the cartridge
            # normally belongs to.
            scope = SCOPE_FIELD.get(source_id, "standard_twist_m")
            existing = record["values"].get(scope)
            if existing is not None:
                if abs(existing["value"] - value) <= 0.02 * max(
                    existing["value"], 1e-6
                ):
                    continue
                conflicts.append(
                    {
                        "entity": record["cartridge_id"],
                        "field": scope,
                        "value_a": existing["value"],
                        "source_a": existing["source"],
                        "value_b": value,
                        "source_b": source_id,
                        "resolution": "Kept the first value. Recorded both.",
                        "rule_applied": "Two held standards disagree. It is recorded, never averaged.",
                        "date": "2026-09-22",
                    }
                )
                disagreed += 1
                continue
            record["values"][scope] = {
                "value": value,
                "unit": "m per turn",
                "source": source_id,
                "grade": grade,
            }
            merged += 1
            if row.get("grooves") and "grooves" not in record["values"]:
                record["values"]["grooves"] = {
                    "value": int(row["grooves"]),
                    "unit": "count",
                    "source": source_id,
                    "grade": grade,
                }

    # The generic standard follows the arm type the cartridge belongs to:
    # a revolver cartridge takes the pistol standard, a rifle cartridge
    # the rifle standard.
    derived = 0
    for record in cartridges:
        values = record["values"]
        if "standard_twist_m" in values:
            continue
        kind = record.get("classification", {}).get("cartridge_type", "")
        order = (
            ("standard_twist_pistol_m", "standard_twist_rifle_m")
            if kind in ("pistol", "revolver")
            else ("standard_twist_rifle_m", "standard_twist_pistol_m")
        )
        for field in order:
            if field in values:
                values["standard_twist_m"] = dict(values[field])
                derived += 1
                break

    # Two scopes are a model, not a disagreement.
    conflicts = [
        c
        for c in conflicts
        if not (
            c.get("field") == "standard_twist_m"
            and {c.get("source_a"), c.get("source_b")}
            <= {"saami_z299_3", "saami_z299_4"}
        )
    ]

    cartridges.sort(key=lambda r: r["cartridge_id"])
    CART.write_text(json.dumps(cartridges, indent=1) + "\n", encoding="utf-8")
    SOURCES.write_text(json.dumps(sources, indent=1) + "\n", encoding="utf-8")
    CONFLICTS.write_text(json.dumps(conflicts, indent=1) + "\n", encoding="utf-8")
    print(
        f"cartridge records added: {added_records}, sources added: {added_sources}, "
        f"twists merged: {merged}, disagreements: {disagreed}, unmatched rows: {unmatched}"
    )


if __name__ == "__main__":
    main()
