#!/usr/bin/env python3
"""Capture a real munition from its encyclopaedia article.

AEE's blast and fragmentation kernels need what a round actually carries:
its total mass, its warhead mass, the mass of the explosive filling and
what that filling is. Until now the fragmentation kernel held four
hand-written rows and the blast handler derived a charge mass from the
engine's own damage number, which is not a real figure at all.

This captures one munition: it holds the article bytes, registers them as
a source with their digest, and writes a catalogue entry whose every value
carries the locator it was read from.

ONE ENTRY PER PUBLISHED MUNITION, which is usually a FAMILY. An article on
the AGM-114 Hellfire states the figures of the Hellfire, and the matcher's
derived designations let that entry name AGM-114K, AGM-114L and AGM-114N
alike. That is honest: the figures are the family's as the article
publishes them, and a mark whose own figures are published separately gets
its own entry with --id and --mark.

The article is a TIER-5 COMPILATION, so every value it yields is graded
``claimed``. A field the article does not state is simply absent; nothing
is invented to fill it.

Run:
    python3 tools/ingest_wikipedia_munition.py --article AGM-114_Hellfire \\
        --id agm114_hellfire --type missile
    python3 tools/ingest_wikipedia_munition.py --list FILE
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).parents[1]
DATA = REPO / "data" / "munition"
CATALOGUE = DATA / "catalogue"
SOURCES = DATA / "sources.json"
HELD = DATA / "sources"
UA = "AEE-research/1.0 (munition catalogue capture)"

# What a munition IS, in the words the game and the sources both use.
TYPES = ("missile", "bomb", "rocket", "cannon", "grenade", "mortar", "shell")

LB_TO_KG = 0.45359237
IN_TO_MM = 25.4


def fetch(article: str) -> bytes:
    url = f"https://en.wikipedia.org/wiki/{article}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return fh.read()


def infobox(raw: bytes) -> dict:
    """The article's infobox, as a map of lowered label to stated value."""
    text = raw.decode("utf-8", "ignore")
    m = re.search(r'<table[^>]*class="[^"]*infobox[^"]*"(.*?)</table>', text, re.S)
    if not m:
        return {}
    out: dict[str, str] = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S):
        th = re.search(r"<th[^>]*>(.*?)</th>", row, re.S)
        td = re.search(r"<td[^>]*>(.*?)</td>", row, re.S)
        if not (th and td):
            continue
        key = html.unescape(re.sub(r"<[^>]+>", " ", th.group(1)))
        val = html.unescape(re.sub(r"<[^>]+>", " ", td.group(1)))
        key = re.sub(r"\s+", " ", key).strip().lower().rstrip(":")
        val = re.sub(r"\s+", " ", val).strip()
        val = re.sub(r"\[\s*\d+\s*\]", "", val).strip()
        if key and val:
            out[key] = val
    return out


def article_title(raw: bytes) -> str:
    m = re.search(r"<title>(.*?)</title>", raw.decode("utf-8", "ignore"), re.S)
    if not m:
        return ""
    return html.unescape(m.group(1)).replace(" - Wikipedia", "").strip()


def redirected_from(raw: bytes) -> str:
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw.decode("utf-8", "ignore")))
    m = re.search(r"Redirected from ([^)]{1,40})", text)
    return m.group(1).strip() if m else ""


# A number, or the FIRST number of a stated range. An article writes a
# family's mass as a range across its marks ("100-108 lb (45-49 kg)"), and
# both bounds are real published masses. The first one written is taken,
# and the locator carries the whole stated text so the range is never
# hidden from a reader of the corpus.
_NUM = r"([\d,]+(?:\.\d+)?)\s*(?:[-–—]\s*[\d,]+(?:\.\d+)?\s*)?"


