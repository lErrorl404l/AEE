#!/usr/bin/env python3
"""Gate for the verified ballistics database (ADR-003).

The contract: no value enters without a source, a grade and a unit.
A grade of "standard" needs a held tier 1 source. A grade of
"verified" needs two independent sources. A grade of "unverified" is
quarantined, and the runtime generator skips it.

Run:  python3 tools/validation/validate_ballistics_data.py
Exit: 0 when the database obeys the contract, 1 when it does not.
"""

import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

DATA = Path(__file__).parents[2] / "data" / "ballistics"

GRADES = {
    "standard",
    "verified",
    "measured",
    "claimed",
    "corroborated",
    "documented",
    "derived",
    "unverified",
}
SOURCE_TYPES = {"standard", "manual", "measurement", "manufacturer", "compilation"}
ENTRY_TIERS = {1, 2, 3, 4}

# Field name to (minimum, maximum), exclusive of both ends where given.
# The upper bounds cover the cannon class (105 mm to 125 mm tank guns and
# 20 to 40 mm autocannon). A 120 mm round exceeds every small-arms bound, so
# a cannon value must pass this widen before it can enter the database.
RANGES = {
    "max_pressure_mpa": (0.1, 1000.0),
    "proof_pressure_mpa": (0.1, 1500.0),
    "standard_twist_m": (0.0, 2.0),  # 0 is a smoothbore
    "standard_twist_pistol_m": (0.0, 2.0),
    "standard_twist_rifle_m": (0.0, 2.0),
    "calibre_mm": (0.1, 200.0),  # cannon class
    "bore_mm": (0.1, 200.0),  # cannon class
    "case_length_mm": (1.0, 1500.0),  # cannon class
    "reference_barrel_mm": (10.0, 8000.0),  # cannon class
    "grooves": (1, 24),
    "mass_g": (0.1, 50000.0),  # cannon class
    "length_mm": (0.1, 2000.0),  # cannon class
    "diameter_mm": (0.1, 200.0),  # cannon class
    "bc_g1": (0.001, 2.0),
    "bc_g7": (0.001, 2.0),
    "sectional_density": (0.01, 2.0),
    "min_twist_m": (0.0, 2.0),
    "twist_m": (0.0, 2.0),
    "required_twist_m": (0.0, 2.0),
    "service_velocity_ms": (1.0, 2500.0),  # cannon class
    "service_pressure_mpa": (0.1, 1000.0),
    "twist_in": (0.0, 100.0),
    # Cannon schema fields (phase 1). The propellant or charge mass and the
    # armour penetration reference, each with a source and a unit.
    "charge_mass_g": (0.1, 50000.0),
    "penetration_mm_rha": (0.1, 2000.0),
}

# Fields that carry a dimension, so a unit is required. The ballistic
# coefficients and the sectional density are ratios and carry no unit.
UNIT_REQUIRED = set(RANGES) - {"bc_g1", "bc_g7", "sectional_density"}

DRAG_FUNCTIONS = DATA / "sources" / "drag_functions.json"

ID_FIELD = {
    "cartridges": "cartridge_id",
    "projectiles": "projectile_id",
    "loads": "load_id",
    "weapons": "weapon_id",
}


