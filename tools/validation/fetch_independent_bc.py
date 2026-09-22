#!/usr/bin/env python3
"""Fetch and parse the independent ballistic coefficient measurements.

Two independent sources:

1. The Aberdeen Proving Ground and Litz G7 BC list, a public compilation
   of measured G7 values for military and commercial bullets.
2. The US Air Force Academy DFRL report "Comparing Advertised Ballistic
   Coefficients with Independent Measurements" (2012), which tabulates
   the manufacturer G1 claim against the Litz measured G1 and G7 for the
   Barnes, Hornady, Sierra and Nosler lines.

Both are measurements, so they are tier 3 and can corroborate a
manufacturer claim.

Run:  python3 tools/validation/fetch_independent_bc.py
"""

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
XLS = SRC / "apg_litz_g7.xls"
CSV = SRC / "apg_litz_g7.csv"
PDF = SRC / "litz_dfrl.pdf"
URL_G7 = "https://frfrogspad.com/20120418-g7bclist.xls"
URL_DFRL = (
    "https://sentineltactical.com/wp-content/uploads/2019/12/Litz-BC-of-bullets.pdf"
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_g7():
    if not CSV.exists():
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "csv",
                str(XLS),
                "--outdir",
                str(SRC),
            ],
            check=True,
            capture_output=True,
        )
    rows = []
    with CSV.open(encoding="utf-8", errors="replace") as fh:
        for rec in csv.reader(fh):
            if len(rec) < 6 or rec[0].strip() not in (
                "APG G7",
                "Litz",
                "SL",
                "Berger",
                "Lapua",
                "Hornady",
                "Sierra",
                "Nosler",
                "Barnes",
                "APG",
                "G7",
            ):
                # Accept any row whose 2nd to 6th cells parse as data.
                pass
            if len(rec) < 6:
                continue
            maker, dia, weight, kind, sd, bc = [c.strip() for c in rec[:6]]
            try:
                row = {
                    "manufacturer": maker,
                    "diameter_in": float(dia),
                    "mass_gr": float(weight),
                    "designation": kind,
                    "sectional_density": float(sd),
                    "bc_g7": float(bc),
                }
            except ValueError:
                continue
            if 0.1 <= row["diameter_in"] <= 0.8 and 0.01 <= row["bc_g7"] <= 2.0:
                rows.append(row)
    return rows


ROW = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9 .\-/]*?)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+"
    r"([0-9.]+|NT)\s+([0-9.]+|NT)\s+([0-9.]+|NT)\s+(-?[0-9.]+)\s*$",
    re.M,
)


def parse_dfrl():
    text = subprocess.run(
        ["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True
    ).stdout
    rows = []
    brand = ""
    caption = re.compile(r"Table \d+:.*?(Barnes|Hornady|Sierra|Nosler)", re.S)
    for line in text.splitlines():
        cap = caption.search(line)
        if cap:
            brand = cap.group(1)
            continue
        m = ROW.match(line)
        if not m:
            continue
        style, dia, mass, sd, claim, litz_g1, litz_g7, over = m.groups()

        def num(x):
            return None if x == "NT" else float(x)

        row = {
            "brand": brand,
            "style": style.strip(),
            "diameter_in": float(dia),
            "mass_gr": float(mass),
            "sectional_density": float(sd),
            "claimed_g1": num(claim),
            "litz_g1": num(litz_g1),
            "litz_g7": num(litz_g7),
            "overestimate_pct": float(over),
        }
        if 0.1 <= row["diameter_in"] <= 0.8:
            rows.append(row)
    return rows


def main():
    if not XLS.exists() or not PDF.exists():
        raise SystemExit("missing source documents in data/ballistics/sources")
    g7 = parse_g7()
    (SRC / "apg_litz_g7.json").write_text(
        json.dumps(
            {
                "url": URL_G7,
                "retrieved": "2026-09-22",
                "sha256": sha(XLS),
                "bullets": g7,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    dfrl = parse_dfrl()
    (SRC / "litz_dfrl.json").write_text(
        json.dumps(
            {
                "url": URL_DFRL,
                "retrieved": "2026-09-22",
                "sha256": sha(PDF),
                "bullets": dfrl,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"apg/litz G7 rows: {len(g7)}, dfrl measured rows: {len(dfrl)}")


if __name__ == "__main__":
    main()
