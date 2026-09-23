#!/usr/bin/env python3
"""Merge the recoil inputs into the database.

Free recoil energy needs four numbers. Two are already held: the ejecta
mass (the projectile layer) and the muzzle velocity (the load layer). This
tool merges the other two:

  mass_kg        onto a weapon record, from the weapon-mass captures
                 under sources/ (a maker page or manual, checked against
                 the verbatim line). The batch files weapon_mass_a and
                 weapon_mass_b join the primary captures.
  charge_mass_g  onto a load record, from sources/load_charges.json

A charge is matched to a load by the cartridge and the bullet mass, so a
charge enters only when exactly one load matches. A service charge is a
tier 2 document. A reloading charge is a manufacturer table and stays a
weaker grade.

Run:  python3 tools/validation/gen_recoil_data.py
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gen_weapons import classify  # noqa: E402  - shared source grading

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
WEAPONS = DATA / "weapons.json"
LOADS = DATA / "loads.json"
CARTRIDGES = DATA / "cartridges.json"
SOURCES = DATA / "sources.json"
CONFLICTS = DATA / "conflicts.json"

# The weapon-mass captures. The primary captures are taken at face value;
# the manual and candidate sets must state verified: true on the row. A new
# batch file joins here, so a landed capture needs no code change and the
# candidates file (all leads) can never be swept in by a pattern.
MASS_FILES = (
    "weapon_mass.json",
    "weapon_mass_manuals.json",
    "weapon_mass_a.json",
    "weapon_mass_b.json",
)
NEEDS_VERIFICATION = {"weapon_mass_manuals.json", "weapon_mass_candidates.json"}

GRAIN_G = 0.06479891
# An archived maker manual is a published document, not a maker web page.
TIER_OVERRIDES = {"manual_": (3, "manual", "documented")}


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def register(sources, known, path):
    if not path.exists():
        return 0
    added = 0
    for source in json.loads(path.read_text(encoding="utf-8")).get("sources", []):
        sid = source["source_id"]
        if sid in known:
            continue
        tier, kind, _ = classify(source)
        for prefix, (tier, kind, _) in TIER_OVERRIDES.items():
            if sid.startswith(prefix):
                break
        sources.append(
            {
                "source_id": sid,
                "tier": tier,
                "type": kind,
                "title": source.get("title", sid),
                "edition": "",
                "identifier": sid,
                "locator": "recoil input",
                "published": "",
                "retrieved": "2026-09-22",
                "url": source.get("url", ""),
                "licence": "public domain" if tier <= 3 else "maker published data",
                "primary_held": bool(source.get("sha256")),
                "note": "Recoil input."
                + ("" if source.get("sha256") else " Cited but not held."),
            }
        )
        known.add(sid)
        added += 1
    return added


def grade_for(sources, sid):
    tier = next((s["tier"] for s in sources if s["source_id"] == sid), 4)
    return "standard" if tier == 1 else "documented" if tier in (2, 3) else "claimed"


def cartridge_lookup(by_cart, text):
    """A name, then the same name with the unit word and case dropped.

    A charge row writes "6.5mm Creedmoor" where the register holds
    "6.5 Creedmoor", and "7.62x54mmR" where it holds "7,62 x 54 R".
    Both differ only by the interior "mm", so the mm-free form is a
    candidate as well as the trailing-descriptor forms.
    """
    base = normalise(text)
    for candidate in (
        base,
        re.sub(r"mmnato$", "", base),
        re.sub(r"mm$", "", base),
        re.sub(r"nato$", "", base),
        base.replace("mm", ""),
    ):
        if candidate and candidate in by_cart:
            return by_cart[candidate]
    return None


def grain_of(text):
    match = re.search(r"(\d+(?:\.\d+)?)\s*gr", text or "", re.I)
    return float(match.group(1)) if match else None


# A reloading table names its bullet ("168 Sierra HPBT"). Several loads
# can share one bullet weight, and the bullet identity in the note is
# what tells them apart.
BULLET_TOKENS = (
    "hpbt",
    "sbt",
    "tmk",
    "matchking",
    "vmax",
    "xtp",
    "ntx",
    "scenar",
    "lrx",
    "tug",
    "fmjbt",
    "fmjsp",
    "spire",
    "jhp",
    "jhp",
    "hap",
    "otm",
    "eld-x",
    "eldx",
    "eld",
    "berger",
    "sierra",
    "hornady",
    "lapua",
    "barnes",
    "speer",
    "brenneke",
    "alsa",
    "berry",
    "hybrid",
)


def bullet_tokens(text):
    low = normalise(text)
    return [token for token in BULLET_TOKENS if normalise(token) in low]


def same_bullet(tokens, projectile):
    """True when the note's bullet identity appears in the load's name."""
    if not tokens:
        return False
    target = normalise(projectile)
    return any(normalise(token) in target for token in tokens)


def main():
    weapons = json.loads(WEAPONS.read_text(encoding="utf-8"))
    loads = json.loads(LOADS.read_text(encoding="utf-8"))
    cartridges = json.loads(CARTRIDGES.read_text(encoding="utf-8"))
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    conflicts = json.loads(CONFLICTS.read_text(encoding="utf-8"))
    known = {s["source_id"] for s in sources}

    added_sources = 0
    for name in MASS_FILES + ("load_charges.json",):
        added_sources += register(sources, known, SRC / name)

    # ─── Weapon mass ─────────────────────────────────────────────────────
    # The index holds the key, the aliases and the readable name, so a
    # maker row matches even when its key differs from ours.
    by_key = {}
    for record in weapons:
        by_key.setdefault(record["weapon_id"], record)
        for alias in record.get("aliases", []):
            by_key.setdefault(alias, record)
        for name in record.get("names", []):
            by_key.setdefault(normalise(name), record)

    def find_weapon(row):
        hit = by_key.get(normalise(row.get("weapon_key", "")))
        if hit is not None:
            return hit
        hit = by_key.get(normalise(row.get("weapon", "")))
        if hit is not None:
            return hit
        # The maker often leads the model name, so try it without the
        # maker as well.
        name = normalise(row.get("weapon", ""))
        maker = normalise(row.get("maker", ""))
        if maker and name.startswith(maker):
            return by_key.get(name[len(maker) :])
        return None

    masses = matched_mass = mass_conflicts = twist_only = 0
    for name in MASS_FILES:
        path = SRC / name
        if not path.exists():
            continue
        for row in json.loads(path.read_text(encoding="utf-8"))["weights"]:
            if not row.get("verified", name not in NEEDS_VERIFICATION):
                continue
            record = find_weapon(row)
            if record is None:
                continue
            if "mass_kg" not in row:
                # A row may state only a twist. A twist enters through the
                # weapon catalogue, not here.
                twist_only += 1
                continue
            masses += 1
            value = round(float(row["mass_kg"]), 3)
            source_id = row["source_id"]
            grade = grade_for(sources, source_id)
            existing = record["values"].get("mass_kg")
            if existing is not None:
                if abs(existing["value"] - value) > 0.02 * existing["value"]:
                    if any(
                        c.get("entity") == record["weapon_id"]
                        and c.get("source_b") == source_id
                        and c.get("value_b") == value
                        for c in conflicts
                    ):
                        mass_conflicts += 1
                        continue
                    conflicts.append(
                        {
                            "entity": record["weapon_id"],
                            "field": "mass_kg",
                            "value_a": existing["value"],
                            "source_a": existing["source"],
                            "value_b": value,
                            "source_b": source_id,
                            "resolution": "Kept the first value. Recorded both.",
                            "rule_applied": "Two sources disagree. It is recorded, never averaged.",
                            "date": "2026-09-22",
                        }
                    )
                    mass_conflicts += 1
                continue
            record["values"]["mass_kg"] = {
                "value": value,
                "unit": "kg",
                "source": source_id,
                "grade": grade,
            }
            matched_mass += 1

    # ─── Load charge ─────────────────────────────────────────────────────
    by_cart = {}
    for record in cartridges:
        for name in record.get("names", []):
            by_cart.setdefault(normalise(name), record["cartridge_id"])

    charges = matched_charge = service_level = 0
    no_lookup = no_load = ambiguous = 0
    by_id = {record["cartridge_id"]: record for record in cartridges}
    charge_file = SRC / "load_charges.json"
    if charge_file.exists():
        for row in json.loads(charge_file.read_text(encoding="utf-8"))["charges"]:
            cartridge_id = cartridge_lookup(by_cart, row.get("cartridge", ""))
            if cartridge_id is None:
                no_lookup += 1
                continue
            charges += 1
            source_id = row["source_id"]
            grade = grade_for(sources, source_id)
            grams = round(float(row["charge_gr"]) * GRAIN_G, 3)
            # A service charge is the actual factory charge for the
            # cartridge, so it belongs on the cartridge record. It applies
            # to every load of that cartridge, which the load table may not
            # hold, and it needs no matching load. A reloading charge is
            # bullet specific and stays on the load.
            if row.get("kind") == "service":
                cartridge = by_id.get(cartridge_id)
                if (
                    cartridge is not None
                    and "service_charge_mass_g" not in cartridge["values"]
                ):
                    cartridge["values"]["service_charge_mass_g"] = {
                        "value": grams,
                        "unit": "g",
                        "source": source_id,
                        "grade": grade,
                    }
                    cartridge["values"]["service_charge_powder"] = {
                        "value": row.get("powder", "") or "not stated",
                        "source": source_id,
                        "grade": grade,
                    }
                    service_level += 1
                continue
            target = float(row["bullet_gr"])
            hits = [
                load
                for load in loads
                if load.get("cartridge_id") == cartridge_id
                and grain_of(load.get("projectile", "")) is not None
                and abs(grain_of(load["projectile"]) - target) <= 0.6
            ]
            if not hits:
                # The table carries a bullet the load table does not hold.
                no_load += 1
                continue
            if len(hits) > 1:
                # One repeated name is one bullet, so every copy takes the
                # charge. Different names are different bullets, and only
                # the note's bullet identity tells them apart.
                if len({normalise(h.get("projectile", "")) for h in hits}) > 1:
                    tokens = bullet_tokens(row.get("note", ""))
                    picked = [
                        h for h in hits if same_bullet(tokens, h.get("projectile", ""))
                    ]
                    if len(picked) != 1:
                        ambiguous += 1
                        continue
                    hits = picked
            for load in hits:
                if "charge_mass_g" in load["values"]:
                    continue
                load["values"]["charge_mass_g"] = {
                    "value": round(float(row["charge_gr"]) * GRAIN_G, 3),
                    "unit": "g",
                    "source": source_id,
                    "grade": grade,
                }
                load["values"]["charge_kind"] = {
                    "value": row.get("kind", "reloading"),
                    "source": source_id,
                    "grade": grade,
                }
                matched_charge += 1

    WEAPONS.write_text(json.dumps(weapons, indent=1) + "\n", encoding="utf-8")
    LOADS.write_text(json.dumps(loads, indent=1) + "\n", encoding="utf-8")
    CARTRIDGES.write_text(json.dumps(cartridges, indent=1) + "\n", encoding="utf-8")
    SOURCES.write_text(json.dumps(sources, indent=1) + "\n", encoding="utf-8")
    CONFLICTS.write_text(json.dumps(conflicts, indent=1) + "\n", encoding="utf-8")
    print(
        f"sources added: {added_sources}, twist-only rows skipped: {twist_only}, "
        f"weapon masses merged: {matched_mass} "
        f"(of {masses} rows, {mass_conflicts} disagreements), "
        f"charge rows considered: {charges}, service charges on the "
        f"cartridge: {service_level}, merged onto a load: {matched_charge}, "
        f"unmatched: {no_load} no load at that bullet, {ambiguous} "
        f"unresolved, {no_lookup} unknown cartridge"
    )


if __name__ == "__main__":
    main()
