#!/usr/bin/env python3
"""Coverage audit: common military weapons and cartridges.

The runtime resolves a weapon in three layers:

  1. the weapon's own verified twist
  2. the chambering standard (grade standard, held tier 1 source)
  3. the Miller rule, which states what the bullet needs

A weapon is fully covered when layer 1 or layer 2 holds. This tool checks
a curated list of common service weapons and cartridges around the world
and reports which layer covers each, so a gap is visible before a player
finds it.

Run:  python3 tools/validation/audit_coverage.py
"""

import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"

# label, name fragments to match a cartridge record
COMMON_CARTRIDGES = [
    ("5.56x45mm NATO", ["5.56x45", "5,56 x 45", "223 rem"]),
    ("7.62x51mm NATO", ["7.62x51", "7,62 x 51", "308 win"]),
    ("7.62x39mm", ["7.62x39", "7,62 x 39", "7.62 x 39"]),
    ("5.45x39mm", ["5.45x39", "5,45 x 39"]),
    ("7.62x54mmR", ["7.62x54", "7,62 x 54"]),
    ("9x19mm Parabellum", ["9x19", "9 mm luger", "9mm luger"]),
    ("9x18mm Makarov", ["9x18", "9 mm makarov"]),
    ("7.62x25mm Tokarev", ["7.62x25", "7,62 x 25"]),
    ("7.63x25mm Mauser", ["7.63x25", "7,63 x 25", "7.63 mauser", "7,63 mauser"]),
    (".45 ACP", ["45 acp", "45 auto", "11.43"]),
    (".40 S&W", ["40 s&w", "40 smith"]),
    (".380 ACP", ["380 acp", "380 auto", "9x17"]),
    (".38 Special", ["38 special", "38 spl"]),
    (".357 Magnum", ["357 magnum", "357 mag"]),
    (".44 Magnum", ["44 magnum", "44 rem"]),
    (".50 AE", ["50 ae", "50 action"]),
    ("12.7x99mm NATO", ["12.7x99", "50 bmg", "12,7 x 99"]),
    ("12.7x108mm", ["12.7x108", "12,7 x 108"]),
    ("14.5x114mm", ["14.5x114"]),
    ("5.7x28mm", ["5.7x28"]),
    ("4.6x30mm", ["4.6x30"]),
    ("9x39mm", ["9x39", "9 x 39"]),
    ("5.8x42mm", ["5.8x42"]),
    (".30 Carbine", ["30 carbine", "7.62x33"]),
    (".30-06 Springfield", ["30-06", "30 06", "7.62x63"]),
    (".303 British", ["303 british", "303 enfield", "7.7x56"]),
    ("7.92x57mm Mauser", ["7.92x57", "8x57", "8 x 57"]),
    ("7.5x55mm Swiss", ["7.5x55", "7,5 x 55"]),
    ("7.5x54mm French", ["7.5x54", "7,5 x 54"]),
    ("6.5x55mm", ["6.5x55", "6,5 x 55"]),
    ("6.5x50mmSR Arisaka", ["6.5x50", "6,5 x 50"]),
    ("7.7x58mm Arisaka", ["7.7x58", "7,7 x 58"]),
    ("7x57mm Mauser", ["7x57", "7 x 57"]),
    ("8x50mmR Lebel", ["8x50", "8 x 50"]),
    ("6.5x52mm Carcano", ["6.5x52", "6,5 x 52"]),
    ("20 Gauge", ["20 gauge", "20/70"]),
    (".410 Bore", ["410 bore", "410/70", "410/76"]),
    ("7mm PRC", ["7mm prc", "7 mm prc"]),
    ("280 British", ["280 british"]),
    (".300 AAC Blackout", ["300 aac", "300 blackout", "7.62x35"]),
    ("6.5mm Creedmoor", ["6.5 creedmoor", "6,5 creedmoor"]),
    (".338 Lapua Magnum", ["338 lapua"]),
    (".338 Norma Magnum", ["338 norma"]),
    (".50 Beowulf", ["50 beowulf"]),
    (".458 SOCOM", ["458 socom"]),
    (".300 Win Mag", ["300 win"]),
    (".22 Long Rifle", ["22 long rifle", "22 lr"]),
    ("5.56x45mm blank/tracer", ["5.56x45"]),
]

