#!/usr/bin/env python3
"""Fetch the CIP TDCC register (all twelve tabs).

The register is the first research source: it lists every CIP cartridge
with its pressure and the URL of its datasheet. This tool scrapes the
public CIP pages and writes the register to the source directory.

Run:  python3 tools/validation/fetch_cip_register.py
"""

import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
OUT = DATA / "sources" / "cip" / "cip_tdcc_all_tabs.json"
BASE = "https://bobp.cip-bobp.org/en/tdcc_public"
TABS = {
    1: "Tab I rimless",
    2: "Tab II rimmed",
    3: "Tab III belted",
    4: "Tab IV pistol/revolver",
    5: "Tab V rimfire (crusher)",
    12: "Tab V rimfire (transducer)",
    6: "Tab VI industrial",
    7: "Tab VII shot",
    8: "Tab VIII alarm",
    9: "Tab IX dust shot",
    10: "Tab X other weapons",
    11: "Tab XI caseless",
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")


def scrape(cartridge_type):
    """One tab. The site repeats the last page past the end, so the loop
    stops when a page adds no new row."""
    seen = {}
    page = 1
    while page <= 40:
        url = f"{BASE}?cartridge_type_id={cartridge_type}&page={page}"
        try:
            html = fetch(url)
        except Exception:  # noqa: BLE001 - a network page may fail
            break
        rows = [
            r
            for r in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S)
            if "uploads/tdcc/" in r
        ]
        added = 0
        for row in rows:
            cells = [
                re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c))
                .replace("&nbsp;", " ")
                .strip()
                for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
            ]
            links = re.findall(r'href="(/uploads/tdcc/[^"]+)"[^>]*>\s*EN', row)
            if not cells or cells[0] in seen:
                continue

            def number(index):
                try:
                    return float(cells[index].replace(",", "."))
                except (ValueError, IndexError):
                    return None

            seen[cells[0]] = {
                "name": cells[0],
                "date": cells[1],
                "rev": cells[2],
                "country": cells[3],
                "m": number(6),
                "ptmax_bar": number(7),
                "pk_bar": number(8),
                "pe_bar": number(9),
                "ee_bar": number(10),
                "en_pdf": ("https://bobp.cip-bobp.org" + links[0]) if links else "",
            }
            added += 1
        if added == 0:
            break
        page += 1
    return list(seen.values())


def main():
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(scrape, TABS))
    register = {TABS[key]: rows for key, rows in zip(TABS, results)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(register, indent=1) + "\n", encoding="utf-8")
    total = sum(len(rows) for rows in register.values())
    print(f"CIP register: {total} cartridges across {len(register)} tabs")


if __name__ == "__main__":
    main()
