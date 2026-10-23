#!/usr/bin/env python3
"""Record, for every cartridge, the standard that defines it.

The register answers one question per cartridge: which standard body
registers it, under which designation, in which edition, and at which
locator. The answer is a list on the record, so a cartridge that both
C.I.P. and SAAMI register cites both.

One entry is authoritative. The C.I.P. register is the base of the
corpus, so it wins where it holds the cartridge. SAAMI is authoritative
where C.I.P. does not hold the cartridge. A service cartridge that only a
NATO document or a military manual defines cites that document. A
cartridge that no held standard defines is reported, never given a made-up
citation.

Where SAAMI and C.I.P. state different pressures, both values go to
conflicts.json. They use different measurement methods, so the database
records the disagreement and never averages it.

Run after gen_cartridge_standards.py:
  python3 tools/validation/gen_cartridge_citations.py
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
CIP_TABS = SRC / "cip" / "cip_tdcc_all_tabs.json"
CIP_EXTRACT = SRC / "cip" / "cip_datasheet_extract.json"
SAAMI = SRC / "saami_pressure.json"
DB = DATA / "cartridges.json"
SOURCES = DATA / "sources.json"
CONFLICTS = DATA / "conflicts.json"
COVERAGE = DATA / "STANDARDS_COVERAGE.md"

BAR_TO_MPA = 0.1
PRESSURE_TOLERANCE = 0.01

# A cartridge whose own spelling does not match the register's.
CIP_ALIAS = {
    "32_acp": ["7,65 mm Browning"],
    "22_winchester_magnum": ["22 Win. Mag. R.F."],
    "22_long_rifle": ["22 L.R."],
    "9_x_19": ["9 mm Luger"],
    "9x18_makarov": ["9 mm Makarov"],
    "45_acp": ["45 Auto."],
    # C.I.P. Tab X registers the low-energy 40 x 46 case under the file
    # name of the DEFTEC submission. The datasheet prints the cartridge
    # and chamber dimensions of the 40 x 46 case.
    "40x46_sr": ["40 x 46 DEFTEC"],
}

# SAAMI registers the rimfire cartridges in Z299.1, which the parsed
# pressure table does not cover. These are the identities it holds.
SAAMI_RIMFIRE = {"22_long_rifle", "22_winchester_magnum"}

STANDARD_SOURCE_PREFIXES = ("cip_", "saami_", "nato_", "stanag", "aep_")

# A standard that governs a cartridge but states no value this corpus can
# enter, so no value cites it and the usual path cannot find it. The
# citation is declared here with its source record, and the pressure stays
# absent because the document states none that is public.
DECLARED_STANDARDS = {
    "30x173": {
        "source": {
            "source_id": "stanag_4624",
            "tier": 2,
            "type": "standard",
            "title": (
                "STANAG 4624, technical performance specification providing "
                "for the interchangeability of 30 mm x 173 ammunition, with "
                "AEP-4624 and AOP-4624 Edition A"
            ),
            "edition": "Edition 2, 2024-10-30",
            "identifier": "STANAG 4624 Ed. 2:2024",
            "locator": "scope and interchangeability specification",
            "published": "2024",
            "retrieved": "2026-10-23",
            "url": (
                "https://shop.standards.ie/en-ie/standards/"
                "stanag-4624-ed-2-2024-737144_saig_nato_nato_3505041/"
            ),
            "licence": "NATO standard, sold through the national standards bodies",
            "primary_held": False,
            "note": (
                "The public catalogue listing states the title, the edition and "
                "the date, and that it supersedes the 2012 edition. The "
                "technical text is not public, so no case dimension, no "
                "pressure and no twist is entered from it."
            ),
        },
        "entry": {
            "standard": "NATO",
            "document": "STANAG 4624, 30 mm x 173 Ammunition",
            "designation": "30 mm x 173",
            "datasheet": "AEP-4624 and AOP-4624 Edition A, technical performance specification",
            "edition": "Edition 2, 2024-10-30",
            "locator": "interchangeability specification, scope",
        },
    },
}

# What was searched for the cartridges that no held standard defines, and
# what each search returned. A reader must be able to repeat the work and
# see that the absence is a finding, not an omission.
STANDARD_SEARCHES = {
    "125mm_2a46": [
        "C.I.P. TDCC: all twelve tables enumerated. No 120 mm and no 125 mm cartridge is registered.",
        "SAAMI Z299: no 125 mm cartridge is registered.",
        "NATO: no tank-gun ammunition standard found. STANAG 4624 covers 30 mm x 173 only.",
        "The held Yugoimport M88 sheet states no chamber pressure, so none is entered. Figures of 510 MPa and 650 MPa circulate in encyclopaedic sources with no primary citation, so they are not entered.",
    ],
    "145x114": [
        "C.I.P. TDCC: no 14,5 designation in any of the twelve tables. The nearest Soviet entry is 5,45 x 39.",
        "SAAMI Z299: no 14.5 x 114 entry.",
        "No public military manual, proof-house sheet or drawing found that states the case dimensions or the maximum pressure. A figure of 360 MPa circulates with no primary citation, so it is not entered.",
    ],
    "58x42": [
        "C.I.P. TDCC and SAAMI Z299: not registered, and no 5,8 designation exists in either.",
        "DSIAC technical inquiry, Information on the 5.8- x 42-mm DBP10 Round, 8 July 2019: states that the material and ballistic data were supplied privately and were classified, and publishes no dimension and no pressure. This is positive evidence that the defining data is not public.",
        "No GJB number could be verified from a public register.",
    ],
    "77x58_arisaka": [
        "C.I.P. TDCC: only 6,5 x 51 R (Arisaka) is registered. No 7,7 designation exists in any table.",
        "SAAMI Z299.4: no Arisaka entry and no 7.7 x 58 entry.",
        "Catalog of Enemy Ordnance Materiel (1945), held as coe_1945_part2, gives the designations and prints a chamber-pressure row, but the scan of that row is not legible, so no pressure is entered from it.",
    ],
    "40x46_sr": [
        "C.I.P. Tab X registers the case twice, as 40 x 46 DEFTEC and as 40 x 46 BDLR X, and never under the United States military designation. A search for the military designation alone misses it.",
        "SAAMI Z299: does not register 40 x 46.",
        "TM 43-0001-28, held, gives the M406 and M433 rounds, the 40 mm calibre and the muzzle velocity, and states no chamber pressure for either.",
    ],
}


def canon(text):
    """Return the comparison key for a cartridge name.

    The register writes a decimal comma, a space around the x, and a
    trailing mm. None of those change which cartridge is named.
    """
    text = str(text).lower()
    text = text.replace("&amp;", "&")
    # A calibre writes the unit as 9mm or 9 mm. Neither spelling names a
    # different cartridge, so the unit is removed before comparison.
    text = re.sub(r"(?<=\d)\s*mm\b", "", text)
    return re.sub(r"[^a-z0-9]", "", text)


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def cip_index():
    index = {}
    for tab, rows in load("sources/cip/cip_tdcc_all_tabs.json").items():
        for row in rows:
            index[canon(row["name"])] = (tab, row)
    return index


def saami_index():
    index = {}
    for row in load("sources/saami_pressure.json")["cartridges"]:
        index[canon(row["cartridge"])] = row
    return index


def find_cip(record, cip):
    names = record.get("names", [])
    for alias in CIP_ALIAS.get(record["cartridge_id"], []):
        names = names + [alias]
    for name in names:
        hit = cip.get(canon(name))
        if hit:
            return hit
    return None


def find_saami(record, saami):
    for name in record.get("names", []):
        hit = saami.get(canon(name))
        if hit:
            return hit
    return None


def saami_editions(by_id):
    """Return the document identity and edition per SAAMI Z299 part."""
    out = {}
    for sid, src in by_id.items():
        if not sid.startswith("saami_z299_"):
            continue
        part = sid.rsplit("_", 1)[-1]
        title = src.get("title", "")
        year = re.search(r"Z299\.\d-?(\d{4})", title)
        out[part] = {
            "document": src.get("identifier") or title,
            "edition": src.get("edition")
            or src.get("published")
            or (year.group(1) if year else ""),
        }
    return out


# A weapon manual describes a weapon, not the cartridge. A cartridge
# citation is only taken from a source that states a cartridge dimension
# or its pressure.
DEFINITION_FIELDS = {
    "calibre_mm",
    "bore_mm",
    "case_length_mm",
    "max_pressure_mpa",
    "proof_pressure_mpa",
    "pressure_standard",
}

# The research names a military document by its index. A civilian
# handbook or a maker page does not define a service cartridge.
MILITARY_ID = re.compile(r"^(tm|fm|mil|coe|us_|tme)|_tm$|_manual$")

# Where the source locator covers several cartridges, the record states
# the sheet the cartridge itself came from.
LOCATOR_OVERRIDE = {
    "105mm_m68": "M735, M774 and M833 APFSDS-T data sheets; M456 HEAT-T series",
}


def source_edition(src):
    """Return the edition a source states, or the year in its title."""
    stated = src.get("edition") or src.get("published")
    if stated:
        return stated
    year = re.search(r"(Z299\.\d[- ]?(\d{4}))", src.get("title", ""))
    return year.group(1) if year else ""


def source_is_standard(src):
    return src.get("type") == "standard" or (
        src.get("type") == "manual" and src.get("tier", 9) <= 3
    )


def cited_sources(record, by_id, fields=None):
    ids = []
    for field, entry in (record.get("values") or {}).items():
        if fields is not None and field not in fields:
            continue
        if not isinstance(entry, dict):
            continue
        for key in (entry.get("source"), *(entry.get("corroborated_by") or [])):
            if key and key in by_id and key not in ids:
                ids.append(key)
    return ids


def build_entries(record, cip, saami, by_id, editions):
    entries = []
    hit_cip = find_cip(record, cip)
    hit_saami = find_saami(record, saami)
    cited = cited_sources(record, by_id)
    defining = cited_sources(record, by_id, DEFINITION_FIELDS)
    saami_cited = next((s for s in cited if s.startswith("saami_")), None)
    cip_cited = next((s for s in cited if s.startswith("cip_")), None)

    if hit_cip or cip_cited:
        tab, row = hit_cip if hit_cip else (None, None)
        if row:
            entry = {
                "standard": "C.I.P.",
                "document": "TDCC, Tables of Dimensions of Cartridges and Chambers",
                "designation": row["name"],
                "datasheet": Path(row.get("en_pdf") or "").name,
                "edition": f"revision {row['rev']}"
                if row.get("rev")
                else f"registered {row['date']}",
                "locator": tab,
            }
            if row.get("ptmax_bar") is not None:
                entry["max_pressure_mpa"] = round(row["ptmax_bar"] * BAR_TO_MPA, 1)
            entries.append(entry)
        else:
            src = by_id.get(cip_cited, {})
            entries.append(
                {
                    "standard": "C.I.P.",
                    "document": src.get("identifier") or "CIP TDCC",
                    "designation": record.get("names", [""])[0],
                    "datasheet": "",
                    "edition": src.get("edition", ""),
                    "locator": src.get("locator", ""),
                }
            )

    if hit_saami:
        part = str(hit_saami.get("standard", "")).replace("Z299.", "")
        doc = editions.get(part, {})
        entry = {
            "standard": "SAAMI",
            "document": doc.get("document") or f"ANSI/SAAMI Z299.{part}",
            "designation": hit_saami["cartridge"],
            "datasheet": f"Z299.{part} pressure and velocity tables",
            "edition": doc.get("edition", ""),
            "locator": "maximum average pressure table",
            "max_pressure_mpa": hit_saami["map_mpa"],
            "max_pressure_psi": hit_saami["map_psi"],
        }
        entries.append(entry)
    elif record["cartridge_id"] in SAAMI_RIMFIRE or saami_cited:
        sid = saami_cited or "saami_z299_1"
        src = by_id.get(sid, {})
        entries.append(
            {
                "standard": "SAAMI",
                "document": src.get("identifier") or src.get("title", "SAAMI Z299.1"),
                "designation": record.get("names", [""])[0],
                "datasheet": "Z299.1 rimfire pressure and velocity tables",
                "edition": source_edition(src),
                "locator": src.get("locator", "reference twist"),
            }
        )

    for sid in defining:
        if sid.startswith(("cip_", "saami_")):
            continue
        src = by_id[sid]
        if not source_is_standard(src):
            continue
        military = bool(MILITARY_ID.search(sid))
        if not military and not any(w in sid for w in ("nato", "stanag", "aep")):
            continue
        # A military manual is cited only where no civil standard holds
        # the cartridge. A NATO document is cited for the service round
        # even where a civil register holds a relative of it.
        if military and any(e["standard"] in ("C.I.P.", "SAAMI") for e in entries):
            continue
        if any(
            e["document"] == (src.get("identifier") or src.get("title"))
            for e in entries
        ):
            continue
        standard = (
            "NATO"
            if any(w in sid for w in ("nato", "stanag", "aep"))
            else "Military manual"
        )
        entries.append(
            {
                "standard": standard,
                "document": src.get("identifier") or src.get("title", sid),
                "designation": record.get("names", [""])[0],
                "datasheet": src.get("title", ""),
                "edition": source_edition(src),
                "locator": LOCATOR_OVERRIDE.get(record["cartridge_id"])
                or src.get("locator", ""),
            }
        )

    declared = DECLARED_STANDARDS.get(record["cartridge_id"])
    if declared and not any(
        e["document"] == declared["entry"]["document"] for e in entries
    ):
        entries.append(dict(declared["entry"]))

    if not entries:
        return entries
    # One entry is authoritative. C.I.P. is the base register, then
    # SAAMI, then the NATO or military document.
    order = {"C.I.P.": 0, "SAAMI": 1, "NATO": 2, "Military manual": 3}
    entries.sort(key=lambda e: order.get(e["standard"], 9))
    entries[0]["authoritative"] = True
    for e in entries[1:]:
        e["authoritative"] = False
    return entries


def pressure_conflicts(record, entries, existing):
    """Record a SAAMI against C.I.P. pressure disagreement, never average.

    The two bodies measure pressure by different methods, so a difference
    is a property of the standard, not an error to reconcile. A pair that
    already has a conflict row is left as it is.
    """
    cip = next((e for e in entries if e["standard"] == "C.I.P."), None)
    saami = next((e for e in entries if e["standard"] == "SAAMI"), None)
    if not cip or not saami:
        return None
    a = cip.get("max_pressure_mpa")
    b = saami.get("max_pressure_mpa")
    if a is None or b is None:
        return None
    if abs(a - b) <= PRESSURE_TOLERANCE * max(a, b):
        return None
    key = (record["cartridge_id"], "max_pressure_mpa", "cip_tdcc", "saami_pressure")
    if key in existing:
        return None
    return {
        "entity": record["cartridge_id"],
        "field": "max_pressure_mpa",
        "value_a": a,
        "source_a": "cip_tdcc",
        "value_b": b,
        "source_b": "saami_pressure",
        "resolution": "Keep both, keyed by the pressure standard. C.I.P. and SAAMI measure pressure by different methods, so the two values are not comparable and are never averaged.",
        "rule_applied": "Record both. Do not average.",
        "date": "2026-10-23",
    }


def main():
    db = load("cartridges.json")
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    registered = register_declared(sources)
    by_id = {s["source_id"]: s for s in sources}
    cip = cip_index()
    saami = saami_index()
    editions = saami_editions(by_id)
    conflicts = json.loads(CONFLICTS.read_text(encoding="utf-8"))
    seen = {
        (c.get("entity"), c.get("field"), c.get("source_a"), c.get("source_b"))
        for c in conflicts
    }
    added = 0
    counts = {"SAAMI": 0, "C.I.P.": 0, "NATO": 0, "Military manual": 0, "none": 0}
    without = []
    for record in db:
        entries = build_entries(record, cip, saami, by_id, editions)
        record["standards"] = entries
        if not entries:
            counts["none"] += 1
            without.append(record["cartridge_id"])
            continue
        for name in counts:
            if name != "none" and any(e["standard"] == name for e in entries):
                counts[name] += 1
        row = pressure_conflicts(record, entries, seen)
        if row:
            conflicts.append(row)
            seen.add((row["entity"], row["field"], row["source_a"], row["source_b"]))
            added += 1

    DB.write_text(json.dumps(db, indent=1) + "\n", encoding="utf-8")
    CONFLICTS.write_text(json.dumps(conflicts, indent=1) + "\n", encoding="utf-8")
    if registered:
        SOURCES.write_text(json.dumps(sources, indent=1) + "\n", encoding="utf-8")
    write_coverage(db, counts, without)
    print(
        f"citations: {len(db)} cartridges, SAAMI {counts['SAAMI']}, "
        f"C.I.P. {counts['C.I.P.']}, NATO/TM {counts['NATO'] + counts['Military manual']}, "
        f"none {counts['none']}, pressure conflicts added {added}, "
        f"declared sources registered {registered}"
    )


def register_declared(sources):
    """Add the source of a declared standard when the register lacks it."""
    known = {s["source_id"] for s in sources}
    added = 0
    for declared in DECLARED_STANDARDS.values():
        record = declared["source"]
        if record["source_id"] in known:
            continue
        sources.append(dict(record))
        known.add(record["source_id"])
        added += 1
    return added


def write_coverage(db, counts, without):
    lines = [
        "# Cartridge standards coverage",
        "",
        "Generated by `tools/validation/gen_cartridge_citations.py`.",
        "Do not edit by hand.",
        "",
        "| Basis | Cartridges |",
        "|---|---|",
        f"| C.I.P. TDCC | {counts['C.I.P.']} |",
        f"| SAAMI Z299 | {counts['SAAMI']} |",
        f"| NATO or military manual only | {counts['NATO'] + counts['Military manual']} |",
        f"| No held standard | {counts['none']} |",
        f"| Total | {len(db)} |",
        "",
        "A cartridge can cite more than one standard. The counts overlap.",
        "",
        "## No held standard",
        "",
    ]
    if without:
        lines += [f"- `{cid}`" for cid in without]
    else:
        lines.append("None.")
    lines += ["", "## Searches recorded", ""]
    lines += [
        "Each entry records what was searched for a cartridge that no held "
        "standard defines, and what the search returned. An absent pressure "
        "stays absent.",
        "",
    ]
    for cid in sorted(STANDARD_SEARCHES):
        lines.append(f"### `{cid}`")
        lines.append("")
        lines += [f"- {step}" for step in STANDARD_SEARCHES[cid]]
        lines.append("")
    COVERAGE.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
