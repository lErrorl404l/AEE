#!/usr/bin/env python3
"""Fetch every CIP datasheet and extract its dimensions.

The CIP datasheets are the held tier 1 documents. For each cartridge the
tool extracts case length (L3), twist (u), bullet diameter (G1), bore
(F), groove diameter (Z) and groove count (N), records the SHA256 of the
fetched file, and merges any missing value into the database.

The run is resumable: a datasheet already on disk is not downloaded
again, and a value already in the database is never overwritten.

Run:  python3 tools/validation/fetch_cip_datasheets.py [limit]
"""

import concurrent.futures
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
CIP = DATA / "sources" / "cip" / "cip_tdcc_all_tabs.json"
SHEETS = DATA / "sources" / "cip" / "datasheets"
EXTRACT = DATA / "sources" / "cip" / "cip_datasheet_extract.json"
DB = DATA / "cartridges.json"


def safe(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:60] or "sheet"


def fetch(url, path):
    if path.exists() and path.stat().st_size > 0:
        return path.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=60).read()
    path.write_bytes(data)
    return data


def extract(pdf_path):
    text = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, text=True
    ).stdout

    def one(pat, where=None):
        scope = text
        if where:
            m = re.search(where, text, re.I)
            scope = text[m.start() :] if m else text
        m = re.search(pat, scope, re.I)
        return m.group(1).replace(",", ".") if m else None

    return {
        "L3": one(r"L3\s*1?\)?\s*=\s*([0-9.,]+)"),
        "u": one(r"\bu\s*(?:1\)\*?)?\s*=\s*([0-9.,]+)"),
        "G1": one(r"G1\s*1?\)\s*=\s*([0-9.,]+)"),
        "F": one(r"\bF\s*1?\)\*?\s*=\s*([0-9.,]+)"),
        "Z": one(r"\bZ\s*1?\)\s*=\s*([0-9.,]+)"),
        "N": one(r"\bN\s*=\s*([0-9]+)", where=r"Grooves"),
    }


def work(item):
    name, url = item
    try:
        path = SHEETS / f"{safe(name)}.pdf"
        data = fetch(url, path)
        dims = extract(path)
        return name, {
            "url": url,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
            **dims,
        }
    except Exception as exc:  # noqa: BLE001 - report and continue
        return name, {"url": url, "error": str(exc)}


def merge(extract):
    """Add any missing CIP dimension to the matching cartridge record."""
    db = json.loads(DB.read_text(encoding="utf-8"))
    by_name = {n.lower(): r for r in db for n in r.get("names", [])}
    fields = [
        ("calibre_mm", "G1", "mm", 1.0),
        ("bore_mm", "F", "mm", 1.0),
        ("case_length_mm", "L3", "mm", 1.0),
        ("standard_twist_m", "u", "m per turn", 0.001),
    ]
    added = 0
    for name, rec in extract.items():
        cart = by_name.get(name.lower())
        if cart is None or rec.get("error"):
            continue
        values = cart["values"]
        for field, key, unit, scale in fields:
            raw = rec.get(key)
            if raw is None or field in values:
                continue
            try:
                value = round(float(raw) * scale, 4)
            except ValueError:
                continue
            values[field] = {
                "value": value,
                "unit": unit,
                "source": "cip_tdcc",
                "grade": "standard",
            }
            added += 1
        if rec.get("N") and "grooves" not in values:
            values["grooves"] = {
                "value": int(rec["N"]),
                "unit": "count",
                "source": "cip_tdcc",
                "grade": "standard",
            }
            added += 1
    DB.write_text(json.dumps(db, indent=1) + "\n", encoding="utf-8")
    return added


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    SHEETS.mkdir(parents=True, exist_ok=True)
    register = json.loads(CIP.read_text(encoding="utf-8"))
    jobs = {}
    for rows in register.values():
        for row in rows:
            if row.get("en_pdf"):
                jobs.setdefault(row["name"], row["en_pdf"])
    items = list(jobs.items())
    if limit:
        items = items[:limit]

    prev = json.loads(EXTRACT.read_text(encoding="utf-8")) if EXTRACT.exists() else {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for name, rec in pool.map(work, items):
            prev[name] = rec
    EXTRACT.write_text(json.dumps(prev, indent=1) + "\n", encoding="utf-8")

    added = merge(prev)
    ok = sum(1 for v in prev.values() if not v.get("error"))
    with_data = sum(
        1 for v in prev.values() if v.get("L3") or v.get("u") or v.get("G1")
    )
    print(
        f"datasheets fetched: {ok}/{len(prev)} ({with_data} with dimensions), "
        f"values merged: {added}"
    )


if __name__ == "__main__":
    main()
