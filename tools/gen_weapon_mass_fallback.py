#!/usr/bin/env python3
"""Generate the weapon-mass family fallback from the real weapon corpus.

``fnc_getWeaponMass`` returns the maker's published mass when the weapon
catalogue identifies the classname.  When it does not, the kernel falls back
on the classname's weapon family, and that fallback used to be a hand-written
ladder of invented kilogram figures.

This generator replaces it with the MEDIAN of the measured masses the corpus
already holds for each family, so no number in the fallback is invented: each
one is the middle of a set of published weapon masses.

The corpus is ``data/ballistics/weapons.json``.  A weapon joins a family by
its chambering where the chambering defines the family (a pistol cartridge
makes a pistol, a rifle cartridge a carbine, a magnum or .50 a sniper rifle),
and by its own model name where it does not (belt-fed machine guns and
submachine guns are named, not implied by their cartridge, because both share
cartridges with other families).

Families with no corpus entry are NOT emitted: the kernel must fall back on
the all-weapon median rather than an invented figure.

Run:
    python3 tools/gen_weapon_mass_fallback.py
    python3 tools/gen_weapon_mass_fallback.py --check
Exit 0 when fresh, 1 when stale or missing under --check.
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
CORPUS = REPO / "data/ballistics/weapons.json"
OUT = REPO / "addons/clothing/functions/clothing/fnc_weaponMassFallback.sqf"

# Chamberings that define a family on their own.
BY_CARTRIDGE = {
    "pistol": [
        "9x19", "45_auto", "40_smith_wesson", "10_mm_auto", "357_sig",
        "380_automatic", "45_gap", "7_62_x_25_tokarev", "5_7_x_28",
    ],
    "revolver": ["357_magnum", "38_special", "44_remington_magnum"],
    "carbine": [
        "556x45_nato", "762x39", "545x39", "58x42", "300_aac_blackout",
    ],
    "dmr": ["762x51_nato", "308_win", "65_creedmoor", "7_62_x_54_r"],
    "sniper": [
        "338_lapua_mag", "300_winchester_magnum", "50_bmg", "8_x_50_r",
    ],
    "shotgun": ["12_gauge"],
}

# Families a cartridge cannot imply, matched on the weapon's own model name.
BY_NAME = {
    "machinegun": re.compile(
        r"\b(m249|m240|pkm|pkp|mg3|mg42|mg5|minimi|negev|m60|rpd|rpk|saw"
        r"|mag58|mk ?48|browning m2|dshk|kord|nsv)\b"
    ),
    "smg": re.compile(
        r"\b(mp5|mp7|mp9|p90|uzi|scorpion|ump|vector|sten|thompson"
        r"|pp-19|bizon|apc9|mpx)\b"
    ),
}

# The classname keywords the kernel tests, most specific first, each mapped
# to the corpus family that supplies its mass.
CLASS_KEYWORDS = [
    ("srifle", "sniper"),
    ("sniper", "sniper"),
    ("dmr", "dmr"),
    ("lmg", "machinegun"),
    ("mmg", "machinegun"),
    ("machinegun", "machinegun"),
    ("smg", "smg"),
    ("pdw", "smg"),
    ("revolver", "revolver"),
    ("hgun", "pistol"),
    ("pistol", "pistol"),
    ("shotgun", "shotgun"),
    ("carbine", "carbine"),
    ("arifle", "carbine"),
]


def load_masses() -> list:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    out = []
    for w in corpus:
        values = w.get("values") or {}
        entry = values.get("mass_kg")
        if not entry:
            continue
        mass = entry.get("value")
        if not isinstance(mass, (int, float)) or mass <= 0:
            continue
        out.append((w, float(mass)))
    return out


def families(masses: list) -> dict:
    """Median measured mass per family, with the sample it came from."""
    buckets: dict[str, list] = {}
    for weapon, mass in masses:
        name = " ".join(
            [str(weapon.get("weapon_id") or "")] + list(weapon.get("names") or [])
        ).lower()
        family = None
        for fam, pattern in BY_NAME.items():
            if pattern.search(name):
                family = fam
                break
        if family is None:
            cartridge = weapon.get("cartridge_id") or ""
            for fam, ids in BY_CARTRIDGE.items():
                if cartridge in ids:
                    family = fam
                    break
        if family is None:
            continue
        buckets.setdefault(family, []).append(mass)
    return {f: (len(v), statistics.median(v)) for f, v in sorted(buckets.items())}


def render(fams: dict, overall_n: int, overall: float) -> str:
    rows = []
    for keyword, family in CLASS_KEYWORDS:
        if family not in fams:
            continue
        count, median = fams[family]
        rows.append(
            (
                f'        ["{keyword}", {median:.3g}]',
                f"// {family}: median of {count} published masses",
            )
        )
    # The comma separates the ROWS, so it must sit before the comment:
    # after it the rest of the line is commented out and the array breaks.
    table = "\n".join(
        f"{code}{',' if i < len(rows) - 1 else ' '}   {comment}"
        for i, (code, comment) in enumerate(rows)
    )
    register = "\n".join(
        f"  {f:<12s} {n:4d} weapons, median {m:.3g} kg"
        for f, (n, m) in fams.items()
    )
    return f'''#include "..\\..\\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_weapon_mass_fallback.py

Weapon-mass fallback by classname family.

fnc_getWeaponMass returns the maker's published mass whenever the weapon
catalogue identifies the classname.  This table is only reached when it does
not, and every figure in it is the MEDIAN of the measured masses the corpus
(data/ballistics/weapons.json) already holds for that family, so the fallback
invents nothing.

A weapon joins a family by its chambering where the chambering defines the
family, and by its model name where it does not (a belt-fed machine gun and a
submachine gun share cartridges with other families).

Per-family sample, from {overall_n} corpus weapons carrying a published mass:
{register}

A classname matching no family takes the all-weapon median, {overall:.3g} kg.

Returns: ARRAY of [keyword, massKg] rows, most specific family first, and the
         all-weapon median as the last element.
*/

[
    [
{table}
    ],
    {overall:.3g}
]
'''


def build() -> str:
    masses = load_masses()
    if not masses:
        raise SystemExit("weapon corpus holds no published mass")
    fams = families(masses)
    overall = statistics.median([m for _, m in masses])
    return render(fams, len(masses), overall)


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    text = build()
    if "--check" in args:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print("weapon mass fallback: stale, run python3 tools/gen_weapon_mass_fallback.py")
            return 1
        print("weapon mass fallback: fresh")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"weapon mass fallback: wrote {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
