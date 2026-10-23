#!/usr/bin/env python3
"""Fetch the Sierra rifle and handgun load data and parse its special loads.

Sierra publishes one PDF per cartridge from the sixth edition of its
reloading manual. Each PDF states the test barrel length, the bullets with
their part number, mass and type, and a "Special Load" table that names a
powder, a charge in grains and the muzzle velocity that charge produced.
The special load sits under the block of bullets it was worked up for, so
its velocity is the published velocity for those bullets in that
cartridge, measured in the barrel the PDF states.

Only the special load row is read. The velocity grid above it prints a
charge per velocity contour and its columns do not survive text
extraction, so a value taken from the grid could be attached to the wrong
velocity. The special load row is an explicit powder, charge and velocity
line, so nothing is inferred.

The bytes are held in the machine-local source cache and are not
committed. The committed record is the extract with the digest of every
document it read.

Run:  python3 tools/validation/fetch_sierra_load_data.py
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))
from tools.validation import source_cache  # noqa: E402

DATA = REPO / "data" / "ballistics"
INDEX_URL = "https://sierrabullets.com/load-data/"
OUT = DATA / "sources" / "sierra_velocity.json"
NS = "{http://www.w3.org/1999/xhtml}"

BULLET = re.compile(r"^#\s?(\d{3,5})\b")
MASS = re.compile(r"\b(\d{2,3})\s?gr\b")
SPECIAL = re.compile(r"\b(Accuracy Load|Hunting Load)\b")
BARREL = re.compile(r"Barrel Length:\s*([0-9.]+)")
TITLE = re.compile(r"^\d[^\n]{4,60}$")
# The words of the watermark printed across every table, which a diagonal
# line can drop between the words of a powder name.
WATERMARK = {
    "this", "data", "is", "for", "individual", "individ", "ual", "use", "only",
    "do", "no", "t", "e", "d", "i", "s", "o", "f", "r", "edit", "or", "redist",
    "red", "ribute", "not", "n",
}
HEADER = re.compile(
    r"^(test specifications|firearm used|barrel length|twist|"
    r"components|case|primer|trim-to|remarks|maximum)\b",
    re.I,
)


def get(url: str, retries: int = 3) -> bytes:
    last: Exception | None = None
    for _ in range(retries):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
            )
            return urllib.request.urlopen(request, timeout=120).read()
        except Exception as exc:  # noqa: BLE001 - a retry covers a transient fault
            last = exc
    raise RuntimeError(f"{url}: {last}")


def page_rows(pdf: Path):
    """Yield each page as rows of (x, text), top to bottom."""
    text = subprocess.run(
        ["pdftotext", "-bbox-layout", str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    root = ET.fromstring(re.sub(r"<!DOCTYPE[^>]*>", "", text))
    for page in root.iter(NS + "page"):
        words = [
            (float(word.get("xMin")), float(word.get("yMin")), word.text or "")
            for word in page.iter(NS + "word")
        ]
        words.sort(key=lambda item: (item[1], item[0]))
        rows: list[list] = []
        for x, y, word in words:
            if rows and abs(y - rows[-1][0]) <= 3.0:
                rows[-1][1].append((x, word))
            else:
                rows.append([y, [(x, word)]])
        yield [
            (min(x for x, _ in cells), " ".join(w for _, w in sorted(cells)))
            for _, cells in rows
        ]


def special_load(text: str) -> tuple[str, float, float] | None:
    """Return the powder, charge in grains and velocity in fps of a row.

    A watermark is printed across the table, so stray words sit between the
    numbers. The velocity is the first four-digit number after the charge,
    the charge is the number before it, and the powder is the text between
    the row label and the charge.
    """
    numbers = list(re.finditer(r"\d+(?:\.\d+)?", text))
    label_end = SPECIAL.search(text).end()
    for index, match in enumerate(numbers):
        if index and float(match.group(0)) >= 1000:
            velocity = float(match.group(0))
            charge_match = numbers[index - 1]
            charge = float(charge_match.group(0))
            # A powder name can carry a number of its own ("IMR 8208 XBR",
            # "RE 7", "N 540"), so the name ends where the charge begins.
            # The watermark is diagonal, so a word of it can land inside the
            # name; those words are dropped and the rest of the name stays.
            powder = " ".join(
                word
                for word in text[label_end : charge_match.start()].split()
                if word.lower().strip(".,") not in WATERMARK
            )
            if velocity and charge and powder:
                return powder, charge, velocity
            return None
    return None


def parse(pdf: Path) -> list[dict]:
    if pdf.open("rb").read(5) != b"%PDF-":
        return []
    section = None
    pending: list[tuple[str, float, str]] = []
    barrels: dict[str, float] = {}
    out: list[dict] = []
    for rows in page_rows(pdf):
        for x, text in rows[:6]:
            text = text.strip()
            if (
                x < 110
                and TITLE.match(text)
                and re.search(r"[A-Za-z]", text)
                and not BULLET.match(text)
                and not SPECIAL.search(text)
            ):
                section = text
                pending = []
                break
        for _, text in rows:
            text = text.strip()
            barrel = BARREL.search(text)
            if barrel:
                if section:
                    barrels[section] = float(barrel.group(1))
                continue
            head = HEADER.match(text)
            if head:
                continue
            bullet = BULLET.match(text)
            if bullet:
                mass = MASS.search(text)
                if mass:
                    pending.append(
                        (bullet.group(1).lstrip("0"), float(mass.group(1)), text)
                    )
                continue
            if SPECIAL.search(text) and pending:
                load = special_load(text)
                if load:
                    powder, charge, velocity = load
                    kind = SPECIAL.search(text).group(1)
                    for part, mass, raw in pending:
                        out.append(
                            {
                                "kind": kind,
                                "section": section,
                                "part": part,
                                "mass_gr": mass,
                                "row": raw,
                                "powder": powder,
                                "charge_gr": charge,
                                "velocity_fps": velocity,
                                "barrel_in": barrels.get(section),
                            }
                        )
                pending = []
    return out


def document_paths() -> list[tuple[str, str]]:
    """Return (cache name, index href) for every load data PDF the index names."""
    index = get(INDEX_URL).decode("utf-8", "replace")
    hrefs = sorted(
        {
            href.replace("&amp;", "&")
            for href in re.findall(r'href="(/content/load-data/[^"]+\.pdf)"', index)
        }
    )
    return [(href.rsplit("/", 1)[1], href) for href in hrefs], hashlib.sha256(
        index.encode("utf-8")
    ).hexdigest()


def main() -> int:
    documents, index_digest = document_paths()
    records = []
    seen = set()
    held = []
    for name, href in documents:
        capture = source_cache.capture_path("ballistics", f"sierra_load_data/{name}")
        if not capture.exists() or capture.open("rb").read(5) != b"%PDF-":
            capture.parent.mkdir(parents=True, exist_ok=True)
            try:
                capture.write_bytes(
                    get("https://sierrabullets.com" + urllib.parse.quote(href))
                )
            except RuntimeError:
                continue  # the index lists a case variant the server does not serve
        if capture.open("rb").read(5) != b"%PDF-":
            continue
        held.append(
            {
                "document": name,
                "sha256": hashlib.sha256(capture.read_bytes()).hexdigest(),
            }
        )
        for row in parse(capture):
            key = (row["section"], row["part"], row["velocity_fps"])
            if not row["barrel_in"] or not row["section"] or key in seen:
                continue
            seen.add(key)
            row["document"] = name
            records.append(row)
    records.sort(key=lambda row: (row["section"], row["mass_gr"], row["part"]))
    payload = {
        "url": INDEX_URL,
        "retrieved": "2026-10-23",
        "capture": "local-cache-only",
        "index_sha256": index_digest,
        "note": (
            "Sierra Reloading Manual, sixth edition, cartridge load data sheets. "
            "Each sheet states its test barrel length. One record per special "
            "load row (Accuracy Load or Hunting Load), which names the powder, "
            "the charge in grains and the velocity in fps that charge produced "
            "in that barrel."
        ),
        "documents": held,
        "loads": records,
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"sierra load data: {len(records)} special loads from {len(held)} documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