def mass_kg(text: str):
    """A mass in kilograms, from whichever unit the article states.

    An article writes the metric figure first when it is the original and
    the imperial first when THAT is, so both are read and the kilogram
    figure is preferred when the article gives it: a converted figure is
    the article's own conversion, not this tool's.
    """
    m = re.search(_NUM + r"(?:kg|kilogram)", text, re.I)
    if m:
        return float(m.group(1).replace(",", "")), f"{m.group(1)} kg"
    m = re.search(_NUM + r"g\b", text)
    if m:
        return float(m.group(1).replace(",", "")) / 1000, f"{m.group(1)} g"
    m = re.search(_NUM + r"(?:lb|pound)", text, re.I)
    if m:
        return float(m.group(1).replace(",", "")) * LB_TO_KG, f"{m.group(1)} lb"
    return None, ""


def length_mm(text: str):
    for pattern, scale, unit in (
        (_NUM + r"mm", 1.0, "mm"),
        (_NUM + r"cm", 10.0, "cm"),
        (_NUM + r"m\b", 1000.0, "m"),
        (_NUM + r"in\b", IN_TO_MM, "in"),
    ):
        m = re.search(pattern, text, re.I)
        if m:
            return float(m.group(1).replace(",", "")) * scale, f"{m.group(1)} {unit}"
    return None, ""


# The explosive fillings a munition article names, and the spelling the
# fragmentation kernel's Gurney register uses for each.
FILLINGS = (
    ("composition b", "Composition B"), ("comp b", "Composition B"),
    ("tritonal", "Tritonal"), ("torpex", "Torpex"),
    ("pbxn-109", "PBXN-109"), ("pbxn-5", "PBXN-5"), ("pbxn", "PBXN"),
    ("pbxc-19", "PBXC-19"), ("pbx", "PBX"),
    ("okfol", "OKFOL"), ("hmx", "HMX"), ("rdx", "RDX"),
    ("tnt", "TNT"), ("amatol", "Amatol"), ("h-6", "H-6"),
    ("comp a-3", "Composition A-3"), ("composition a-3", "Composition A-3"),
    ("ahead", ""), ("hexal", "Hexal"), ("a-ix-2", "A-IX-2"),
    ("tgaf-5", "TGAF-5"), ("hexogen", "RDX"), ("octol", "Octol"),
)


def filling_of(text: str) -> str:
    low = text.lower()
    for needle, name in FILLINGS:
        if needle in low and name:
            return name
    return ""


def value(num, unit, source, locator, state):
    return {
        "value": num,
        "unit": unit,
        "source": source,
        "locator": locator,
        "state": state,
        "grade": "claimed",
    }


STATE = "as published; source tier-5 compilation"


def build_values(box: dict, source: str) -> dict:
    """Read the fields the article states, and only those."""
    out: dict = {}

    def put(field, unit, pair, label):
        num, written = pair
        if num is None:
            return
        out[field] = value(
            round(num, 4), unit, source, f"Infobox, {label}: {written}", STATE
        )

    if "mass" in box:
        put("total_mass_kg", "kg", mass_kg(box["mass"]), f"mass: {box['mass'][:70]}")
    for key in ("warhead weight", "warhead"):
        if key in box and "warhead_mass_kg" not in out:
            num, written = mass_kg(box[key])
            if num is not None:
                put("warhead_mass_kg", "kg", (num, written), f"{key}: {box[key][:70]}")
    for key in ("filling weight", "filling"):
        if key in box and "charge_mass_kg" not in out:
            num, written = mass_kg(box[key])
            if num is not None:
                put("charge_mass_kg", "kg", (num, written), f"{key}: {box[key][:70]}")
    if "length" in box:
        put("length_mm", "mm", length_mm(box["length"]), f"length: {box['length'][:70]}")
    for key in ("diameter", "calibre", "caliber"):
        if key in box and "calibre_mm" not in out:
            put("calibre_mm", "mm", length_mm(box[key]), f"{key}: {box[key][:70]}")

    # The filling NAME, which is what gives the fragmentation kernel its
    # Gurney energy. It is read from whichever field names an explosive.
    for key in ("filling", "warhead", "filling weight", "explosive"):
        name = filling_of(box.get(key, ""))
        if name:
            out["filling"] = value(
                name, "name", source, f"Infobox, {key}: {box[key][:70]}", STATE
            )
            break
    for key in ("guidance system", "guidance"):
        if key in box:
            out["guidance"] = value(
                re.sub(r"\s+", " ", box[key])[:80], "name", source,
                f"Infobox, {key}: {box[key][:70]}", STATE,
            )
            break
    return out