# label, chambering fragment, weapon name fragments
COMMON_WEAPONS = [
    ("AK-47/AKM", "7.62x39", ["ak47", "akm", "ak-47"]),
    ("AK-74", "5.45x39", ["ak74", "ak-74"]),
    ("AK-12/AK-15", "5.45x39", ["ak12", "ak12k"]),
    ("AK-203", "7.62x39", ["ak203"]),
    ("RPK-74", "5.45x39", ["rpk74"]),
    ("PK/PKM", "7.62x54", ["pkm", "pk "]),
    ("SVD", "7.62x54", ["svd", "dragunov"]),
    ("SKS", "7.62x39", ["sks"]),
    ("Mosin-Nagant", "7.62x54", ["mosin", "m91"]),
    ("VSS Vintorez", "9x39", ["vssvintorez", "vintorez"]),
    ("AS Val", "9x39", ["asval"]),
    ("PP-19 Bizon", "9x19", ["bizon"]),
    ("M16A4", "5.56x45", ["m16a4"]),
    ("M4A1", "5.56x45", ["m4a1"]),
    ("M14/M21", "7.62x51", ["m14", "m21"]),
    ("M24 SWS", "7.62x51", ["m24"]),
    ("M40A5", "7.62x51", ["m40a5"]),
    ("M110 SASS", "7.62x51", ["m110"]),
    ("Mk 12 SPR", "5.56x45", ["mk12", "mk11"]),
    ("Mk 18 CQBR", "5.56x45", ["mk18"]),
    ("M249 SAW", "5.56x45", ["m249", "minimi"]),
    ("M240B", "7.62x51", ["m240"]),
    ("M60", "7.62x51", ["m60"]),
    ("M2 Browning", "12.7x99", ["m2 browning", "50cal", "m2hb"]),
    ("M107/M82", "12.7x99", ["m107", "m82", "barrett"]),
    ("Mk 19 (40mm)", "40x53", ["mk19"]),
    ("M203 (40mm)", "40x46", ["m203"]),
    ("G3", "7.62x51", ["g3 "]),
    ("G36", "5.56x45", ["g36"]),
    ("MG3", "7.62x51", ["mg3"]),
    ("MG4", "5.56x45", ["mg4"]),
    ("HK416", "5.56x45", ["hk416"]),
    ("HK417", "7.62x51", ["hk417"]),
    ("MP5", "9x19", ["mp5"]),
    ("MP7", "4.6x30", ["mp7"]),
    ("UMP45", "45 acp", ["ump45"]),
    ("FN FAL", "7.62x51", ["fal", "l1a1"]),
    ("L85/SA80", "5.56x45", ["sa80", "l85"]),
    ("L129A1", "7.62x51", ["l129a1"]),
    ("Lee-Enfield", "303 british", ["lee enfield", "smle"]),
    ("Bren", "303 british", ["bren"]),
    ("Sten", "9x19", ["sten"]),
    ("Sterling", "9x19", ["sterling"]),
    ("FAMAS", "5.56x45", ["famas"]),
    ("FR-F2", "7.62x51", ["frf2", "fr-f2"]),
    ("Beretta AR70/90", "5.56x45", ["ar70", "ar90"]),
    ("SIG SG550", "5.56x45", ["sg550", "sg551"]),
    ("Stgw 90", "5.56x45", ["stgw90", "sig550"]),
    ("SSG 3000", "7.62x51", ["ssg3000"]),
    ("Steyr AUG", "5.56x45", ["aug"]),
    ("Steyr SSG 69", "7.62x51", ["ssg69"]),
    ("Galil", "5.56x45", ["galil"]),
    ("Tavor TAR-21", "5.56x45", ["tavor", "tar21"]),
    ("Negev", "5.56x45", ["negev"]),
    ("Uzi", "9x19", ["uzi"]),
    ("QBZ-95", "5.8x42", ["qbz95", "qbz-95"]),
    ("QBU-88", "5.8x42", ["qbu88", "qbu-88"]),
    ("Daewoo K2", "5.56x45", ["k2a", "k2 "]),
    ("Howa Type 89", "5.56x45", ["type89"]),
    ("INSAS", "5.56x45", ["insas"]),
    ("vz.58", "7.62x39", ["vz58", "vz.58"]),
    ("CZ 805 BREN", "5.56x45", ["bren2", "805"]),
    ("Skorpion vz.61", "7.65x17", ["skorpion", "vz61"]),
    ("FN P90", "5.7x28", ["p90"]),
    ("MAC-10", "45 acp", ["mac10", "mac-10"]),
    ("Thompson", "45 acp", ["thompson"]),
    ("MP40", "9x19", ["mp40"]),
    ("PPSh-41", "7.62x25", ["ppsh"]),
    ("PPS-43", "7.62x25", ["pps43"]),
    ("M1 Garand", "30-06", ["m1garand", "garand"]),
    ("M1 Carbine", "30 carbine", ["m1carbine"]),
    ("M3 Grease Gun", "45 acp", ["m3greasegun"]),
    ("Glock 17", "9x19", ["glock"]),
    ("Beretta M9/92F", "9x19", ["m9", "92f", "92fs"]),
    ("SIG P320/M17", "9x19", ["p320", "m17"]),
    ("SIG P226", "9x19", ["p226"]),
    ("CZ 75", "9x19", ["cz75"]),
    ("Browning Hi-Power", "9x19", ["hipower", "hi-power"]),
    ("M1911A1", "45 acp", ["1911a1", "m1911"]),
    ("Remington 870", "12 gauge", ["870", "remington870"]),
    ("Mossberg 500", "12 gauge", ["mossberg", "500"]),
]


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def find_in(index, fragments):
    """Exact match first, then the shortest key that contains the needle."""
    for fragment in fragments:
        needle = normalise(fragment)
        if not needle:
            continue
        if needle in index:
            return index[needle]
        hits = [key for key in index if needle in key]
        if hits:
            return index[min(hits, key=len)]
    return None


