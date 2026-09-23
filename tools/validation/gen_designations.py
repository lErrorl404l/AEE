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
import chambering  # noqa: E402  - shared canonical form

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

    # The chambering join runs on the canonical form, shared with
    # gen_weapons. An exact name match left most maker strings unresolved.
    chambering_index = chambering.build_index(cartridges)
    chambering_aliases = chambering.load_aliases()

    aliased = created = standard_only = ambiguous = disagreed = 0
    # Two batches may name the same model. The first file in name order
    # owns it, so a duplicate cannot create a second record. The key is
    # the resolved record and not the designation text: two different
    # weapons can share a designation, as the Beretta M9 and the Steyr M9
    # both being "M9", and deduping on the text would drop the row that
    # carries the twist.
    seen = set()
    for path in FILES:
        if not path.exists():
            continue
        for row in json.loads(path.read_text(encoding="utf-8"))["designations"]:
            designation = row.get("designation", "")
            key = normalise(designation)
            # A short designation is real: M4, M9, C7 and PK are all
            # service designations. The guard is one character, which
            # rejects only a placeholder, and the target lookup below
            # rejects a name that resolves to nothing.
            if len(key) < 2:
                continue
            # The explicit weapon_key is the strongest identity: it names
            # the record the row is about. The designation text is weaker,
            # because two weapons can share one, as the Beretta M9 and the
            # Steyr M9 are both "M9".
            target = (
                by_key.get(normalise(row.get("weapon_key", "")))
                or by_key.get(key)
                or by_key.get(normalise(row.get("weapon", "")))
            )
            seen_key = target["weapon_id"] if target is not None else key
            if seen_key in seen:
                continue
            seen.add(seen_key)
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
                # The catalogue may hold the record with no chambering
                # joined. The designation row names it, so fill it here.
                # This is a repair of the target's own record, not an
                # alias claim, so it runs before the ownership guard: two
                # weapons can share a designation, as the Beretta M9 and
                # the Steyr M9 both being "M9", and the guard would drop
                # the row that carries the twist.
                if not target.get("cartridge_id"):
                    target["cartridge_id"], _ = chambering.resolve(
                        row.get("chambering", ""), chambering_index, chambering_aliases
                    )
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
            cartridge_id, _candidates = chambering.resolve(
                row.get("chambering", ""), chambering_index, chambering_aliases
            )
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

    # A designation row can name a record that a later row creates, so the
    # alias attach in the main loop can miss it. Every record exists now,
    # so attach the remaining aliases and converge in one run.
    for path in FILES:
        if not path.exists():
            continue
        for row in json.loads(path.read_text(encoding="utf-8"))["designations"]:
            key = normalise(row.get("designation", ""))
            if len(key) < 2:
                continue
            target = by_key.get(normalise(row.get("weapon_key", ""))) or by_key.get(key)
            if target is None:
                continue
            if owner.get(key, target["weapon_id"]) != target["weapon_id"]:
                continue
            if key not in target.get("aliases", []) and key != target["weapon_id"]:
                target.setdefault("aliases", [])
                target["aliases"] = sorted(set(target["aliases"]) | {key})
                owner[key] = target["weapon_id"]
                aliased += 1

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
        new_id = wid[len(maker) :]
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
