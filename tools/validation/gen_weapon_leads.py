#!/usr/bin/env python3
"""Turn the sourced real-weapons corpus into weapon LEADS.

The corpus is a compilation. Under ADR-003 a compilation is a tier 5
signal and cannot be an entry source, so a corpus value never enters the
database. It generates a lead instead. The lead says one of:

  agrees_with_standard  our held cartridge standard (tier 1, grade
                        standard) already covers this weapon
  differs_from_standard a real barrel exception, and the worklist for
                        verification against a held primary document
  no_standard           we hold no standard twist for the chambering
  weak_citation         a wiki or a website, not usable even as a lead

The identity is the MODEL, never the manufacturer. The corpus carries ids
such as "izhmash_svds", and a maker inside the key makes the identity
ambiguous, so the maker stays in its own field.

Run:  python3 tools/validation/gen_weapon_leads.py
"""

import csv
import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
CORPUS = Path("/home/matt/Development/AceBallisticsExtention/data/real_weapons.tsv")
LEADS = DATA / "sources" / "weapon_leads.json"
REPORT = DATA / "WEAPON_LEADS.md"
DB = DATA / "weapons.json"
SOURCES = DATA / "sources.json"

STANDARD_WORDS = ("nato", "epvat", "stanag", "saami", "cip", "aep")
MANUAL_WORDS = ("tm ", "tm-", "fm ", "manual", "army", "marine", " mod", "technical")
WEAK_WORDS = (
    "wiki",
    "modern firearms",
    "forum",
    "blog",
    ".com",
    ".org",
    ".net",
    "catalog",
    "catalogue",
    "unknown",
)
TOLERANCE = 0.02

# A corpus chambering name that is another name for a cartridge we hold.
# 7.92 mm Mauser is our 8x57 IS, 7.62x35 mm is the C.I.P. name for the
# .300 AAC Blackout. The mapping only sharpens the lead, it never enters
# a value.
CHAMBERING_SYNONYMS = {
    "7.92x57": "8x57",
    "7.62x35": "300",
}


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def calibre_key(text):
    """The calibre core, so wording differences do not break the match.

    A gauge is kept apart from a bore diameter, so 12 gauge never
    collides with 12.7 mm. A bare cartridge id is never parsed: the id
    "12_7_x_108" would otherwise collapse to the key "12".
    """
    text = (text or "").lower().replace("\u00d7", "x").replace(",", ".")
    text = re.sub(r"\bmm\b", " ", text)
    gauge = re.search(r"(\d+(?:\.\d+)?)\s*(?:gauge|ga)\b", text)
    if gauge:
        return f"{gauge.group(1)}gauge"
    pair = re.search(r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)", text)
    if pair:
        return f"{pair.group(1)}x{pair.group(2)}"
    number = re.search(r"(\d{2,3}(?:\.\d+)?)", text)
    return number.group(1) if number else normalise(text)


def citation_tier(citation):
    text = (citation or "").lower()
    if any(word in text for word in WEAK_WORDS):
        return None
    if any(word in text for word in STANDARD_WORDS):
        return 1
    if any(word in text for word in MANUAL_WORDS):
        return 2
    return 4


def identity(row):
    model = (row.get("model") or "").strip()
    variant = (row.get("variant") or "").strip()
    base = normalise(model) or normalise(row.get("weapon_id", ""))
    names = [f"{model} {variant}".strip()] if model else [row.get("weapon_id", "")]
    return base, names