def load(name):
    path = DATA / name
    if not path.exists():
        raise SystemExit(f"missing data file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def check_sources(sources, errors):
    ids = set()
    for s in sources:
        sid = s.get("source_id", "<none>")
        if sid in ids:
            errors.append(f"source {sid}: duplicate source_id")
        ids.add(sid)
        if s.get("tier") not in range(1, 7):
            errors.append(f"source {sid}: tier must be 1 to 6")
        if s.get("type") not in SOURCE_TYPES:
            errors.append(f"source {sid}: type must be one of {sorted(SOURCE_TYPES)}")
        if not isinstance(s.get("primary_held"), bool):
            errors.append(f"source {sid}: primary_held must be true or false")
        for field in ("title", "identifier", "retrieved"):
            if not s.get(field):
                errors.append(f"source {sid}: {field} is required")
    return {s["source_id"]: s for s in sources}


def entry_source_ids(records):
    """Return every source id a value entry cites.

    The entry source is the source field of a value, its corroborating
    sources, and the classification source of a record.
    """
    ids = set()
    for record in records:
        for entry in (record.get("values") or {}).values():
            if not isinstance(entry, dict):
                continue
            if entry.get("source"):
                ids.add(entry["source"])
            for c in entry.get("corroborated_by") or []:
                ids.add(c)
        cls = record.get("classification")
        if isinstance(cls, dict) and cls.get("classification_source"):
            ids.add(cls["classification_source"])
    return ids


def held_filename(source):
    """Return the held file name for a source, or None when none is named.

    A source names its held file with `held_file`. Without that field the
    file is the source id plus the url suffix, the rule the vehicle register
    uses. The held file name need not equal the source id.
    """
    explicit = source.get("held_file")
    if isinstance(explicit, str) and explicit:
        return explicit
    suffix = Path(urlparse(str(source.get("url") or "")).path).suffix.lower()
    if not re.fullmatch(r"\.[A-Za-z0-9]{1,8}", suffix):
        return None
    return f"{source['source_id']}{suffix}"


def sha256_file(path):
    """Return the SHA-256 digest of the held bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_held_sources(sources, entry_ids, sources_dir, errors):
    """Every held tier 1 to 4 entry source must record a held sha256.

    A source is held only when its bytes are locatable and their digest is
    recorded as `archive_hash` or `held_pdf_sha256`. Bytes that are not
    vendored are tolerated, the same rule as the vehicle gate, so a fresh
    clone passes. The recorded digest is verified against the bytes whenever
    the bytes are present.
    """
    for source in sources:
        sid = source.get("source_id", "<none>")
        if source.get("tier") not in ENTRY_TIERS:
            continue
        if source.get("primary_held") is not True:
            continue
        if sid not in entry_ids:
            continue
        name = held_filename(source)
        if name is None:
            continue
        path = sources_dir / name
        if not path.exists():
            continue
        recorded = source.get("archive_hash") or source.get("held_pdf_sha256")
        if not recorded:
            errors.append(f"source {sid}: primary_held is true but no held sha256")
            continue
        actual = sha256_file(path)
        if actual != source.get("archive_hash") and actual != source.get(
            "held_pdf_sha256"
        ):
            errors.append(
                f"source {sid}: held file {name} digest {actual} does not match "
                f"the recorded digest"
            )


def check_value(kind, record_id, field, entry, by_id, errors):
    where = f"{kind} {record_id} field {field}"
    if "value" not in entry or entry["value"] in (None, ""):
        errors.append(f"{where}: value is required")
    sid = entry.get("source")
    src = by_id.get(sid)
    if not sid:
        errors.append(f"{where}: source is required")
    elif src is None:
        errors.append(f"{where}: unknown source {sid}")
    grade = entry.get("grade")
    if grade not in GRADES:
        errors.append(f"{where}: grade must be one of {sorted(GRADES)}")
        return

    if grade == "standard":
        if not src or src["tier"] != 1:
            errors.append(f"{where}: grade standard needs a tier 1 source")
        elif not src["primary_held"]:
            errors.append(f"{where}: grade standard needs a held primary document")
    elif grade == "verified":
        corr = entry.get("corroborated_by", [])
        if len(set(corr)) < 2:
            errors.append(f"{where}: grade verified needs two independent sources")
        for c in corr:
            if c not in by_id:
                errors.append(f"{where}: unknown corroborating source {c}")
            elif by_id[c]["tier"] > 3:
                errors.append(f"{where}: source {c} is too weak to corroborate")
    elif grade == "measured":
        if not src or src["type"] != "measurement":
            errors.append(f"{where}: grade measured needs a measurement source")
    elif grade == "claimed":
        if not src or src["type"] != "manufacturer":
            errors.append(f"{where}: grade claimed needs a manufacturer source")
    elif grade == "corroborated":
        corr = entry.get("corroborated_by", [])
        if not any(c in by_id and by_id[c]["tier"] <= 3 for c in corr):
            errors.append(f"{where}: grade corroborated needs an independent source")
    elif grade == "documented":
        if not src or src["tier"] not in (2, 3):
            errors.append(f"{where}: grade documented needs a tier 2 or 3 source")
    elif grade == "derived":
        if not entry.get("formula"):
            errors.append(f"{where}: grade derived needs a formula")

    if src and src["tier"] not in ENTRY_TIERS:
        errors.append(f"{where}: tier {src['tier']} cannot be an entry source")

    value = entry.get("value")
    if field in RANGES and isinstance(value, (int, float)):
        low, high = RANGES[field]
        if not low <= value <= high:
            errors.append(f"{where}: {value} outside the sane band {low} to {high}")
    if field in RANGES and not isinstance(value, (int, float)):
        errors.append(f"{where}: must be a number")
    if field in UNIT_REQUIRED and not entry.get("unit"):
        errors.append(f"{where}: unit is required")


def check_records(kind, records, by_id, errors):
    idf = ID_FIELD[kind]
    seen = set()
    for r in records:
        rid = r.get(idf, "<none>")
        if rid in seen:
            errors.append(f"{kind} {rid}: duplicate {idf}")
        seen.add(rid)
        values = r.get("values", {})
        if not isinstance(values, dict) or not values:
            errors.append(f"{kind} {rid}: no values")
        for field, entry in values.items():
            if not isinstance(entry, dict):
                errors.append(f"{kind} {rid} field {field}: entry must be an object")
                continue
            check_value(kind, rid, field, entry, by_id, errors)
        cls = r.get("classification")
        if cls is not None and cls.get("classification_source") not in by_id:
            errors.append(
                f"{kind} {rid}: classification_source must name a known source"
            )


def check_references(weapons, cartridges, gaps, errors):
    """Every joined cartridge_id names a cartridge. Every blank one is
    reported. A weapon with a blank id falls back to its own twist alone,
    and the gap report is where that is recorded, so a blank id that no
    report names is an unreported hole."""
    cartridge_ids = {c["cartridge_id"] for c in cartridges}
    for weapon in weapons:
        cid = weapon.get("cartridge_id", "")
        if not cid:
            continue
        if cid not in cartridge_ids:
            errors.append(
                f"weapon {weapon['weapon_id']}: cartridge_id {cid} is not a cartridge"
            )
    if gaps is None:
        return
    reported = set()
    for row in gaps.get("gaps", []):
        for wid in row["weapons"]:
            reported.add(wid)
    for weapon in weapons:
        if weapon.get("cartridge_id") or weapon["weapon_id"] in reported:
            continue
        errors.append(
            f"weapon {weapon['weapon_id']}: no cartridge_id and no chambering gap row"
        )


def check_drag_models(errors):
    """Every drag model name must map to a source that holds it.

    A model maps directly through the sources table, or through a
    placeholder that names the held model it reuses. An unsourced curve
    is never presented as sourced.
    """
    data = json.loads(DRAG_FUNCTIONS.read_text(encoding="utf-8"))
    models = data.get("models", {})
    sources = data.get("sources", {})
    placeholders = data.get("placeholder_models", {})
    for model in models:
        if model in sources:
            if not sources[model]:
                errors.append(f"drag model {model}: source url is empty")
            continue
        if model in placeholders:
            entry = placeholders[model]
            reuse = entry.get("reuses", "")
            if reuse not in sources:
                errors.append(
                    f"drag model {model}: placeholder reuses unknown model {reuse}"
                )
            if not entry.get("note"):
                errors.append(f"drag model {model}: placeholder needs a note")
            continue
        errors.append(f"drag model {model}: no source and no placeholder entry")
    for model in placeholders:
        if model not in models:
            errors.append(f"placeholder {model}: no matching drag model")
    for model in sources:
        if model not in models:
            errors.append(f"source {model}: no matching drag model")


def main():
    errors = []
    sources = load("sources.json")
    by_id = check_sources(sources, errors)
    entry_ids = set()
    for kind in ("cartridges", "projectiles", "loads", "weapons"):
        records = load(f"{kind}.json")
        check_records(kind, records, by_id, errors)
        entry_ids |= entry_source_ids(records)
    check_held_sources(sources, entry_ids, DATA / "sources", errors)
    load("conflicts.json")
    check_drag_models(errors)
    gaps_path = DATA / "sources" / "chambering_gaps.json"
    gaps = (
        json.loads(gaps_path.read_text(encoding="utf-8"))
        if gaps_path.exists()
        else None
    )
    check_references(load("weapons.json"), load("cartridges.json"), gaps, errors)

    if errors:
        print("ballistics data gate: FAIL")
        for e in errors:
            print(f"  {e}")
        return 1
    print(
        f"ballistics data gate: PASS ({len(sources)} sources, "
        f"{len(load('cartridges.json'))} cartridges, "
        f"{len(load('projectiles.json'))} projectiles, "
        f"{len(load('loads.json'))} loads)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
