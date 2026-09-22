#!/usr/bin/env python3
"""Mine the archive.org manual library for weapon mass and twist.

The maker sites cover current models. A discontinued or historical arm
often has no page left, and its manual in the archived library is then
the held document. This tool matches a catalogue model to a manual,
fetches the OCR text layer, and extracts a candidate value with the
verbatim line, so a person can check it before it enters the database.

The output is a CANDIDATE file. A review of the first run showed that
about half of the candidates were wrong: a trigger mass, a bolt mass, or
a value from another weapon's manual. A candidate is a lead, never a
value. A person or a verifier reads the verbatim line and writes the
accepted rows to sources/weapon_mass_manuals.json, which is the file the
merge step reads.

Run:  python3 tools/validation/mine_manual_library.py [limit]
"""

import concurrent.futures
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
LIBRARY = SRC / "manual_library.json"
DB = DATA / "weapons.json"
OUT = SRC / "weapon_mass_candidates.json"
CACHE = Path("/tmp/opencode/manuals_cache")

MASS_WORDS = ("weight", "gewicht", "masse", "poids", "peso", "waga", "вес", "mass")
UNIT_TO_KG = {
    "kg": 1.0,
    "kilogram": 1.0,
    "g": 0.001,
    "gram": 0.001,
    "lb": 0.45359237,
    "lbs": 0.45359237,
    "pound": 0.45359237,
    "oz": 0.028349523125,
    "ounce": 0.028349523125,
}
TWIST_WORDS = ("twist", "rifling", "drall", "rayure", "нарез")

MASS_RE = re.compile(
    r"(?P<value>\d+[.,]?\d*)\s*(?P<unit>kg|kilogram\w*|g|gram\w*|lbs?|pound\w*|oz|ounce\w*)",
    re.I,
)
TWIST_RE = re.compile(
    r"(?:1\s*(?:turn\s*)?(?:in|:)\s*(?P<inch>\d+(?:[.,]\d+)?)\s*(?:\"|in|inch)?)"
    r"|(?P<mm>\d{2,3}(?:[.,]\d+)?)\s*mm\s*(?:per\s*turn|/)",
    re.I,
)


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def tokens(text):
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(t) > 2}


def fetch_text(stem, base):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{stem}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="ignore")
    url = f"{base}{stem}_djvu.txt"
    raw = subprocess.run(
        ["curl", "-sL", "--max-time", "60", "-A", "Mozilla/5.0", url],
        capture_output=True,
    ).stdout
    text = raw.decode("utf-8", errors="ignore")
    path.write_text(text, encoding="utf-8", errors="ignore")
    return text


def find_mass(text):
    """Return (mass_kg, verbatim line) or (None, None)."""
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        low = line.lower()
        if not any(word in low for word in MASS_WORDS):
            continue
        scope = " ".join(lines[index : index + 3])
        match = MASS_RE.search(scope)
        if not match:
            continue
        unit = match.group("unit").lower()
        grams = UNIT_TO_KG.get(unit.rstrip("."))
        if grams is None:
            continue
        try:
            value = float(match.group("value").replace(",", "."))
        except ValueError:
            continue
        kilograms = value * grams
        if 0.1 <= kilograms <= 20.0:
            return round(kilograms, 3), line[:160]
    return None, None


def find_twist(text):
    """Return (twist_m, verbatim line) or (None, None)."""
    for line in text.splitlines():
        low = line.lower()
        if not any(word in low for word in TWIST_WORDS):
            continue
        match = TWIST_RE.search(line)
        if not match:
            continue
        if match.group("inch"):
            millimetres = float(match.group("inch").replace(",", ".")) * 25.4
        else:
            millimetres = float(match.group("mm").replace(",", "."))
        if 100.0 <= millimetres <= 2000.0:
            return round(millimetres / 1000, 5), line.strip()[:160]
    return None, None


def model_keys(record):
    """The names a document stem must carry for the match to be trusted."""
    keys = {normalise(record["weapon_id"])}
    keys |= {normalise(alias) for alias in record.get("aliases", [])}
    keys |= {normalise(record.get("names", [""])[0])}
    return {key for key in keys if len(key) >= 4}


def score(stem, record):
    """The length of the model key the stem carries, or zero.

    The document must name the model. A shared chambering is not enough,
    because an FN .308 manual must not supply the twist of a Sako .308.
    """
    flat = normalise(stem)
    return max((len(key) for key in model_keys(record) if key in flat), default=0)


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    library = json.loads(LIBRARY.read_text(encoding="utf-8"))
    base = library["download_base"]
    weapons = json.loads(DB.read_text(encoding="utf-8"))
    wanted = [w for w in weapons if "mass_kg" not in w.get("values", {})]

    pairs = []
    for record in wanted:
        best, best_score = None, 0
        for document in library["documents"]:
            if not document["ocr_text"]:
                continue
            current = score(document["stem"], record)
            if current > best_score:
                best, best_score = document["stem"], current
        if best and best_score >= 4:
            pairs.append((record, best))
    if limit:
        pairs = pairs[:limit]
    print(f"models without mass: {len(wanted)}, matched to a manual: {len(pairs)}")

    sources, weights = {}, []
    skipped = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        texts = dict(
            pool.map(
                lambda p: (p[1], fetch_text(p[1], base)),
                {(r["weapon_id"], s): None for r, s in pairs}.keys() and pairs,
            )
        )
    # The map above keeps insertion order; walk the pairs again.
    for record, stem in pairs:
        text = texts.get(stem)
        if not text:
            continue
        mass, mass_line = find_mass(text)
        twist, twist_line = find_twist(text)
        if mass is None and twist is None:
            continue
        # The document must place the weapon, or its chambering, in
        # context. Without this check an AR-15 manual supplies 1:7 to an
        # AK-74.
        body = normalise(text)
        weapon_token = normalise(record["weapon_id"])
        chamber_digits = re.sub(r"[^0-9]", "", record.get("cartridge_id", ""))[:3]
        if not ((weapon_token and weapon_token in body)
                or (len(chamber_digits) == 3 and chamber_digits in body)):
            skipped += 1
            continue
        source_id = "manual_" + re.sub(r"[^a-z0-9]+", "_", stem.lower())[:40]
        if source_id not in sources:
            digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()
            sources[source_id] = {
                "source_id": source_id,
                "title": f"Maker manual or catalogue: {stem.replace('_', ' ')}",
                "url": f"{base}{stem}_djvu.txt",
                "sha256": digest,
                "note": "OCR text layer of the archived manual.",
            }
        row = {
            "verified": False,
            "weapon_key": record["weapon_id"],
            "maker": record.get("manufacturer", ""),
            "weapon": record.get("names", [""])[0],
            "source_id": source_id,
        }
        if mass is not None:
            row["mass_kg"] = mass
            row["state"] = "as published"
            row["note"] = mass_line
        if twist is not None:
            row["twist_mm"] = round(twist * 1000, 2)
            row["twist_note"] = twist_line
        weights.append(row)

    OUT.write_text(
        json.dumps(
            {
                "retrieved": "2026-09-22",
                "note": (
                    "Mined from the archived manual library. A candidate needs "
                    "a check against the verbatim line before it is trusted."
                ),
                "sources": list(sources.values()),
                "weights": weights,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"candidates: {len(weights)} mass or twist, "
        f"dropped for no chambering context: {skipped}, "
        f"sources: {len(sources)}, wrote {OUT.name}"
    )


if __name__ == "__main__":
    main()
