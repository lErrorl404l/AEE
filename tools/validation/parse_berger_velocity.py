#!/usr/bin/env python3
"""Extract per-bullet muzzle velocity from the Berger load-data sheets.

Berger publishes one PDF per cartridge and bullet weight at
https://bergerbullets.com/pdf/<sheet>.pdf. Each sheet prints the test barrel
length and, per powder, an approximate start velocity and an approximate
maximum velocity. The row kept here is the fastest maximum-charge velocity on
the sheet, so the anchor is a published number for that bullet in that barrel.

The sheets are captured bytes held outside the repository. This script reads
them from the local source cache and writes only the citation record.

  python3 tools/validation/parse_berger_velocity.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from source_cache import cache_root, capture_path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
INDEX_URL = "https://bergerbullets.com/reloading-data/"
BASE = "https://bergerbullets.com/pdf/"
OUT = DATA / "sources" / "berger_velocity.json"

# Bullet descriptor printed on the sheet -> words the Berger projectile name uses.
MODEL = {
    "elite hunter": "Elite Hunter",
    "classic hunter": "Classic Hybrid Hunter",
}

# The 338-family sheets are scans with no text layer, so they are transcribed
# from the page image. Each entry is one sheet: cartridge, barrel in inches,
# the two bullets the sheet prints, and the fastest maximum-velocity row
# (powder, start charge, start velocity, max charge, max velocity). Both
# bullets of a sheet share the sheet's single load table.
SCANNED = [
    (
        "338 Lapua Magnum",
        26,
        ("250", "Elite Hunter"),
        ("250", "Hybrid OTM Tactical"),
        "RETUMBO",
        "86.5",
        "2669",
        "94.0",
        "2907",
    ),
    (
        "338 Lapua Magnum",
        26,
        ("300", "Elite Hunter"),
        ("300", "Hybrid OTM Tactical"),
        "VIHT N570",
        "85.5",
        "2554",
        "90.0",
        "2704",
    ),
    (
        "338 Remington Ultra Magnum",
        26,
        ("250", "Elite Hunter"),
        ("250", "Hybrid OTM Tactical"),
        "RAMSHOT MAGNUM",
        "86.0",
        "2666",
        "90.5",
        "2815",
    ),
    (
        "338 Remington Ultra Magnum",
        26,
        ("300", "Elite Hunter"),
        ("300", "Hybrid OTM Tactical"),
        "RETUMBO",
        "83.0",
        "2489",
        "87.3",
        "2611",
    ),
    (
        "338 Winchester Magnum",
        26,
        ("250", "Elite Hunter"),
        ("250", "Hybrid OTM Tactical"),
        "RAMSHOT HUNTER",
        "63.0",
        "2569",
        "66.5",
        "2703",
    ),
    (
        "338 Winchester Magnum",
        26,
        ("300", "Elite Hunter"),
        ("300", "Hybrid OTM Tactical"),
        "VIHT N560",
        "62.0",
        "2384",
        "65.5",
        "2522",
    ),
    (
        "340 Weatherby Magnum",
        26,
        ("250", "Elite Hunter"),
        ("250", "Hybrid OTM Tactical"),
        "NORMA MRP",
        "76.0",
        "2699",
        "80.0",
        "2842",
    ),
    (
        "340 Weatherby Magnum",
        26,
        ("300", "Elite Hunter"),
        ("300", "Hybrid OTM Tactical"),
        "VIHT N560",
        "70.0",
        "2458",
        "73.8",
        "2582",
    ),
]

# Sheet cartridge heading -> the name data/ballistics/cartridges.json records.
CARTRIDGE = {
    "6.5 x 55mm Swedish Mauser": "6.5 x 55 Swedish",
    "6.5-284 Norma": "6.5-284 Norma",
}

ROW = re.compile(
    r"^(?P<powder>[A-Za-z][A-Za-z0-9 .\-/#]*?)\s+"
    r"(?P<start_gr>\d{1,2}\.\d)\s+(?P<start_fps>\d{3,4})\s+"
    r"(?P<max_gr>\d{1,2}\.\d)\s+(?P<max_fps>\d{3,4})\s+"
    r"(?P<fill>\d{1,3})\s*%$"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sheet_text(path: Path) -> str:
    return subprocess.run(
        ["pdftotext", "-raw", str(path), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def parse_sheet(path: Path) -> dict | None:
    text = sheet_text(path)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 8 or "Barrel Length" not in text:
        return None
    heading = lines[0]
    grain = re.match(r"^([\d.]+) Grain$", lines[1])
    barrel = re.search(r'Barrel Length = ([\d.]+)\s*[”"]', text)
    part = re.search(r"Part # (\d+)", text)
    descriptor = re.search(r"^([\d.]+) gr (.+)$", text, re.MULTILINE)
    if not (grain and barrel and part and descriptor):
        return None

    rows = []
    for line in lines:
        found = ROW.match(line)
        if found:
            rows.append(found.groupdict())
    if not rows:
        return None
    best = max(rows, key=lambda row: int(row["max_fps"]))
    model = MODEL.get(descriptor.group(2).strip().lower())
    if model is None:
        return None
    mass = descriptor.group(1)
    return {
        "cartridge": CARTRIDGE.get(heading, heading),
        "projectile": f"{mass} Grain {model}",
        "barrel_mm": round(float(barrel.group(1)) * 25.4, 1),
        "velocity_ms": round(int(best["max_fps"]) * 0.3048, 1),
        "source_locator": f"{BASE}{path.name} p.1, table row '{best['powder']}'",
        "source_note": (
            f"Berger {heading} {grain.group(1)} grain load sheet "
            f"(part {part.group(1)}), Barrel Length = {barrel.group(1)} in; "
            f"fastest published approximate maximum velocity: "
            f"{best['powder']} {best['max_gr']} gr -> {best['max_fps']} fps "
            f"(start load {best['start_gr']} gr -> {best['start_fps']} fps); "
            f"sheet sha256={digest(path)}"
        ),
    }


def scanned_rows() -> list[dict]:
    """Return the rows transcribed from the scanned 338-family sheets."""
    rows = []
    for (
        cartridge,
        barrel_in,
        first,
        second,
        powder,
        start_gr,
        start_fps,
        max_gr,
        max_fps,
    ) in SCANNED:
        sheet = capture_path(
            "ballistics", f"berger/pdf/{cartridge.replace(' ', '-')}-{first[0]}gr.pdf"
        )
        for bullet in (first, second):
            rows.append(
                {
                    "cartridge": cartridge,
                    "projectile": f"{bullet[0]} Grain {bullet[1]}",
                    "barrel_mm": round(barrel_in * 25.4, 1),
                    "velocity_ms": round(int(max_fps) * 0.3048, 1),
                    "source_locator": (
                        f"{BASE}{sheet.name} p.1 (scanned page, table row '{powder}')"
                    ),
                    "source_note": (
                        f"Berger {cartridge} {bullet[0]} grain load sheet, "
                        f"Barrel Length = {barrel_in} in; fastest published "
                        f"approximate maximum velocity: {powder} {max_gr} gr -> "
                        f"{max_fps} fps (start load {start_gr} gr -> {start_fps} fps). "
                        f"The sheet is an image with no text layer, so the printed "
                        f"table was read from the page; it lists both "
                        f"{bullet[0]} grain bullets against one table. "
                        f"Sheet sha256={digest(sheet)}"
                    ),
                }
            )
    return rows


def main() -> None:
    sheets = sorted((cache_root() / "ballistics" / "berger" / "pdf").glob("*.pdf"))
    if not sheets:
        raise SystemExit("no Berger sheets in the cache")
    loads, skipped = [], []
    for sheet in sheets:
        row = parse_sheet(sheet)
        if row is None:
            skipped.append(sheet.name)
            continue
        loads.append(row)
    loads.extend(scanned_rows())
    index = capture_path("ballistics", "berger/reloading-data.html")
    record = {
        "url": INDEX_URL,
        "retrieved": "2026-10-23",
        "sha256": digest(index),
        "capture": "local-cache-only",
        "capture_path": str(index),
        "note": (
            "Berger load-data sheets linked from the Berger Reloading Data page, "
            "one PDF per cartridge and bullet weight. Every sheet prints the test "
            "barrel length; a sheet without one was not used. The projectile "
            "designation repeats the mass and model words the Berger projectile "
            "name uses, so the verifier's token test binds the load. Velocities are "
            "the fastest approximate maximum-charge velocity each sheet prints. "
            "Each load cites its own sheet URL and that sheet's sha256; the bytes "
            "are held in the local source cache and are not redistributed. Six "
            "further scanned sheets (338-300 Winchester Short Magnum, 338 Edge, "
            "338-378 Weatherby Magnum) are not emitted because cartridges.json "
            "holds no record for those chamberings. The 2024 catalogue's "
            "ammunition velocities are not used because it prints no barrel length."
        ),
        "loads": loads,
    }
    OUT.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(f"loads: {len(loads)}; sheets without a text table: {len(skipped)}")
    if skipped:
        print("skipped: " + ", ".join(skipped))


if __name__ == "__main__":
    main()
