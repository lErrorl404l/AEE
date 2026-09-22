#!/usr/bin/env python3
"""Fetch and parse manufacturer bullet BC tables.

Hornady publishes G1 and G7 BCs for its ELD Match, ELD-X, A-Tip and
ELD-VT bullets at three Mach numbers. The values are manufacturer
claims, so they enter at grade claimed and stay flagged until an
independent source agrees.

The parsed table is written to the source directory with the SHA256 of
the fetched page.

Run:  python3 tools/validation/fetch_bullet_bc.py
"""

import hashlib
import html
import json
import re
import urllib.request
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
OUT = DATA / "sources" / "hornady_bc.json"
URL = "https://www.hornady.com/bc?age=confirmed"

# Published bullet diameter per calibre label, in mm.
DIAMETER = {
    "22": 5.69,
    "25": 6.53,
    "6": 6.17,
    "6.5": 6.71,
    "7": 7.21,
    "270": 7.04,
    "30": 7.82,
    "338": 8.59,
    "375": 9.53,
    "416": 10.57,
}
GRAIN_TO_G = 0.06479891


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=60).read()


def parse(page):
    text = page.decode("utf-8", "replace")
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S):
        cells = [
            html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)
        ]
        if len(cells) < 2:
            continue
        name = cells[0]
        if not re.search(r"ELD Match|ELD-X|A-Tip|ELD-VT", name, re.I):
            continue
        mach = re.search(r"([0-9.]+)\s*a?G1\s*([0-9.]+)\s*G7", cells[1])
        if not mach:
            continue
        cal = re.search(r"^\.?([0-9]+(?:\.[0-9]+)?)\s*(?:mm|Cal)", name, re.I)
        mass = re.search(r"([0-9]+)\s*gr", name, re.I)
        twist = re.search(r"1 in ([0-9.]+)", name)
        family = re.search(r"(ELD Match|ELD-X|A-Tip|ELD-VT)", name, re.I)
        if not (cal and mass and family):
            continue
        out.append(
            {
                "published_name": re.sub(r"\s+", " ", name),
                "calibre_label": cal.group(1),
                "diameter_mm": DIAMETER.get(cal.group(1)),
                "mass_gr": float(mass.group(1)),
                "mass_g": round(float(mass.group(1)) * GRAIN_TO_G, 4),
                "family": family.group(1),
                "twist_in": float(twist.group(1)) if twist else None,
                "bc_g1": float(mach.group(1)),
                "bc_g7": float(mach.group(2)),
            }
        )
    return out


def main():
    page = fetch()
    rows = parse(page)
    payload = {
        "url": URL,
        "retrieved": "2026-09-22",
        "sha256": hashlib.sha256(page).hexdigest(),
        "bullets": rows,
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"hornady bullets parsed: {len(rows)}")


if __name__ == "__main__":
    main()
