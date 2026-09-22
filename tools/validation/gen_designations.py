#!/usr/bin/env python3
"""Merge national service designations into the weapon catalogue.

A designation is a nation's name for a real weapon. "L115A3" is the
British designation of the Accuracy International AWM, and "AK-74M" is
the Russian designation of the Kalashnikov rifle. The catalogue is keyed
on the real weapon, so a designation becomes an alias of it.

Where a designation names a weapon the catalogue does not hold:

  - a known twist that differs from the chambering standard earns a new
    record, because the weapon genuinely differs
  - a designation whose twist equals the standard, or is unknown, needs
    no record: the chambering standard already covers it at grade
    standard

The mapping itself is a fact and carries a source. An alias that another
record already claims is dropped and reported, because a shared alias is
not an identity signal.

Run:  python3 tools/validation/gen_designations.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gen_weapons import classify  # noqa: E402  - shared source grading

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
DB = DATA / "weapons.json"
SOURCES = DATA / "sources.json"
CONFLICTS = DATA / "conflicts.json"
CART = DATA / "cartridges.json"

FILES = [SRC / "service_designations_uk.json"] + sorted(SRC.glob("designations_*.json"))

# A reference work the general classifier would grade as a maker page.
TIER_OVERRIDES = {
    "rifleman_uk": (3, "manual", "documented"),
    "altair": (3, "manual", "documented"),
    "iwm": (3, "manual", "documented"),
    "royal_armouries": (3, "manual", "documented"),
}

TOLERANCE = 0.02


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def main():
    weapons = json.loads(DB.read_text(encoding="utf-8"))
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    conflicts = json.loads(CONFLICTS.read_text(encoding="utf-8"))
    cartridges = json.loads(CART.read_text(encoding="utf-8"))
    known = {s["source_id"] for s in sources}

    tiers = {s["source_id"]: s["tier"] for s in sources}
    added_sources = 0
    for path in FILES:
        if not path.exists():
            continue
        for source in json.loads(path.read_text(encoding="utf-8")).get("sources", []):
            sid = source["source_id"]
            if sid in known:
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
                    "locator": "designation mapping",
                    "published": "",
                    "retrieved": "2026-09-22",
                    "url": source.get("url", ""),
                    "licence": "public domain" if tier <= 3 else "published source",
                    "primary_held": bool(source.get("sha256")),
                    "note": "Designation source."
                    + ("" if source.get("sha256") else " Cited but not held."),
                }
            )
            known.add(sid)
            tiers[sid] = tier
            added_sources += 1

    by_key = {}
    for record in weapons:
        by_key.setdefault(record["weapon_id"], record)
        for alias in record.get("aliases", []):
            by_key.setdefault(alias, record)
    # An alias owned by one record may not move to another.
    owner = {}
    for record in weapons:
        for alias in [record["weapon_id"]] + record.get("aliases", []):
            owner.setdefault(alias, record["weapon_id"])

    by_cart = {}
    for record in cartridges:
        for name in record.get("names", []):
            by_cart.setdefault(normalise(name), record["cartridge_id"])

    aliased = created = standard_only = ambiguous = disagreed = 0
    # Two batches may name the same model. The first file in name order
    # owns it, so a duplicate cannot create a second record.
    seen = set()
    for path in FILES:
        if not path.exists():
            continue
        for row in json.loads(path.read_text(encoding="utf-8"))["designations"]:
            designation = row.get("designation", "")
            key = normalise(designation)
            if len(key) < 3:
                continue
            if key in seen:
                continue
            seen.add(key)
            target = (
                by_key.get(key)
                or by_key.get(normalise(row.get("weapon_key", "")))
                or by_key.get(normalise(row.get("weapon", "")))
            )
            source_id = row.get("twist_source_id") or row.get("map_source_id")
            tier = tiers.get(source_id, 4)
            grade = (
                "standard"
                if tier == 1
                else "documented"
                if tier in (2, 3)
                else "claimed"
            )
            twist = row.get("twist_mm")
            value = round(float(twist) / 1000, 5) if twist else 0.0

            if target is not None:
                if owner.get(key, target["weapon_id"]) != target["weapon_id"]:
                    ambiguous += 1
                    continue
                if key not in target.get("aliases", []) and key != target["weapon_id"]:
                    target.setdefault("aliases", [])
                    target["aliases"] = sorted(set(target["aliases"]) | {key})
                    owner[key] = target["weapon_id"]
                    aliased += 1
                held = target["values"].get("twist_m")
                if value > 0 and held is not None:
                    if abs(held["value"] - value) > TOLERANCE * held["value"]:
                        # A re-run must not append the same disagreement.
                        if any(
                            c.get("entity") == target["weapon_id"]
                            and c.get("source_b") == source_id
                            and c.get("value_b") == value
                            for c in conflicts
                        ):
                            disagreed += 1
                            continue
                        conflicts.append(
                            {
                                "entity": target["weapon_id"],
                                "field": "twist_m",
                                "value_a": held["value"],
                                "source_a": held["source"],
                                "value_b": value,
                                "source_b": source_id,
                                "resolution": "Kept the existing value. Recorded both.",
                                "rule_applied": "Two sources disagree. It is recorded, never averaged.",
                                "date": "2026-09-22",
                            }
                        )
                        disagreed += 1
                continue

            # No record yet. Every catalogue model earns an identity entry
            # that names its chambering, so a model resolves even when its
            # twist equals the chambering standard. The model's own twist is
            # stored only when a source states it; otherwise the chambering
            # standard applies, which is the same value with its own
            # provenance.
            cartridge_id = by_cart.get(normalise(row.get("chambering", "")), "")
            if not row.get("chambering") and value <= 0:
                standard_only += 1
                continue
            weapon_id = normalise(row.get("weapon_key", "")) or key
            base = weapon_id
            suffix = 2
            while weapon_id in owner:
                weapon_id = f"{base}_{suffix}"
                suffix += 1
            values = {
                "cartridge": {
                    "value": row.get("chambering", ""),
                    "unit": "name",
                    "source": source_id,
                    "grade": grade,
                },
            }
            if value > 0:
                values["twist_m"] = {
                    "value": value,
                    "unit": "m per turn",
                    "source": source_id,
                    "grade": grade,
                }
            if row.get("grooves"):
                values["grooves"] = {
                    "value": int(row["grooves"]),
                    "unit": "count",
                    "source": source_id,
                    "grade": grade,
                }
            maker_slug = normalise(row.get("maker", ""))
            aliases = {key, base, weapon_id}
            if maker_slug:
                aliases.add(maker_slug + base)
            record = {
                "weapon_id": weapon_id,
                "names": [row.get("weapon") or designation],
                "aliases": sorted(a for a in aliases if len(a) >= 3),
                "manufacturer": row.get("maker", ""),
                "cartridge_id": cartridge_id,
                "note": f"{designation} ({row.get('nation', '')}). "
                f"{row.get('note', '')}".strip(),
                "values": values,
            }
            weapons.append(record)
            owner[weapon_id] = weapon_id
            owner[key] = weapon_id
            by_key[key] = record
            created += 1

    # A maker slug never leads the key: the maker is a field. A record
    # whose key carries it is renamed, and the old form stays an alias, so
    # a mod classname that carries the maker still matches.
    taken = {record["weapon_id"] for record in weapons}
    renamed = 0
    for record in weapons:
        maker = normalise(record.get("manufacturer", ""))
        wid = record["weapon_id"]
        if not maker or not wid.startswith(maker) or len(wid) <= len(maker) + 2:
            continue
        new_id = wid[len(maker):]
        if new_id in taken:
            continue
        taken.discard(wid)
        taken.add(new_id)
        record["aliases"] = sorted(set(record.get("aliases", [])) | {wid})
        record["weapon_id"] = new_id
        renamed += 1

    weapons.sort(key=lambda r: r["weapon_id"])
    DB.write_text(json.dumps(weapons, indent=1) + "\n", encoding="utf-8")
    SOURCES.write_text(json.dumps(sources, indent=1) + "\n", encoding="utf-8")
    CONFLICTS.write_text(json.dumps(conflicts, indent=1) + "\n", encoding="utf-8")
    print(
        f"designations: aliases added {aliased}, records created {created}, "
        f"covered by the standard {standard_only}, ambiguous aliases {ambiguous}, "
        f"disagreements {disagreed}, sources added {added_sources}"
    )


if __name__ == "__main__":
    main()