def main():
    cartridges = json.loads((DATA / "cartridges.json").read_text(encoding="utf-8"))
    weapons = json.loads((DATA / "weapons.json").read_text(encoding="utf-8"))

    cart_index = {}
    for record in cartridges:
        entry = record["values"].get("standard_twist_m")
        for name in record.get("names", []) + [record["cartridge_id"]]:
            cart_index[normalise(name)] = (record, entry)
    weapon_index = {}
    for record in weapons:
        for alias in [record["weapon_id"]] + record.get("aliases", []):
            weapon_index[normalise(alias)] = record

    lines = [
        "# Coverage audit",
        "",
        "Layer 1 is the weapon's own twist. Layer 2 is the chambering",
        "standard. A weapon is covered when either holds.",
        "",
        "## Cartridges",
        "",
    ]
    missing_cart = []
    for label, fragments in COMMON_CARTRIDGES:
        hit = find_in(cart_index, fragments)
        if hit and hit[1]:
            continue
        missing_cart.append(label)
        lines.append(f"- MISSING standard twist: {label}")
    lines += ["", "## Weapons", ""]
    missing_weapon = []
    for label, chambering, fragments in COMMON_WEAPONS:
        entry = find_in(weapon_index, fragments)
        chamber_entry = find_in(cart_index, [chambering])
        chamber = chamber_entry[1] if chamber_entry else None
        covered = (
            "layer 1"
            if entry and "twist_m" in entry["values"]
            else ("layer 2" if chamber else "NONE")
        )
        if covered == "NONE":
            missing_weapon.append(label)
            lines.append(f"- NOT COVERED: {label} (chambering {chambering})")

    lines += [
        "",
        f"Cartridges without a standard twist: {len(missing_cart)} / "
        f"{len(COMMON_CARTRIDGES)}",
        f"Weapons not covered: {len(missing_weapon)} / {len(COMMON_WEAPONS)}",
    ]
    report = DATA / "COVERAGE_AUDIT.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"cartridges without a standard twist: {len(missing_cart)}")
    for label in missing_cart:
        print("   ", label)
    print(f"weapons not covered: {len(missing_weapon)}")
    for label in missing_weapon:
        print("   ", label)
    print(f"wrote {report}")


if __name__ == "__main__":
    main()
