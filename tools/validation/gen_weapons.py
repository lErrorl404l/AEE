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


# The shortest key that can carry a maker as well as a model.
IDENTITY_MIN = 6

# How good the evidence is, best last.
GRADE_RANK = {"claimed": 1, "documented": 2, "standard": 3}


def model_key(weapon):
    """The weapon's MODEL, with maker and editorial noise removed.

    The corpus keys an entry on its chambering, so one model legitimately
    holds several entries when it is sold in several calibres - a Sako 85
    in .243 and in .308 are different rifles. What it must NOT hold is two
    entries for ONE model in ONE chambering: the two then advertise the
    same designation, every query carrying it is ambiguous, and the
    matcher names neither.

    This reduces an entry to its model so that case can be seen:

      "Simonov SKS (designer designation)"  -> sks      parenthetical dropped
      "FN Herstal Minimi Para (LMG)"        -> minimipara   maker dropped
      "FN Minimi Para (LMG)"                -> minimipara
      "FN Minimi (LMG)"                     -> minimi    a real variant, kept apart

    The maker words come from the entry's OWN manufacturer field, so no
    list of makers is kept here.
    """
    name = weapon.get("name") or (weapon.get("names") or [""])[0]
    # A parenthesis after a SPACE is editorial - an alternative
    # designation, a service name, a calibre note - and the model is the
    # same without it. One GLUED to the word before it is part of the
    # model: "XD(M)" and "XD(S)" are two pistols, not one written twice.
    name = re.sub(r"\s+\([^)]*\)", " ", name)
    words = [
        normalise(word) for word in re.split(r"[^A-Za-z0-9]+", name) if normalise(word)
    ]
    key = "".join(w for w in words if w not in maker_words(weapon) and w not in GENERIC)
    return key if len(key) >= 3 else "".join(words)


def maker_words(weapon):
    """The words of the entry's own manufacturer field."""
    return {
        normalise(word)
        for word in re.split(r"[^A-Za-z0-9]+", weapon.get("manufacturer") or "")
        if len(word) > 1
    }


def consolidate(weapons):
    """Fuse entries that are the same model in the same chambering."""
    out, index, merged = [], {}, []
    for weapon in weapons:
        key = (model_key(weapon), weapon.get("cartridge_id") or "")
        first = index.get(key)
        # The model key drops the maker, so two makers can sell a model of
        # the same name in the same calibre - a Ruger Scout and a Steyr
        # Scout are different rifles. They are one weapon only if their
        # makers agree: one's maker words contain the other's, which is
        # how "FN" and "FN Herstal" name one firm.
        if first is not None and not any(c.isdigit() for c in key[0]):
            # Only a key of PLAIN WORDS needs this: a type number is a
            # maker-unique designation, so two firms do not both sell a
            # "PP-19", and a disagreement between the two entries' maker
            # fields there is a data error, not two weapons.
            mine, theirs = maker_words(weapon), maker_words(first)
            if mine and theirs and not (mine <= theirs or theirs <= mine):
                out.append(weapon)
                continue
        if first is None:
            index[key] = weapon
            out.append(weapon)
            continue
        # The richer record survives, so no sourced value is lost, and it
        # takes the other's keys so the dropped id still resolves.
        keep, drop = first, weapon
        if len(weapon.get("values") or {}) > len(first.get("values") or {}):
            keep, drop = weapon, first
            out[out.index(first)] = weapon
            index[key] = weapon
        for field in ("names", "aliases"):
            keep[field] = sorted(
                set(keep.get(field) or []) | set(drop.get(field) or [])
            )
        for field, value in (drop.get("values") or {}).items():
            (keep.setdefault("values", {})).setdefault(field, value)
        keep["cartridge_id"] = keep.get("cartridge_id") or drop.get("cartridge_id")
        keep["manufacturer"] = keep.get("manufacturer") or drop.get("manufacturer")
        note = str(drop.get("note", "")).strip()
        if note and note not in str(keep.get("note", "")):
            keep["note"] = (str(keep.get("note", "")) + " " + note).strip()
        merged.append((drop["weapon_id"], keep["weapon_id"]))
    return out, merged


def identity_keys(weapon):
    """The keys under which this record names its weapon.

    Two records name the SAME weapon when they share one of these, even
    with different weapon_ids: "Zastava M21" captured a second time as
    "zastavam21" is not a second rifle. Two entries for one weapon make
    every query that carries its designation ambiguous, so the matcher
    returns nothing for both - the duplicate costs more coverage than the
    missing entry it was meant to add.
    """
    # A MODEL CODE is not an identity on its own: "M21" is the Zastava
    # rifle and the US M21 SWS alike, so merging on it would fuse two real
    # weapons into one. Only a key long enough to carry the maker as well
    # as the model is admitted, plus the folded full name.
    out = {
        key
        for key in aliases(weapon.get("weapon_id", ""), weapon.get("name", ""))
        if len(key) >= IDENTITY_MIN
    }
    for name in [weapon.get("name", "")] + list(weapon.get("names") or []):
        key = normalise(name)
        if len(key) >= IDENTITY_MIN:
            out.add(key)
    return out


