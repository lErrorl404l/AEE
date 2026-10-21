#!/usr/bin/env python3
"""Capture a real vehicle or aircraft from its encyclopaedia article.

The matcher can only name a thing the catalogue holds, so a real vehicle
that appears in the game or in a mod but not in the catalogue is a gap.
This captures one: it holds the article bytes, registers them as a source
with their digest, and writes a catalogue entry whose every value carries
the locator it was read from.

The article is a TIER-5 COMPILATION, so every value it yields is graded
``claimed`` - the same grade the existing encyclopaedia-sourced entries
carry. It is evidence of what the real vehicle is, not a manufacturer
datasheet, and the grade says so. A field the article does not state is
simply absent; nothing is invented to fill it.

Run:
    python3 tools/ingest_wikipedia_vehicle.py --domain vehicle \\
        --article LAV-25 --id lav25 --type wheeled
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
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation import source_cache  # noqa: E402
UA = "AEE-research/1.0 (vehicle catalogue capture)"


def fetch(article: str) -> bytes:
    url = f"https://en.wikipedia.org/wiki/{article}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as fh:
        return fh.read()


def infobox(raw: bytes) -> dict:
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
        # Drop reference markers: "[ 2 ]" is a citation, not a value.
        val = re.sub(r"\[\s*\d+\s*\]", "", val).strip()
        if key and val:
            out[key] = val
    return out


def speclist(raw: bytes) -> dict:
    """Read an aircraft article's Specifications list.

    An aircraft article states its figures as labelled list items,
    "<li><b>Empty weight:</b> 3,300 kg</li>", rather than in the infobox,
    so those are parsed too and merged under the keys the infobox would
    have used.
    """
    text = raw.decode("utf-8", "ignore")
    want = (
        "empty weight", "gross weight", "max takeoff weight", "length",
        "wingspan", "height", "maximum speed", "cruise speed", "powerplant",
        "width",
    )
    out: dict[str, str] = {}
    for item in re.findall(r"<li>(.*?)</li>", text, re.S):
        m = re.match(r"\s*<b>(.*?)</b>(.*)", item, re.S)
        if not m:
            continue
        key = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
        key = re.sub(r"\s+", " ", key).strip().lower().rstrip(":")
        if key not in want or key in out:
            continue
        val = html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
        val = re.sub(r"\[\s*\d+\s*\]", "", val)
        val = re.sub(r"\s+", " ", val).strip()
        if val:
            out[key] = val[:160]
    return out


def first_number(text: str, units: tuple[str, ...]) -> float | None:
    for unit in units:
        m = re.search(r"([\d,]+(?:\.\d+)?)\s*" + unit + r"\b", text, re.I)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def value(num, unit, locator, state):
    return {
        "value": num,
        "unit": unit,
        "source": None,  # filled by the caller
        "locator": locator,
        "state": state,
        "grade": "claimed",
    }


def build_values(box: dict, mark: str = "") -> dict:
    """Read the fields the article states, and only those.

    ``mark`` prefixes every state. The aircraft corpus requires a value
    taken from a source whose primary is NOT held to say so in its state,
    so the capture says it rather than presenting a compilation figure as
    if it came from a datasheet.
    """
    out: dict[str, dict] = {}

    mass = (
        box.get("mass")
        or box.get("weight")
        or box.get("empty weight")
        or box.get("gross weight")
        or box.get("max takeoff weight")
    )
    if mass:
        t = first_number(mass, ("t", "tonnes", "tonne"))
        kg = first_number(mass, ("kg",))
        lb = first_number(mass, ("lb", "pounds"))
        n = (t * 1000) if t else (kg if kg else (lb * 0.45359237 if lb else None))
        if n:
            out["operating_weight_kg"] = value(
                round(n), "kg", f"Infobox, mass: {mass[:60]}",
                mark + "operating weight as published; source tier-5 compilation",
            )

    for field, keys in (
        ("length_mm", ("length",)),
        ("width_mm", ("width", "wingspan")),
        ("height_mm", ("height",)),
    ):
        raw = next((box[k] for k in keys if k in box), None)
        if not raw:
            continue
        m = first_number(raw, ("m",))
        if m and m < 200:
            out[field] = value(
                round(m * 1000), "mm", f"Infobox, {keys[0]}: {raw[:60]}",
                mark + f"overall {keys[0]} as published; source tier-5 compilation",
            )

    speed = box.get("maximum speed") or box.get("speed") or box.get("max speed")
    if speed:
        k = first_number(speed, ("km/h", "kmh"))
        mph = first_number(speed, ("mph",))
        n = k if k else (mph * 1.609344 if mph else None)
        if n:
            out["max_speed_kmh"] = value(
                round(n), "km/h", f"Infobox, speed: {speed[:60]}",
                mark + "maximum speed as published; source tier-5 compilation",
            )

    engine = box.get("engine") or box.get("powerplant")
    if engine:
        kw = first_number(engine, ("kW",))
        hp = first_number(engine, ("hp", "bhp"))
        n = kw if kw else (hp * 0.7456998716 if hp else None)
        if n:
            out["net_power_kw"] = value(
                round(n, 1), "kW", f"Infobox, engine: {engine[:60]}",
                mark + "engine power as published; source tier-5 compilation",
            )
        out["engine_model"] = value(
            engine[:120], "text", f"Infobox, engine: {engine[:60]}",
            mark + "engine make and model as published; source tier-5 compilation",
        )
    return out


def build_aircraft_values(box: dict, mark: str) -> dict:
    """The REFERENCE-ONLY aircraft fields an unheld source may fill.

    The aircraft corpus keeps its four calculation inputs for sources whose
    primary is held: a flight manual or a type certificate, never an
    encyclopaedia. So a capture fills only the reference airframe fields,
    which name the aircraft and describe it without feeding the physics.
    """
    out: dict[str, dict] = {}

    def put(field, unit, num, locator, what):
        out[field] = {
            "value": num,
            "unit": unit,
            "source": None,
            "locator": locator,
            "state": mark + what + "; source tier-5 compilation",
            "grade": "claimed",
        }

    # NO weight is captured. The corpus derives the runtime operating
    # weight from a held weight, and a runtime field may never trace back
    # to a source whose primary is not held, so a weight from an
    # encyclopaedia would poison the derivation. It waits for a flight
    # manual or a type certificate.

    for field, keys in (
        ("length_m", ("length",)),
        ("height_m", ("height",)),
        ("wing_span_m", ("wingspan",)),
    ):
        raw = next((box[k] for k in keys if k in box), None)
        if not raw:
            continue
        m = first_number(raw, ("m",))
        if m and m < 200:
            put(field, "m", round(m, 2), f"Specifications, {keys[0]}: {raw[:60]}",
                f"{keys[0]} as published")

    for field, keys in (
        ("max_speed_kmh", ("maximum speed",)),
        ("cruise_speed_kmh", ("cruise speed",)),
    ):
        raw = next((box[k] for k in keys if k in box), None)
        if not raw:
            continue
        k = first_number(raw, ("km/h",))
        if k:
            put(field, "km/h", round(k), f"Specifications, {keys[0]}: {raw[:60]}",
                f"{keys[0]} as published")

    eng = box.get("powerplant") or box.get("engine")
    if eng:
        put("engine_model", "text", eng[:120],
            f"Specifications, powerplant: {eng[:60]}", "engine as published")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", choices=("vehicle", "aircraft"), required=True)
    ap.add_argument("--article", required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--maker", default="")
    ap.add_argument("--type", default="wheeled")
    ap.add_argument("--country", default="")
    ap.add_argument("--era", default="contemporary")
    ap.add_argument("--aliases", default="")
    # Aircraft entries carry two extra identity fields.
    ap.add_argument("--propulsion", default="")
    ap.add_argument("--role", default="")
    args = ap.parse_args()

    data = REPO / "data" / args.domain

    # The catalogue may already hold this thing from a BETTER source - a
    # technical manual beats an encyclopaedia - so never shadow an existing
    # id. The capture is for gaps, not for second opinions.
    for existing in sorted((data / "catalogue").glob("*.json")):
        try:
            payload = json.loads(existing.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for entry in payload.get("entries", []):
            if entry.get("catalogue_id") == args.id:
                print(
                    f"{args.id}: already held in {existing.name}; not captured",
                    file=sys.stderr,
                )
                return 1

    raw = fetch(args.article)
    box = infobox(raw)
    # An aircraft states its figures in the Specifications list; a ground
    # vehicle states them in the infobox. Take both and let the infobox win.
    merged = speclist(raw)
    merged.update(box)
    box = merged
    if not box:
        print(f"{args.article}: no infobox found", file=sys.stderr)
        return 1

    source_id = f"wikipedia_{args.id}"
    held = source_cache.cache_dir(args.domain) / f"{source_id}.html"
    held.parent.mkdir(parents=True, exist_ok=True)
    held.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    today = date.today().isoformat()

    # The aircraft corpus requires an unheld source to be declared in the
    # state; the vehicle corpus carries the same fact in the grade.
    if args.domain == "aircraft":
        mark = "UNSOURCED (tier-5 compilation, primary not held): "
        values = build_aircraft_values(box, mark)
    else:
        values = build_values(box, "")
    for v in values.values():
        v["source"] = source_id
    if not values:
        print(f"{args.article}: infobox states none of the needed fields", file=sys.stderr)
        return 1

    title = args.name or args.article.replace("_", " ")
    record = {
        "source_id": source_id,
        "tier": 5,
        "type": "compilation",
        "title": title,
        "edition": f"English Wikipedia, article snapshot held as HTML, retrieved {today}",
        "identifier": f"English Wikipedia article '{args.article}'",
        "locator": "Infobox, specifications",
        "retrieved": today,
        "url": f"https://en.wikipedia.org/wiki/{args.article}",
        "archive_ref": "English Wikipedia article held as HTML in the local source cache",
        "capture": "local-cache-only",
        "licence": (
            "Wikipedia text is available under the Creative Commons "
            "Attribution-ShareAlike licence. The article is a secondary "
            "compilation. The held bytes are the article HTML, not a primary "
            "document."
        ),
        "primary_held": False,
        "sha256": digest,
        "note": "Captured to close a catalogue gap found by scanning the installed game content.",
    }

    reg_path = data / "sources.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    reg = [r for r in reg if r.get("source_id") != source_id]
    reg.append(record)
    reg.sort(key=lambda r: str(r.get("source_id")))
    reg_path.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    entry = {
        "catalogue_id": args.id,
        "canonical_name": title,
        "maker": args.maker,
        "model": title,
        "variant": "base",
        "variant_id": args.id,
        "vehicle_type": args.type,
        "class_token": "",
        "country": args.country,
        "era": args.era,
        "aliases": [a for a in args.aliases.split("|") if a],
        "keywords": [],
        "runtime_ready": False,
        "values": values,
    }
    if args.domain == "aircraft":
        entry["propulsion"] = args.propulsion
        entry["role"] = args.role
    out = data / "catalogue" / f"{args.id}.json"
    out.write_text(
        json.dumps(
            {
                "retrieved": today,
                "note": (
                    "Capture for "
                    + title
                    + ". Every value is grade claimed: the source is a tier-5 "
                    "compilation. Captured to close a gap found by scanning the "
                    "installed game content."
                ),
                "sources": [],
                "entries": [entry],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"{args.id}: {len(values)} values -> {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
