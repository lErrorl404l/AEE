#!/usr/bin/env python3
"""Fetch the Applied Ballistics bullet library index.

Applied Ballistics measures bullet drag with Doppler radar. The published
library index lists every bullet it models, with manufacturer,
designation, calibre and weight. It is an independent source for bullet
identity and weight, which corroborates a manufacturer claim.

The direct download is blocked, so the archived copy is used.

Run:  python3 tools/validation/fetch_ab_library.py
"""

import hashlib
import json
import re
import subprocess
import urllib.request
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
URL = "https://web.archive.org/web/2020id_/http://www.appliedballisticsllc.com/Downloads/ABLibrary.pdf"
PDF = DATA / "sources" / "ab_bullet_library.pdf"
OUT = DATA / "sources" / "ab_bullet_library.json"


def fetch():
    if PDF.exists() and PDF.stat().st_size > 0:
        return PDF.read_bytes()
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=120).read()
    PDF.write_bytes(data)
    return data


def main():
    data = fetch()
    text = subprocess.run(
        ["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True
    ).stdout
    rows = []
    # The library index lists centerfire bullets first, then rimfire and
    # personalised drag models. Only the centerfire index is parsed.
    text = text.split("Personalized Drag Models")[0]
    for line in text.splitlines():
        if not re.search(r"0\.\d{3}\s+\d", line):
            continue
        parts = [p for p in re.split(r"\s{2,}", line.strip()) if p]
        if len(parts) == 5:
            maker, design, cal, weight = parts[1:5]
        elif len(parts) == 4:
            maker, design, cal, weight = parts
        else:
            continue
        if not re.fullmatch(r"0\.\d{3}", cal):
            continue
        try:
            mass = float(weight)
        except ValueError:
            continue
        rows.append(
            {
                "manufacturer": maker.strip(),
                "designation": design.strip(),
                "diameter_in": float(cal),
                "mass_gr": mass,
            }
        )
    payload = {
        "url": URL,
        "retrieved": "2026-09-22",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bullets": rows,
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"applied ballistics bullets parsed: {len(rows)}")


if __name__ == "__main__":
    main()
