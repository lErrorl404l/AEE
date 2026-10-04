#!/usr/bin/env python3
"""Generate addons/optics/functions/sensor/fnc_meteorShowers.sqf from IMO data.

Source: data/astronomy/sources/imo_cal2025.txt, the pdftotext -layout
extraction of the IMO 2025 Meteor Shower Calendar (document header
"IMO INFO(3.1-24)").  The eight major annual showers are read from Table 5
("Working List of Visual Meteor Showers") ONLY.  The narrative text and the
Antihelion row are ignored.

The extraction uses three glyphs the PDF renderer emits:
  U+25E6 WHITE BULLET  - the degree-dot after a coordinate
  U+2013 EN DASH       - the activity-window separator
  U+2212 MINUS SIGN    - a negative declination
The generator normalises them.  It fails loudly on any missing field; it
never defaults a value.

Row format (14 fields, also documented in the generated header):
  [code, name, startMonth, startDay, endMonth, endDay, peakMonth, peakDay,
   lambdaDeg, raDeg, decDeg, vinfKmS, r, zhr]

Usage:
  python3 tools/validation/gen_meteor_showers.py            # (re)generate
  python3 tools/validation/gen_meteor_showers.py --check    # fail when stale
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "astronomy" / "sources" / "imo_cal2025.txt"
OUT = ROOT / "addons" / "optics" / "functions" / "sensor" / "fnc_meteorShowers.sqf"

DEGREE_DOT = "\u25e6"
EN_DASH = "\u2013"
MINUS_SIGN = "\u2212"

MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

# The eight major showers, in IMO Table 5 order.  The 3-letter code anchors
# the parse and is carried into the generated row.
CODES = ["QUA", "LYR", "ETA", "PER", "ORI", "LEO", "GEM", "URS"]

# Greek glyphs the PDF uses in shower names, transliterated to ASCII.
NAME_GLYPHS = {"\u03b7": "eta"}  # eta

TABLE_START = "Table 5. Working List of Visual Meteor Showers"
TABLE_END = "Table 6 (next page)"


def _integer(text):
    text = text.strip()
    if not re.fullmatch(r"[+-]?\d+", text):
        raise ValueError(f"not an integer: {text!r}")
    return int(text)


def parse_showers(text):
    """Parse the eight major showers from Table 5.  Returns a list of rows."""
    table = text[text.index(TABLE_START) : text.index(TABLE_END)]
    found = {}
    for line in table.splitlines():
        marker = re.search(r"\((\d{3})\s+([A-Z]{3})\)", line)
        if marker is None or marker.group(2) not in CODES:
            continue
        code = marker.group(2)
        name = line[: marker.start()].strip()
        for glyph, ascii_name in NAME_GLYPHS.items():
            name = name.replace(glyph, ascii_name)

        rest = line[marker.end() :].replace(EN_DASH, "-").replace(MINUS_SIGN, "-")
        parts = rest.split(DEGREE_DOT)
        if len(parts) != 4:
            raise ValueError(f"{code}: expected 3 degree glyphs, got {len(parts) - 1}")
        p_lam, p_ra, p_dec, p_rate = parts

        activity = re.search(
            r"([A-Z][a-z]{2})\s+(\d{1,2})-([A-Z][a-z]{2})\s+(\d{1,2})", p_lam
        )
        if activity is None:
            raise ValueError(f"{code}: no activity window")
        sm, sd, em, ed = activity.groups()

        peak = re.search(r"([A-Z][a-z]{2})\s+(\d{1,2})", p_lam[activity.end() :])
        if peak is None:
            raise ValueError(f"{code}: no peak date")
        pm, pd = peak.groups()

        lam_int = re.search(r"(\d+)\s*$", p_lam[activity.end() + peak.end() :])
        if lam_int is None:
            raise ValueError(f"{code}: no solar longitude")

        lam_frac = re.search(r"^\.\s*(\d+)", p_ra)
        ra = re.search(r"(\d+)\s*$", p_ra)
        dec = re.search(r"([+-]?\d+)\s*$", p_dec)
        rate = re.search(r"^\s*(\d+)\s+([\d.]+)\s+(\d+)\s*$", p_rate)
        if ra is None or dec is None or rate is None:
            raise ValueError(f"{code}: missing radiant or rate field")

        lambda_deg = (
            float(f"{lam_int.group(1)}.{lam_frac.group(1)}")
            if lam_frac
            else int(lam_int.group(1))
        )
        row = (
            code,
            name,
            MONTHS[sm],
            int(sd),
            MONTHS[em],
            int(ed),
            MONTHS[pm],
            int(pd),
            lambda_deg,
            int(ra.group(1)),
            _integer(dec.group(1)),
            int(rate.group(1)),
            float(rate.group(2)),
            int(rate.group(3)),
        )
        found[code] = row

    missing = [c for c in CODES if c not in found]
    if missing:
        raise ValueError(f"missing shower(s): {', '.join(missing)}")
    return [found[c] for c in CODES]


def _literal(value):
    """SQF number literal that preserves the parsed form (140.0 not 140)."""
    if isinstance(value, float):
        return repr(value)
    return str(value)


def build():
    rows = parse_showers(SRC.read_text(encoding="utf-8"))
    lines = []
    for row in rows:
        fields = ", ".join(
            [f'"{row[0]}"', f'"{row[1]}"'] + [_literal(v) for v in row[2:]]
        )
        lines.append("    [" + fields + "]")
    body = ",\n".join(lines)

    header = (
        '#include "..\\..\\script_component.hpp"\n'
        "\n"
        "/*\n"
        "Meteor shower data (issue #122 dynamic night sky).\n"
        "\n"
        "GENERATED from data/astronomy/sources/imo_cal2025.txt (IMO 2025\n"
        "Meteor Shower Calendar, IMO INFO(3.1-24), Table 5 'Working List of\n"
        "Visual Meteor Showers') by tools/validation/gen_meteor_showers.py.\n"
        "Do not edit by hand.\n"
        "\n"
        "Each entry is [code, name, startMonth, startDay, endMonth, endDay,\n"
        "peakMonth, peakDay, lambdaDeg, raDeg, decDeg, vinfKmS, r, zhr].\n"
        "Dates give the activity window and peak (2025).  lambdaDeg is the\n"
        "solar longitude at maximum (equinox 2000.0).  raDeg and decDeg are\n"
        "the radiant in degrees.  vinfKmS is the pre-atmospheric velocity.\n"
        "r is the population index.  zhr is the Zenithal Hourly Rate.\n"
        "*/\n"
        "private _showers = [\n"
    )
    footer = "];\n\n_showers\n"
    return header + body + "\n" + footer


def main():
    text = build()
    if "--check" in sys.argv:
        if OUT.exists() and OUT.read_text(encoding="utf-8") == text:
            print("fresh: " + str(OUT.relative_to(ROOT)))
            return 0
        print("stale: " + str(OUT.relative_to(ROOT)) + "; run the generator")
        return 1
    OUT.write_text(text, encoding="utf-8")
    print(
        "wrote {} showers, {} lines -> {}".format(
            text.count('["'), text.count("\n"), OUT.relative_to(ROOT)
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