def merge_record(first, later, name):
    """Fill the held record's gaps from a later record of the same weapon."""
    filled = False
    if twist_mm(first) <= 0 and twist_mm(later) > 0:
        first["twist_mm"] = later.get("twist_mm")
        first["twist_in"] = later.get("twist_in")
        first["source_id"] = later.get("source_id")
        filled = True
    if not first.get("grooves") and later.get("grooves"):
        first["grooves"] = later["grooves"]
        filled = True
    if not first.get("mass_kg") and later.get("mass_kg"):
        first["mass_kg"] = later["mass_kg"]
        # The mass carries the source that STATES it, which is the later
        # record's, not the one the held record cites for its rifling.
        first["mass_source_id"] = later.get("mass_source_id") or later.get("source_id")
        first["source_id"] = first.get("source_id") or first["mass_source_id"]
        filled = True
    if later.get("aliases"):
        # A designation the later record states is a designation of the
        # same weapon, so it joins the held record's own.
        merged_aliases = list(first.get("aliases") or [])
        for alias in later["aliases"]:
            if alias not in merged_aliases:
                merged_aliases.append(alias)
                filled = True
        first["aliases"] = merged_aliases
    if not first.get("source_id") and later.get("source_id"):
        first["source_id"] = later["source_id"]
        first["cartridge"] = first.get("cartridge") or later.get("cartridge")
        filled = True
    if filled:
        first["source_note"] = (
            str(first.get("source_note", "")) + " " + str(later.get("source_note", ""))
        ).strip()
    return filled