def capture(article, cid, mtype, aliases, name=None, force=False) -> int:
    raw = fetch(article)
    digest = hashlib.sha256(raw).hexdigest()
    title = article_title(raw)
    box = infobox(raw)
    if not box:
        print(f"{cid}: the article states no infobox, nothing captured")
        return 1

    source_id = "wikipedia_" + re.sub(r"[^a-z0-9]+", "_", article.lower()).strip("_")
    HELD.mkdir(parents=True, exist_ok=True)
    (HELD / f"{source_id}.html").write_bytes(raw)

    registry = json.loads(SOURCES.read_text(encoding="utf-8")) if SOURCES.exists() else []
    known = {s["source_id"] for s in registry}
    if source_id not in known:
        registry.append(
            {
                "source_id": source_id,
                "tier": 5,
                "type": "compilation",
                "title": f"English Wikipedia article '{title}'",
                "edition": "",
                "identifier": source_id,
                "locator": "Infobox",
                "published": "",
                "retrieved": date.today().isoformat(),
                "url": f"https://en.wikipedia.org/wiki/{article}",
                "licence": "CC BY-SA 4.0",
                "primary_held": True,
                "sha256": digest,
                "note": "Munition figures. Tier-5 compilation, so every value "
                        "it backs is graded claimed.",
            }
        )
        SOURCES.write_text(json.dumps(registry, indent=1) + "\n", encoding="utf-8")

    values = build_values(box, source_id)
    if not values:
        print(f"{cid}: the infobox states no figure this corpus holds")
        return 1

    out = CATALOGUE / f"{cid}.json"
    if out.exists() and not force:
        print(f"{cid}: already held, not overwritten")
        return 1
    redirect = redirected_from(raw)
    note = (
        f"Capture for {name or title} from its encyclopaedia article. Every "
        f"value is grade claimed: a tier-5 compilation backs nothing better. "
        f"Fields the article does not state are absent."
    )
    if redirect:
        note += f" The title '{redirect}' redirects to this article."
    out.write_text(
        json.dumps(
            {
                "retrieved": date.today().isoformat(),
                "note": note,
                "sources": [],
                "entries": [
                    {
                        "catalogue_id": cid,
                        "canonical_name": name or title,
                        "munition_type": mtype,
                        "aliases": sorted({a.strip() for a in aliases if a.strip()}),
                        "keywords": [],
                        "values": values,
                    }
                ],
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{cid}: {', '.join(sorted(values))}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--article")
    ap.add_argument("--id")
    ap.add_argument("--type", choices=TYPES, default="missile")
    ap.add_argument("--name", default=None)
    ap.add_argument("--alias", action="append", default=[])
    ap.add_argument("--force", action="store_true")
    ap.add_argument(
        "--list",
        help="a TSV of id<TAB>article<TAB>type<TAB>alias,alias,... to capture in one run",
    )
    args = ap.parse_args()

    if args.list:
        bad = 0
        for line in Path(args.list).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            cid, article = parts[0], parts[1]
            mtype = parts[2] if len(parts) > 2 and parts[2] else "missile"
            aliases = parts[3].split(",") if len(parts) > 3 else []
            name = parts[4] if len(parts) > 4 and parts[4] else None
            try:
                bad += capture(article, cid, mtype, aliases, name, args.force)
            except Exception as exc:  # a dead title must not stop the run
                print(f"{cid}: FAILED {exc}")
                bad += 1
        return 0 if bad == 0 else 1

    if not (args.article and args.id):
        ap.error("--article and --id are required without --list")
    return capture(args.article, args.id, args.type, args.alias, args.name, args.force)


if __name__ == "__main__":
    sys.exit(main())