def main():
    cartridges = json.loads((DATA / "cartridges.json").read_text(encoding="utf-8"))
    standard, standard_id = {}, {}
    for rec in cartridges:
        entry = rec["values"].get("standard_twist_m")
        if not entry:
            continue
        for name in rec.get("names", []):
            key = calibre_key(name)
            standard.setdefault(key, entry["value"])
            standard_id.setdefault(key, rec["cartridge_id"])

    # A weapon that now holds a twist is verified, and leaves the worklist.
    verified_ids = set()
    if DB.exists():
        for record in json.loads(DB.read_text(encoding="utf-8")):
            if "twist_m" in record["values"]:
                verified_ids.add(record["weapon_id"])
                verified_ids.update(record.get("aliases", []))

    rows = list(csv.DictReader(CORPUS.open(encoding="utf-8"), delimiter="\t"))
    leads = []
    counts = {
        "agrees_with_standard": 0,
        "differs_from_standard": 0,
        "no_standard": 0,
        "weak_citation": 0,
        "unsourced": 0,
        "verified": 0,
    }
    for row in rows:
        if (row.get("confidence") or "").strip().lower() != "researched":
            counts["unsourced"] += 1
            continue
        try:
            twist_m = round(float(row.get("twist_mm") or 0) / 1000, 5)
        except ValueError:
            counts["unsourced"] += 1
            continue
        citation = (row.get("source") or "").strip()
        tier = citation_tier(citation)
        if tier is None:
            counts["weak_citation"] += 1
            continue
        weapon_id, names = identity(row)
        key = calibre_key(row.get("cartridge", ""))
        key = CHAMBERING_SYNONYMS.get(key, key)
        held = standard.get(key)
        if held is None:
            verdict = "no_standard"
            counts["no_standard"] += 1
        elif twist_m <= 0:
            # A smoothbore agrees with a zero standard. A zero twist with
            # a rifled standard is a gap in the lead, not a weapon fact.
            verdict = "agrees_with_standard" if held == 0 else "no_standard"
            counts[verdict] += 1
        elif held == 0:
            # A rifled barrel on a smoothbore chambering is a real
            # exception, as a slug gun shows.
            verdict = "differs_from_standard"
            counts["differs_from_standard"] += 1
        elif abs(twist_m - held) <= TOLERANCE * held:
            verdict = "agrees_with_standard"
            counts["agrees_with_standard"] += 1
        else:
            verdict = "differs_from_standard"
            counts["differs_from_standard"] += 1
        verified = weapon_id in verified_ids
        if verified:
            counts["verified"] += 1
        leads.append(
            {
                "weapon_id": weapon_id,
                "verified": verified,
                "names": names,
                "manufacturer": row.get("manufacturer", ""),
                "cartridge": row.get("cartridge", ""),
                "calibre_key": key,
                "cartridge_id": standard_id.get(key, ""),
                "twist_m": twist_m,
                "standard_twist_m": held,
                "verdict": verdict,
                "citation": citation,
                "citation_tier": tier,
            }
        )

    leads.sort(key=lambda lead: (lead["verdict"], lead["weapon_id"]))
    LEADS.write_text(
        json.dumps(
            {
                "generated": "2026-09-22",
                "note": (
                    "A compilation cannot be an entry source (ADR-003, tier 5). "
                    "These are leads for verification, not values."
                ),
                "counts": counts,
                "leads": leads,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )

    exceptions = [
        lead
        for lead in leads
        if lead["verdict"] == "differs_from_standard" and not lead.get("verified")
    ]
    lines = [
        "# Weapon leads",
        "",
        "Generated from the sourced real-weapons corpus by",
        "`tools/validation/gen_weapon_leads.py`. A compilation cannot be an entry",
        "source, so a lead never becomes a value. It names where the chambering",
        "standard already applies and where verification is needed.",
        "",
        f"- Weapons held at the held cartridge standard: {counts['agrees_with_standard']}",
        f"- Weapons that differ: {counts['differs_from_standard']}",
        f"- Of those, now verified against a held source: {counts['verified']}",
        f"- Of those, still open in this worklist: {len(exceptions)}",
        f"- Weapons with no standard for the chambering: {counts['no_standard']}",
        f"- Weak citation, not usable even as a lead: {counts['weak_citation']}",
        f"- Unsourced, skipped: {counts['unsourced']}",
        "",
        "## The verification worklist",
        "",
        "| Weapon | Chambering | Corpus twist (m) | Standard (m) | Citation |",
        "|---|---|---|---|---|",
    ]
    for lead in exceptions:
        lines.append(
            f"| {lead['weapon_id']} | {lead['cartridge']} | {lead['twist_m']} | "
            f"{lead['standard_twist_m']} | tier {lead['citation_tier']} |"
        )
    lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    # The corpus never leaves a value behind. Strip the corpus-sourced
    # values an earlier ingest may have written, and drop a record only
    # when nothing usable remains.
    if DB.exists():
        weapons = json.loads(DB.read_text(encoding="utf-8"))
        kept = []
        for record in weapons:
            values = {
                field: entry
                for field, entry in record["values"].items()
                if not str(entry.get("source", "")).startswith("corpus_")
            }
            if values:
                record["values"] = values
                kept.append(record)
        if kept != weapons:
            DB.write_text(json.dumps(kept, indent=1) + "\n", encoding="utf-8")
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    kept_sources = [s for s in sources if not s["source_id"].startswith("corpus_")]
    if len(kept_sources) != len(sources):
        SOURCES.write_text(json.dumps(kept_sources, indent=1) + "\n", encoding="utf-8")

    print(f"leads: {len(leads)} " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    print(f"wrote {LEADS.name} and {REPORT.name}")


if __name__ == "__main__":
    main()
