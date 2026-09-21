#!/usr/bin/env python3
"""Generate the ammunition database from the ABE seed (issue #167).

Reads the ABE real-data seed (ir_ammo.tsv: 781 ammo with real BCs,
caliber_ref.tsv: 81 calibers) and writes the SQF _ROUNDS table in
fnc_getAmmoProperties.sqf.

SMART ORGANISATION: the seed's 781 entries are mostly the SAME
projectile under mod-prefixed keys (b_556x45_m995 == 556x45ballm995ap
== mag30rnd556x45m995).  The generator DEDUPLICATES by the physics
identity (caliber + mass + BC + drag model): 781 -> 187 distinct
projectiles.  Each distinct projectile gets one SQF entry with its
real MV (from the #167 research, added by the projectile-name map).

Usage: python3 tools/validation/gen_ammo_table.py
"""

from collections import defaultdict
from pathlib import Path

SEED_DIR = Path("/home/matt/Development/AceBallisticsExtention/data")
OUT = Path(__file__).parents[2] / "addons/ballistics/functions/fnc_getAmmoProperties.sqf"

# The researched real MVs for the KNOWN projectiles (issue #167: NATO
# EPVAT/STANAG, MIL-C-50, Soviet, Applied Ballistics).  A projectile
# without a researched MV falls back to its family's reference MV (the
# derivation computes the barrel-length variation).
RESEARCHED_MV = {
    "m855": 948, "m855a1": 961, "m193": 993, "m995": 1013,
    "mk262": 838, "mk318": 915, "m80": 838, "m61": 833,
    "m118lr": 786, "m993": 930, "m67": 733, "m43": 710,
    "7n6": 880, "7n10": 880, "7n22": 890, "lps": 820,
    "m33": 885, "b32": 818, "slap": 1219, "amax": 882,
    "7n1": 830, "m2ap": 856, "m74": 905,
}

# The family reference MV by caliber (the #167 anchors) - used when a
# projectile has no specific researched MV.
FAMILY_MV = {
    5.56: 948, 5.45: 880, 7.62: 838, 9.01: 351,
    12.7: 885, 8.58: 899, 6.71: 790, 7.82: 675, 11.48: 255,
    14.5: 1000, 18.5: 470, 9.27: 315,
}


def load_ammo():
    """ir_ammo.tsv: dedup by (caliber, mass, BC, drag) -> the distinct
    projectiles with their key samples."""
    rows = []
    with open(SEED_DIR / "ir_ammo.tsv", encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines()
                 if l.strip() and not l.startswith("#")]
    for line in lines[2:]:
        p = line.split("\t")
        if len(p) < 6:
            continue
        try:
            rows.append((p[0], float(p[1] or 0), float(p[2] or 0),
                         float(p[3] or 0), float(p[4] or 0), int(p[5] or 1)))
        except ValueError:
            continue

    phys = defaultdict(list)
    for key, dia, mass, bc1, bc7, drag in rows:
        if bc1 == 0 and bc7 == 0:
            continue
        bc = bc7 if bc7 else bc1
        ident = (round(dia, 1), round(mass, 1), round(bc, 3), drag)
        phys[ident].append(key)

    out = []
    import re
    for ident, keys in sorted(phys.items()):
        cal, mass, bc, drag = ident
        # A sane bullet diameter is 4-20 mm.  The seed has junk rows
        # (diameter 0.2 etc from machine extraction) - skip them; they
        # are not real rounds.
        if cal < 4.0 or cal > 20.0:
            continue
        bc1, bc7 = (0, bc) if drag == 7 else (bc, 0)
        mv = 0
        for k in keys:
            for name, val in RESEARCHED_MV.items():
                if name in k.lower():
                    mv = val
                    break
            if mv:
                break
        if not mv:
            mv = FAMILY_MV.get(cal, 905)
        tail = re.sub(r"^(ball|bullet|mag\d*rnd|ammo|b|rhs|mcc|mpp|mig|mhs)", "", keys[0])
        out.append({"keys": keys, "key": keys[0], "alias": tail,
                    "mv": mv, "bc1": bc1, "bc7": bc7, "cal": cal,
                    "mass": mass, "drag": drag})
    return out


def main():
    projectiles = load_ammo()
    print(f"distinct projectiles: {len(projectiles)} (781 seed entries collapsed)")

    lines = []
    lines.append("// AUTO-GENERATED from the ABE seed (issue #167).")
    lines.append("// Do not edit by hand - run tools/validation/gen_ammo_table.py")
    lines.append("// Source: ir_ammo.tsv (781 rounds -> distinct projectiles,")
    lines.append("// deduplicated by caliber + mass + BC + drag model).")
    lines.append("// [realMV, bcG1, bcG7, caliberMm, massG, dragModel]")
    lines.append("private _ROUNDS = createHashMapFromArray [")
    seen_aliases = set()
    for p in projectiles:
        esc = p["key"].replace('"', '\\"')
        entry = f'    ["{esc}", [{p["mv"]}, {p["bc1"]}, {p["bc7"]}, {p["cal"]}, {p["mass"]}, {p["drag"]}]],'
        if p["key"] not in seen_aliases:
            lines.append(entry)
        seen_aliases.add(p["key"])
        alias = p["alias"]
        if alias and alias not in seen_aliases and len(alias) >= 3:
            seen_aliases.add(alias)
            lines.append(
                f'    ["{alias}", [{p["mv"]}, {p["bc1"]}, {p["bc7"]}, '
                f'{p["cal"]}, {p["mass"]}, {p["drag"]}]],'
            )
    lines.append("];")
    lines.append("")

    aliases = sorted(seen_aliases, key=len, reverse=True)
    lines.append("// The projectile alias scan (longest first).")
    lines.append("private _roundNames = [")
    for a in aliases:
        lines.append(f'    "{a}",')
    lines.append("];")
    lines.append("")

    src = OUT.read_text(encoding="utf-8")
    start = src.find("private _ROUNDS = createHashMapFromArray [")
    end = src.find("// ─── Resolve")
    if start < 0 or end < 0:
        raise SystemExit("splice markers not found in the SQF")
    block = "\n".join(lines)
    src = src[:start] + block + "\n" + src[end:]
    OUT.write_text(src, encoding="utf-8")
    print(f"wrote {len(projectiles)} projectiles + {len(seen_aliases)} aliases")


if __name__ == "__main__":
    main()
