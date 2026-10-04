#!/usr/bin/env python3
"""Generate addons/environmental/functions/astronomy/fnc_starCatalogData.sqf
from BSC5.

Source: Yale Bright Star Catalogue, 5th edition (BSC5), CDS VizieR V/50,
fixed-width catalog.dat. Columns (0-indexed):
  HR 0:4, Name 4:14, DM 14:25, HD 25:31, SAO 31:37, FK5 37:41.
  J2000 RA: RAh 75:77, RAm 77:79, RAs 79:83 (F4.1).
  J2000 Dec: sign 83, DEd 84:86, DEm 86:88, DEs 88:90.
  GLON 90:96, GLAT 96:102, Vmag 102:107 (F5.2).

Stars fainter than V = 7.0 are dropped: the naked-eye limiting-magnitude
chain (fnc_calculateLimitingMagnitude) clamps at 7.0, and BSC5 is only
complete to about 7.0, so anything fainter is dead data.

Usage:
  python3 tools/validation/gen_star_catalog.py            # (re)generate
  python3 tools/validation/gen_star_catalog.py --check    # fail when stale
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "astronomy" / "sources" / "catalog.dat"
OUT = (
    ROOT
    / "addons"
    / "environmental"
    / "functions"
    / "astronomy"
    / "fnc_starCatalogData.sqf"
)

V_CUTOFF = 7.0


def parse_record(ln):
    """Return (hr, name, ra_deg, dec_deg, vmag) or None for a non-star line."""
    try:
        rah = int(ln[75:77])
        ram = int(ln[77:79])
        ras = float(ln[79:83])
        sign = ln[83]
        ded = int(ln[84:86])
        dem = int(ln[86:88])
        des = int(ln[88:90])
        vmag = float(ln[102:107])
    except (ValueError, IndexError):
        return None
    if vmag > V_CUTOFF:
        return None
    ra = rah * 15 + ram / 4 + ras / 240
    dec = (ded + dem / 60 + des / 3600) * (-1 if sign == "-" else 1)
    hr = ln[0:4].strip()
    name = ln[4:14].strip()
    if not name:
        name = "HR " + hr
    return (hr, name, ra, dec, vmag)


def parse_all():
    """Parse, sort by magnitude, and uniquify names. Returns (name, ra, dec, v)."""
    lines = SRC.read_text(encoding="latin-1").splitlines()
    stars = []
    for ln in lines:
        rec = parse_record(ln)
        if rec is not None:
            stars.append(rec)
    stars.sort(key=lambda s: s[4])
    used = set()
    out = []
    for hr, name, ra, dec, vmag in stars:
        if name in used:
            name = name + " (HR " + hr + ")"
        used.add(name)
        out.append((name, ra, dec, vmag))
    return out


def build():
    data = parse_all()
    rows = ",\n".join(
        '    ["{0}", {1:.4f}, {2:.4f}, {3:.2f}]'.format(n, ra, de, v)
        for n, ra, de, v in data
    )
    header = (
        '#include "..\\..\\script_component.hpp"\n'
        "\n"
        "/*\n"
        "Star catalogue data (issue #122 full night sky).\n"
        "\n"
        "GENERATED from data/astronomy/sources/catalog.dat (Yale Bright Star\n"
        "Catalogue, 5th edition, CDS VizieR V/50) by\n"
        "tools/validation/gen_star_catalog.py. Do not edit by hand.\n"
        "\n"
        "Each entry is [name, raDeg, decDeg, vmag]: J2000.0 right ascension and\n"
        "declination in degrees, and visual magnitude. Stars fainter than V = 7.0\n"
        "are dropped (the limiting-magnitude chain caps at 7.0 and BSC5 is only\n"
        "complete to about 7.0). Sorted by magnitude, brightest first.\n"
        "*/\n"
        "private _catalog = [\n"
    )
    footer = "];\n\n_catalog\n"
    return header + rows + "\n" + footer


def main():
    text = build()
    if "--check" in sys.argv:
        if OUT.exists() and OUT.read_text(encoding="utf-8") == text:
            print("fresh: " + str(OUT.relative_to(ROOT)))
            return 0
        print("stale: " + str(OUT.relative_to(ROOT)) + "; run the generator")
        return 1
    OUT.write_text(text, encoding="utf-8")
    n = text.count("\n")
    print(
        "wrote {} stars, {} lines -> {}".format(
            text.count('["'), n, OUT.relative_to(ROOT)
        )
    )


if __name__ == "__main__":
    sys.exit(main())