def load_found():
    """Read the original file and every batch, with duplicates recorded."""
    sources, weapons, seen, duplicates, fills, retrieved = {}, [], {}, [], [], ""
    by_identity = {}
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
            keys = identity_keys(weapon)
            first = seen.get(weapon_id)
            if first is None:
                # Not the same id, but the same weapon: a recapture under
                # another id is merged into the held record, never added
                # beside it.
                for key in keys:
                    if key in by_identity:
                        first = by_identity[key]
                        break
            if first is not None:
                held, second = twist_mm(first), twist_mm(weapon)
                if merge_record(first, weapon, path.name):
                    fills.append((weapon_id, path.name))
                elif held > 0 and second > 0 and abs(held - second) > 0.02 * held:
                    duplicates.append((first, weapon, path.name))
                continue
            seen[weapon_id] = weapon
            for key in keys:
                by_identity.setdefault(key, weapon)
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

    # Register only the sources the research actually rests on: the one a
    # value cites, and the one that states a designation when that is a
    # different document (a service index is often published apart from
    # the figures).
    referenced = {row["source_id"] for row in found_weapons if row.get("source_id")}
    for row in found_weapons:
        referenced |= {s for s in (row.get("alias_sources") or []) if s}
        if row.get("mass_source_id"):
            referenced.add(row["mass_source_id"])
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
                # The batch states where in the document the figure sits,
                # and the digest of the bytes that were read. A reader who
                # needs the bytes asks the local cache; the digest is what
                # makes that check possible without vendoring the page.
                "locator": source.get("locator", "weapon twist"),
                "published": "",
                "retrieved": retrieved or "2026-09-22",
                "url": source.get("url", ""),
                "sha256": source.get("sha256", ""),
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
    held = (
        {w["weapon_id"]: w for w in json.loads(DB.read_text(encoding="utf-8"))}
        if DB.exists()
        else {}
    )
    # The catalogue already names weapons that no batch carries, so the
    # identity guard has to see them too: a recapture of a held weapon
    # under a new id would otherwise enter beside it and make every query
    # carrying its designation ambiguous.
    held_identity = {}
    for weapon in held.values():
        for key in set(weapon.get("aliases") or []) | identity_keys(weapon):
            if len(key) >= IDENTITY_MIN:
                held_identity.setdefault(key, weapon["weapon_id"])
    # A recapture of a held weapon under a NEW id is renamed onto the held
    # id before anything is built, so its figures and its designations
    # reach the held entry instead of entering beside it. The held id is
    # the one the generated table and the tests already name, so it is the
    # one that survives.
    recaptures = 0
    for row in found_weapons:
        if not row.get("source_id") or row["weapon_id"] in held:
            continue
        same = {
            held_identity[key]
            for key in identity_keys(row)
            if key in held_identity and held_identity[key] != row["weapon_id"]
        }
        if same:
            row["weapon_id"] = sorted(same)[0]
            recaptures += 1
    # Rebuild only the records this tool CAN emit, so neither a record
    # added by another tool nor one whose research carries no citation is
    # dropped. A row with no source_id produces no entry, so it does not
    # own the held one either: claiming it and then emitting nothing is
    # how the held record used to disappear.
    owned = {
        row["weapon_id"]
        for row in found_weapons
        if row.get("weapon_id") and row.get("source_id")
    }
    weapons = [w for w in held.values() if w["weapon_id"] not in owned]

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
        # A launcher fires a rocket or a recoilless round. It has no
        # chambering and no cartridge, so the record names the round it
        # fires instead. The validator enforces the same split, stated
        # once in data/ballistics/SCHEMA.md.
        if row.get("kind") == "launcher":
            values = {
                "rocket": {
                    "value": row.get("rocket", ""),
                    "unit": "name",
                    "source": source_id,
                    "grade": grade,
                },
            }
        else:
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
        # The maker's published mass, when the same document states it.
        # fnc_getWeaponMass prefers it over the family median, so a weapon
        # that carries one needs no fallback at all.
        if row.get("mass_kg"):
            mass_source = row.get("mass_source_id") or source_id
            values["mass_kg"] = {
                "value": round(float(row["mass_kg"]), 4),
                "unit": "kg",
                "source": mass_source,
                "grade": {
                    "standard": "standard",
                    "manual": "documented",
                    "manufacturer": "claimed",
                }.get(by_source.get(mass_source, {}).get("type"), "claimed"),
            }
        cartridge_id, candidates = chambering.resolve(
            row.get("cartridge", ""), chambering_index, chambering_aliases
        )
        # A launcher fires a rocket or a recoilless round: it HAS no
        # chambering, so its empty one is not an unresolved gap and must
        # not be reported as research still to do.
        if not cartridge_id and row.get("kind") != "launcher":
            unresolved_chamberings += 1
        # This tool owns the chambering and the rifling. Any OTHER value
        # on the held record was sourced by another tool, so it is carried
        # across rather than overwritten: rebuilding an entry must not
        # silently delete a published mass that this generator never
        # researched and cannot restore.
        previous = held.get(row["weapon_id"], {})
        for key, value in (previous.get("values") or {}).items():
            kept = values.get(key)
            # A later capture must not DOWNGRADE a value: a chambering
            # already taken from a standard is better evidence than the
            # same chambering repeated by an encyclopaedia, so the held
            # value stays and the batch only fills what is missing.
            if kept is None or GRADE_RANK.get(
                str(value.get("grade")), 0
            ) > GRADE_RANK.get(str(kept.get("grade")), 0):
                values[key] = value
        # The carried-over values come from a record built before the
        # launcher rule, so a launcher may still hold the empty cartridge
        # value that rule retires. The rocket is the record now.
        if row.get("kind") == "launcher":
            values.pop("cartridge", None)
        weapons.append(
            {
                "weapon_id": row["weapon_id"],
                "names": [row["name"]] if row.get("name") else [row["weapon_id"]],
                # A batch may carry the designations the held source
                # states for the weapon - a service designation, an index,
                # a second published name. They are identity spellings,
                # not figures, and they are what lets a classname that
                # names the weapon another way still resolve to it.
                "aliases": sorted(
                    set(aliases(row["weapon_id"], row.get("name", "")))
                    | {
                        normalise(a)
                        for a in (row.get("aliases") or [])
                        if len(normalise(a)) >= 2
                    }
                    | set(previous.get("aliases") or [])
                ),
                "manufacturer": row.get("manufacturer", "")
                or previous.get("manufacturer", ""),
                # What KIND of weapon this is, when it is not the kind
                # the corpus is mostly made of. A small arm needs no mark.
                # A launcher fires a rocket or a recoilless round, so it
                # has no rifling and its mass is in its own band; a
                # crew-served gun is not carried at all. Both are held with
                # their published figures, and neither joins a family
                # median for a weapon a soldier picks up.
                **(
                    {"kind": row["kind"]}
                    if row.get("kind")
                    else ({"kind": previous["kind"]} if previous.get("kind") else {})
                ),
                "cartridge_id": cartridge_id or previous.get("cartridge_id", ""),
                "note": row.get("source_note", ""),
                "values": values,
            }
        )

    weapons, merged = consolidate(weapons)

    # A disagreement between two batches is recorded, never averaged.
    conflicts = (
        json.loads(CONFLICTS.read_text(encoding="utf-8")) if CONFLICTS.exists() else []
    )
    conflicts = [
        c for c in conflicts if not str(c.get("source_b", "")).startswith("batch_")
    ]
    # A disagreement may already be recorded by hand, from the two sources
    # themselves rather than from the batch that carried the second one.
    # Re-adding it would ledger one disagreement twice, so the same
    # weapon, field and pair of values is only written once.
    recorded = {
        (
            str(c.get("entity")),
            str(c.get("field")),
            c.get("value_a"),
            c.get("value_b"),
        )
        for c in conflicts
    }
    for first, second, filename in duplicates:
        key = (
            str(first["weapon_id"]),
            "twist_m",
            round(twist_mm(first) / 1000, 5),
            round(twist_mm(second) / 1000, 5),
        )
        if key in recorded:
            continue
        recorded.add(key)
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
        f"recaptures merged: {recaptures}, "
        f"duplicate models fused: {len(merged)}, "
        f"sources added: {added_sources}, rows skipped for no source: {skipped}, "
        f"disagreements: {len(duplicates)}, "
        f"chamberings unresolved: {unresolved_chamberings}"
    )


if __name__ == "__main__":
    main()
