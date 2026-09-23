#!/usr/bin/env python3
"""Merge the found weapon data into the weapon catalogue.

The weapon layer holds ONE datum per weapon: the rifling twist. Barrel
length is measured from the model and the cartridge comes from the
ammunition, so neither is stored here.

The source type decides the grade:

  a standard we hold (NATO EPVAT, SAAMI, CIP)  tier 1, grade standard
  a military or operator manual                tier 2, grade documented
  an established reference work                tier 3, grade documented
  a manufacturer datasheet or page             tier 4, grade claimed

A source counts as held when the research recorded its SHA-256, which
means the document was fetched. A source without a hash is cited but not
held, and it is never graded standard.

Only a source that a value references is registered, so the registry
holds no dead entries.

Research arrives as batches under sources/weapon_batches/. Two records
for one weapon_id keep the first file in name order, and a differing
twist is written to conflicts.json rather than dropped in silence.

Run:  python3 tools/validation/gen_weapons.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import chambering  # noqa: E402  - shared canonical form

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
BATCH_DIR = SRC / "weapon_batches"
FOUND = SRC / "weapons_found.json"
DB = DATA / "weapons.json"
SOURCES = DATA / "sources.json"
CONFLICTS = DATA / "conflicts.json"

MANUAL_WORDS = (
    "tm ",
    "tm-",
    "fm ",
    "manual",
    "operator",
    "instruction",
    "technical data",
    "technical manual",
    "army",
    "marine",
    "cadet",
    " mod ",
)
STANDARD_WORDS = ("nato", "epvat", "stanag", "saami", "cip", "aep")
REFERENCE_HOSTS = (
    "weaponsystems.net",
    "gunspec.io",
    "sadefensejournal",
    "smallarmsreview",
    "laipublications",
    "militaryfactory",
    "dockeryarmory",
    "riflesnguns",
    "genitron",
    "americanrifleman",
    "americanhandgunner",
    "modernfirearms",
    "gunmanual",
    "archive.org",
    "gunnerynetwork",
)
GENERIC = (
    "carbine",
    "rifle",
    "sniper",
    "weaponsystem",
    "system",
    "machinegun",
    "submachinegun",
    "pistol",
    "smg",
    "mg",
    "weapon",
)


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def aliases(weapon_id, name):
    out = {normalise(weapon_id), normalise(name)}
    stripped = normalise(name)
    for word in GENERIC:
        stripped = stripped.replace(word, "")
    if len(stripped) >= 3:
        out.add(stripped)
    return sorted(a for a in out if len(a) >= 3)


def classify(source):
    """Return (tier, type, grade) from the document itself."""
    text = f"{source.get('title', '')} {source.get('url', '')}".lower()
    if any(word in text for word in MANUAL_WORDS):
        return 2, "manual", "documented"
    if any(word in text for word in STANDARD_WORDS) or any(
        host in text for host in REFERENCE_HOSTS
    ):
        # A standard alone cannot be an entry source unless held.
        if source.get("sha256"):
            return 1, "standard", "standard"
        return 3, "manual", "documented"
    return 4, "manufacturer", "claimed"


def twist_mm(row):
    """The twist in millimetres per turn, from either unit."""
    if row.get("twist_mm"):
        return float(row["twist_mm"])
    if row.get("twist_in"):
        return float(row["twist_in"]) * 25.4
    return 0.0


def load_found():
    """Read the original file and every batch, with duplicates recorded."""
    sources, weapons, seen, duplicates, fills, retrieved = {}, [], {}, [], [], ""
    paths = ([FOUND] if FOUND.exists() else []) + sorted(BATCH_DIR.glob("*.json"))
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        retrieved = retrieved or data.get("retrieved", "")
        for source in data.get("sources", []):
            sources.setdefault(source["source_id"], source)
        for weapon in data.get("weapons", []):
            weapon_id = weapon.get("weapon_id")
            if not weapon_id:
                continue
            if weapon_id in seen:
                first = seen[weapon_id]
                held, second = twist_mm(first), twist_mm(weapon)
                if held <= 0 and second > 0:
                    # The earlier record has no twist, so the later one
                    # fills the gap rather than being dropped.
                    first["twist_mm"] = weapon.get("twist_mm")
                    first["twist_in"] = weapon.get("twist_in")
                    first["source_id"] = weapon.get("source_id")
                    first["grooves"] = weapon.get("grooves") or first.get("grooves")
                    first["source_note"] = (
                        str(first.get("source_note", ""))
                        + " "
                        + str(weapon.get("source_note", ""))
                    ).strip()
                    fills.append((weapon_id, path.name))
                elif held > 0 and second > 0 and abs(held - second) > 0.02 * held:
                    duplicates.append((first, weapon, path.name))
                continue
            seen[weapon_id] = weapon
            weapons.append(weapon)
    return retrieved, list(sources.values()), weapons, duplicates, fills


def main():
    retrieved, found_sources, found_weapons, duplicates, fills = load_found()
    cartridges = json.loads((DATA / "cartridges.json").read_text(encoding="utf-8"))
    # The chambering join runs on the canonical form, which is one source
    # for every generator. An exact name match missed most maker strings,
    # because the maker writes "5.56x45mm NATO" and the register writes
    # "5.56x45". A collision is left unresolved and reported by
    # gen_chambering_gaps.py, never guessed.
    chambering_index = chambering.build_index(cartridges)
    chambering_aliases = chambering.load_aliases()
    unresolved_chamberings = 0

    # Register only the sources a value actually references.
    referenced = {row["source_id"] for row in found_weapons if row.get("source_id")}
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    known = {s["source_id"] for s in sources}
    added_sources = 0
    for source in found_sources:
        if source["source_id"] not in referenced or source["source_id"] in known:
            continue
        tier, kind, _ = classify(source)
        sources.append(
            {
                "source_id": source["source_id"],
                "tier": tier,
                "type": kind,
                "title": source.get("title", source["source_id"]),
                "edition": "",
                "identifier": source["source_id"],
                "locator": "weapon twist",
                "published": "",
                "retrieved": retrieved or "2026-09-22",
                "url": source.get("url", ""),
                "licence": "public domain"
                if tier <= 3
                else "manufacturer published data",
                "primary_held": bool(source.get("sha256")),
                "note": "Weapon twist source."
                + ("" if source.get("sha256") else " Cited but not held."),
            }
        )
        known.add(source["source_id"])
        added_sources += 1
    SOURCES.write_text(json.dumps(sources, indent=1) + "\n", encoding="utf-8")

    by_source = {s["source_id"]: s for s in sources}
    # Rebuild only the records this tool owns, so a record added by
    # another tool is preserved.
    owned = {row["weapon_id"] for row in found_weapons if row.get("weapon_id")}
    weapons = (
        [
            w
            for w in json.loads(DB.read_text(encoding="utf-8"))
            if w["weapon_id"] not in owned
        ]
        if DB.exists()
        else []
    )
    skipped = 0
    for row in found_weapons:
        # No source, no entry: a value without a citation cannot enter.
        if not row.get("source_id"):
            skipped += 1
            continue
        source_id = row["source_id"]
        kind = by_source.get(source_id, {}).get("type")
        grade = {
            "standard": "standard",
            "manual": "documented",
            "manufacturer": "claimed",
        }.get(kind, "claimed")
        values = {
            "cartridge": {
                "value": row.get("cartridge", ""),
                "unit": "name",
                "source": source_id,
                "grade": grade,
            },
        }
        millimetres = twist_mm(row)
        if millimetres > 0:
            values["twist_m"] = {
                "value": round(millimetres / 1000, 5),
                "unit": "m per turn",
                "source": source_id,
                "grade": grade,
            }
        if row.get("grooves"):
            values["grooves"] = {
                "value": row["grooves"],
                "unit": "count",
                "source": source_id,
                "grade": grade,
            }
        cartridge_id, candidates = chambering.resolve(
            row.get("cartridge", ""), chambering_index, chambering_aliases
        )
        if not cartridge_id:
            unresolved_chamberings += 1
        weapons.append(
            {
                "weapon_id": row["weapon_id"],
                "names": [row["name"]] if row.get("name") else [row["weapon_id"]],
                "aliases": aliases(row["weapon_id"], row.get("name", "")),
                "manufacturer": row.get("manufacturer", ""),
                "cartridge_id": cartridge_id,
                "note": row.get("source_note", ""),
                "values": values,
            }
        )

    # A disagreement between two batches is recorded, never averaged.
    conflicts = (
        json.loads(CONFLICTS.read_text(encoding="utf-8")) if CONFLICTS.exists() else []
    )
    conflicts = [
        c for c in conflicts if not str(c.get("source_b", "")).startswith("batch_")
    ]
    for first, second, filename in duplicates:
        conflicts.append(
            {
                "entity": first["weapon_id"],
                "field": "twist_m",
                "value_a": round(twist_mm(first) / 1000, 5),
                "source_a": first.get("source_id", ""),
                "value_b": round(twist_mm(second) / 1000, 5),
                "source_b": f"batch_{filename}",
                "resolution": "Kept the record from the earlier file.",
                "rule_applied": "A disagreement is recorded, never averaged.",
                "date": "2026-09-22",
            }
        )
    CONFLICTS.write_text(json.dumps(conflicts, indent=1) + "\n", encoding="utf-8")

    weapons.sort(key=lambda r: r["weapon_id"])
    DB.write_text(json.dumps(weapons, indent=1) + "\n", encoding="utf-8")
    with_twist = sum(1 for w in weapons if "twist_m" in w["values"])
    print(
        f"weapons: {len(weapons)} ({with_twist} with a twist), "
        f"sources added: {added_sources}, rows skipped for no source: {skipped}, "
        f"disagreements: {len(duplicates)}, "
        f"chamberings unresolved: {unresolved_chamberings}"
    )


if __name__ == "__main__":
    main()
