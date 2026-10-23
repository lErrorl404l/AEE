#!/usr/bin/env python3
"""Add the Sierra special loads, each with the barrel it was measured in.

One load per Sierra bullet in the cartridge its bore is normally loaded in.
The far edge of the corpus is a bullet catalogue, not a set of loads: a
bullet enters with a measured ballistic coefficient and no velocity, so the
independent verifier cannot compare it. A published velocity with the
barrel it was measured in puts the bullet back in the comparison.

The designation comes from the projectile record, not from the sheet, so an
extract never has to restate a name the catalogue already holds. The sheet
names the bullet by part number, and the part number is the projectile id.

The velocity is a manufacturer claim: Sierra measured it, nobody
corroborated it. It enters at grade claimed.

Run after gen_loads_from_velocity.py and before the runtime projections:
  python3 tools/validation/gen_loads_from_sierra.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
DB = DATA / "loads.json"
EXTRACT = DATA / "sources" / "sierra_velocity.json"
SOURCE_ID = "sierra_reloading_manual"

GRAIN_G = 0.06479891
FOOT_M = 0.3048

# The cartridge a bullet's bore is loaded in. A bullet record carries the
# bore, never a chambering, so the anchor has to name one: the one the
# bullet is catalogued for. First name that the cartridge register holds
# wins, so the choice is reviewable here and not buried in the data.
BORE_CARTRIDGE = {
    5.18: ("204 Ruger",),
    5.66: ("22 Hornet",),
    5.69: ("223 Remington",),
    6.17: ("243 Winchester", "6mm Remington"),
    6.53: ("25-06 Remington", "257 Roberts"),
    6.71: ("6.5 Creedmoor",),
    7.04: ("270 Winchester",),
    7.21: ("7mm-08 Remington", "7mm Remington Magnum"),
    7.82: ("308 Winchester",),
    7.90: ("303 British", "7.62x39mm"),
    7.92: ("7.7x58mm Arisaka",),
    8.20: ("8mm Mauser (8 x 57)",),
    8.59: ("338 Lapua Magnum", "338 Winchester Magnum"),
    9.02: ("9mm Luger",),
    9.07: ("357 Magnum",),
    9.09: ("358 Win.",),
    9.53: (".375 Holland & Holland Magnum", "375 Ruger"),
    10.16: ("10mm Auto",),
    10.41: (".41 Remington Magnum",),
    10.91: (".44 Remington Magnum",),
    11.47: ("45 Auto", ".45 ACP"),
    11.63: (".45-70 Government",),
    12.70: ("500 Special", ".500 Linebaugh"),
}
BORE_TOLERANCE_MM = 0.02


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def value(record: dict, field: str):
    entry = (record.get("values") or {}).get(field)
    return entry.get("value") if isinstance(entry, dict) else None


def designation(names: list[str]) -> str:
    """The bullet's own name without the trailing abbreviation.

    "30 Cal 155 gr HPBT MatchKing (SMK)" becomes
    "30 Cal 155 gr HPBT MatchKing". Every word is a word the projectile
    record already carries, so the verifier's token bind finds it and the
    generator invents no name. The bore prefix stays: two bores can carry
    the same bullet name ("100 gr HPBT MatchKing" in .257 and 6.5 mm), and
    the prefix is what tells them apart when a cartridge name carries no
    calibre the bind can read.
    """
    name = re.sub(r"\s*\([A-Z/]+\)\s*$", "", names[0].strip())
    return re.sub(r"\s+", " ", name).strip()


def main() -> int:
    if not EXTRACT.exists():
        raise SystemExit(f"missing extract: {EXTRACT}")
    extract = json.loads(EXTRACT.read_text(encoding="utf-8"))
    projectiles = json.loads((DATA / "projectiles.json").read_text(encoding="utf-8"))
    cartridges = json.loads((DATA / "cartridges.json").read_text(encoding="utf-8"))
    by_name = {}
    names_by_id = {}
    for record in cartridges:
        for name in record.get("names", []):
            by_name.setdefault(norm(name), record["cartridge_id"])
        names_by_id[record["cartridge_id"]] = (
            record.get("names") or [record["cartridge_id"]]
        )[0]
    wanted = {}
    for bore, candidates in BORE_CARTRIDGE.items():
        for name in candidates:
            if norm(name) in by_name:
                wanted[bore] = by_name[norm(name)]
                break

    by_part = {}
    for record in projectiles:
        parts = record["projectile_id"].split("_")
        if len(parts) == 2 and parts[0] == "sierra":
            by_part[parts[1].lstrip("0")] = record

    rows = {}
    for row in extract["loads"]:
        cartridge_id = by_name.get(norm(row["section"]))
        if cartridge_id is None:
            continue
        record = by_part.get(str(row["part"]).lstrip("0"))
        if record is None:
            continue
        diameter = value(record, "diameter_mm")
        if diameter is None:
            continue
        bore = min(BORE_CARTRIDGE, key=lambda nominal: abs(nominal - diameter))
        if abs(bore - diameter) > BORE_TOLERANCE_MM:
            continue
        if wanted.get(bore) != cartridge_id:
            continue
        mass_g = value(record, "mass_g")
        if mass_g is None or abs(mass_g / GRAIN_G - float(row["mass_gr"])) > 0.6:
            continue
        key = (cartridge_id, record["projectile_id"])
        # One velocity per bullet. The accuracy load is the sheet's headline
        # load, so it wins over the hunting load when both are printed.
        if key in rows and rows[key]["kind"] == "Accuracy Load":
            continue
        rows[key] = row

    loads = json.loads(DB.read_text(encoding="utf-8"))
    # The generator owns what it writes, so a re-run replaces its records
    # rather than adding a second copy under the same id.
    loads = [
        record
        for record in loads
        if not any(
            isinstance(entry, dict) and entry.get("source") == SOURCE_ID
            for entry in (record.get("values") or {}).values()
        )
    ]
    index = {record["load_id"]: record for record in loads}
    added = 0
    for (cartridge_id, projectile_id), row in sorted(rows.items()):
        record = by_part[projectile_id.split("_")[1].lstrip("0")]
        load_id = f"{cartridge_id}_{projectile_id}"
        if load_id in index:
            continue
        velocity = round(float(row["velocity_fps"]) * FOOT_M, 1)
        barrel = round(float(row["barrel_in"]) * 25.4, 1)
        charge = round(float(row["charge_gr"]) * GRAIN_G, 3)
        label = row["kind"]
        index[load_id] = {
            "load_id": load_id,
            "cartridge_id": cartridge_id,
            "projectile": designation(record["names"]),
            "note": (
                f"Sierra {label.lower()} for {record['names'][0]} in the "
                f"{row['section']} sheet: {row['charge_gr']} gr "
                f"{row['powder']}, {row['velocity_fps']:.0f} fps in a "
                f"{row['barrel_in']:g} in test barrel."
            ),
            "values": {
                "cartridge": {
                    "value": names_by_id[cartridge_id],
                    "unit": "name",
                    "source": SOURCE_ID,
                    "grade": "claimed",
                },
                "projectile": {
                    "value": designation(record["names"]),
                    "unit": "designation",
                    "source": SOURCE_ID,
                    "grade": "claimed",
                },
                "mv_anchors": {
                    "value": [{"barrel_mm": barrel, "mv_ms": velocity}],
                    "unit": "mm, m/s",
                    "source": SOURCE_ID,
                    "grade": "claimed",
                    "formula": f"{row['velocity_fps']:.0f} fps x 0.3048 m/s per fps; "
                    f"{row['barrel_in']:g} in x 25.4 mm per in",
                },
                "charge_mass_g": {
                    "value": charge,
                    "unit": "g",
                    "source": SOURCE_ID,
                    "grade": "claimed",
                    "formula": f"{row['charge_gr']} gr x 0.06479891 g per gr",
                },
                "propellant": {
                    "value": row["powder"],
                    "source": SOURCE_ID,
                    "grade": "claimed",
                },
            },
        }
        loads.append(index[load_id])
        added += 1
    loads.sort(key=lambda record: record["load_id"])
    DB.write_text(json.dumps(loads, indent=1) + "\n", encoding="utf-8")
    print(f"loads: Sierra special loads added: {added} (bullets ready: {len(rows)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
