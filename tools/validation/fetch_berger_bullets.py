#!/usr/bin/env python3
"""Fetch the Berger catalog and parse its bullet table.

Berger publishes sectional density, G1 and G7 BC, G7 form factor and a
minimum twist for every bullet. That is manufacturer data, so it enters
at grade claimed. The minimum twist is Berger's own stability figure.

Run:  python3 tools/validation/fetch_berger_bullets.py
"""

import hashlib
import json
import re
import subprocess
import urllib.request
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
URL = "https://bergerbullets.com/wp-content/uploads/2026/03/English-Berger-Catalog-2026.pdf"
PDF = DATA / "sources" / "berger_catalog.pdf"
OUT = DATA / "sources" / "berger_bullets.json"

DIAMETER = {
    "17": 0.172,
    "20": 0.204,
    "22": 0.224,
    "6": 0.243,
    "25": 0.257,
    "6.5": 0.264,
    "270": 0.277,
    "7": 0.284,
    "30": 0.308,
    "338": 0.338,
    "375": 0.375,
}

ROW = re.compile(
    r"^\s*(.+?)\s{2,}(\d{5})\s+([0-9.]+|NA)\s+([0-9.]+|NA)\s+([0-9.]+|NA)\s+"
    r"([0-9.]+|NA)\s+1:([0-9.]+)\"",
    re.M,
)


def fetch():
    if PDF.exists() and PDF.stat().st_size > 0:
        return PDF.read_bytes()
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=120).read()
    PDF.write_bytes(data)
    return data


def parse(text):
    out = []
    for m in ROW.finditer(text):
        desc, part, sd, g1, g7, ff, twist = m.groups()
        cal = re.match(r"^(\d+(?:\.\d+)?)\s*(?:Cal|mm)\b", desc, re.I)
        mass = re.search(r"(\d+(?:\.\d+)?)\s*(?:Grain|gr)\b", desc, re.I)
        if not (cal and mass):
            continue
        out.append(
            {
                "description": re.sub(r"\s+", " ", desc).strip(),
                "part": part,
                "calibre_label": cal.group(1),
                "diameter_in": DIAMETER.get(cal.group(1)),
                "mass_gr": float(mass.group(1)),
                "sectional_density": None if sd == "NA" else float(sd),
                "bc_g1": None if g1 == "NA" else float(g1),
                "bc_g7": None if g7 == "NA" else float(g7),
                "g7_form_factor": None if ff == "NA" else float(ff),
                "min_twist_in": float(twist),
            }
        )
    return out


def main():
    data = fetch()
    text = subprocess.run(
        ["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True
    ).stdout
    rows = parse(text)
    payload = {
        "url": URL,
        "retrieved": "2026-09-22",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bullets": rows,
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"berger bullets parsed: {len(rows)}")


if __name__ == "__main__":
    main()
