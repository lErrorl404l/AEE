#!/usr/bin/env python3
"""Generate the weapon database from the ABE seed (issue #167).

Reads real_weapons.tsv (2,295 real weapons, source-cited) and writes
the SQF _WEAPONS table in fnc_getWeaponProperties.sqf.

Each weapon FAMILY carries its real barrel-length -> MV curve anchors
(the seed's measured per-barrel muzzle velocities: HK416 264mm->767,
368->862, 419->898, 508->940 m/s) plus the twist/pressure.  The SQF
classifier matches the family keyword (HK416, LICC, SPEAR, Mk18 ...),
then the barrel-length curve computes the real MV at the weapon's
measured barrel (the derivation feeds the ammo MV).

Usage: python3 tools/validation/gen_weapon_table.py
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

SEED_DIR = Path("/home/matt/Development/AceBallisticsExtention/data")
OUT = (
    Path(__file__).parents[2]
    / "addons/ballistics/functions/fnc_getWeaponProperties.sqf"
)

# The family keywords the classifier matches (the real weapon families
# mods carry, mapped to the seed's weapon_id prefixes).
FAMILIES = [
    "hk416",
    "hk417",
    "m4a1",
    "m16a4",
    "m249",
    "m240",
    "pkm",
    "svd",
    "awm",
    "awp",
    "m24",
    "m107",
    "m82",
    "sr25",
    "mp5",
    "glock",
    "ak74",
    "akm",
    "ak47",
    "g36",
    "scar",
    "famas",
    "aug",
    "sako",
    "mrad",
    "spear",
    "licc",
    "rec7",
    "l85",
    "g3",
    "fal",
    "mk18",
    "ddm4",
    "qbz",
    "tt33",
    "makarov",
    "usp",
    "p226",
    "beretta",
    "m1911",
    "vector",
    "p90",
    "uzi",
    "mp7",
    "mpx",
    "mcx",
    "ar18",
    "solgw",
    "rdak",
    "lmt",
    "mk12",
    "m110",
    "m40",
    "m2010",
    "psl",
    "negev",
    "minimi",
    "mg3",
    "rpk",
    "m60",
    "m14",
    "m1",
    "m3",
]


def load_weapons():
    """real_weapons.tsv -> per-family barrel->(mv, twist, pressure) anchors."""
    data = defaultdict(list)
    with open(SEED_DIR / "real_weapons.tsv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            wid = (r.get("weapon_id") or "").lower()
            mv = r.get("muzzle_velocity_ms")
            barrel = r.get("barrel_mm")
            if not mv or not barrel:
                continue
            try:
                mv_f = float(mv)
                b_f = float(barrel)
                twist_f = (
                    float(r.get("twist_mm") or 0) / 1000 if r.get("twist_mm") else 0.178
                )
                press_f = (
                    float(r.get("pressure_mpa") or 0) if r.get("pressure_mpa") else 430
                )
            except ValueError:
                continue
            for fam in FAMILIES:
                if fam in wid:
                    data[fam].append((round(b_f, 1), mv_f, round(twist_f, 4), press_f))
                    break
    # dedup by barrel, keep the median MV for duplicates
    out = {}
    for fam, rows in data.items():
        seen = defaultdict(list)
        for b, mv, tw, pr in rows:
            seen[b].append((mv, tw, pr))
        anchors = []
        for b in sorted(seen):
            mvs = [x[0] for x in seen[b]]
            mvs.sort()
            mv = mvs[len(mvs) // 2]  # median
            tw = seen[b][0][1]
            pr = seen[b][0][2]
            anchors.append([b, mv, tw, pr])
        out[fam] = anchors
    return out


def main():
    weapons = load_weapons()
    print(f"families: {len(weapons)}")

    lines = []
    lines.append("// AUTO-GENERATED from the ABE seed (issue #167).")
    lines.append("// Do not edit by hand - run tools/validation/gen_weapon_table.py")
    lines.append("// Source: real_weapons.tsv (2,295 real weapons).")
    lines.append("// Flat rows: [family, barrelM, mvAtBarrel, twistM, pressureMPa]")
    lines.append("// (the barrel-length -> MV curve anchors, one row per point).")
    lines.append("private _WEAPON_ROWS = [")
    for fam, anchors in sorted(weapons.items()):
        for b, mv, tw, pr in anchors:
            lines.append(f'    ["{fam}", {b}, {mv}, {tw}, {pr}],')
    lines.append("];")
    lines.append("")
    # The family keyword list (the classifier scan, longest first).
    lines.append("private _familyKeys = [")
    for fam in sorted(weapons, key=len, reverse=True):
        lines.append(f'    "{fam}",')
    lines.append("];")
    lines.append("")

    src = OUT.read_text(encoding="utf-8")
    start = src.find("private _WEAPON_ROWS = [")
    end = src.find("// ─── The family resolution")
    if start < 0 or end < 0:
        raise SystemExit("splice markers not found in the SQF")
    block = "\n".join(lines)
    src = src[:start] + block + "\n" + src[end:]
    OUT.write_text(src, encoding="utf-8")
    print(f"wrote {len(weapons)} weapon families")


if __name__ == "__main__":
    main()
