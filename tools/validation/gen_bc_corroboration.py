#!/usr/bin/env python3
"""Corroborate projectile ballistic coefficients against measurements.

Two independent measured sources are matched to each projectile. The
match must be strong: same manufacturer, same bullet diameter, mass
inside one percent, and a shared name token. A weak match is skipped,
because two different bullets of the same weight would otherwise be
compared and produce a false disagreement.

Inside the ADR tolerance the coefficient is raised to grade
corroborated. Outside it the disagreement is recorded as a conflict, and
the manufacturer value is kept, never averaged.

Run after gen_projectiles.py:
  python3 tools/validation/gen_bc_corroboration.py
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
DB = DATA / "projectiles.json"
CONFLICTS = DATA / "conflicts.json"
BASIS = DATA / "BC_BASIS.md"

# What each independent source is, in one line. A reader needs to know
# whether the measurement behind a coefficient is a range firing or a
# compilation of one.
MEASUREMENT_SOURCES = {
    "apg_litz_g7": (
        "G7 and G8 coefficient list compiled from Aberdeen Proving Ground "
        "data, Shooting Lab conversions and the work of Brian Litz. The "
        "compiling page states the three origins and does not separate "
        "them per row."
    ),
    "litz_dfrl": (
        "US Air Force Academy research report that compares advertised "
        "coefficients against measured ones, published as DTIC "
        "ADA554683. The measured column is a Doppler-radar measurement."
    ),
}

# The searches made for a further independent source, and what each
# returned. A blocked source is named, and its numbers are not entered.
SEARCHES = [
    (
        "DTIC and the Internet Archive DTIC mirror, US Army free-flight and "
        "spark-range reports",
        "Held reports such as ARL-TR-5182 (Silton and Howell, May 2010, "
        "ADA530895, M855) tabulate the zero-yaw axial force coefficient "
        "against Mach, not a ballistic coefficient. A coefficient would "
        "have to be derived by fitting the measured curve to the G7 "
        "standard, so the value would be derived, not measured. Not entered.",
    ),
    (
        "Applied Ballistics, Ballistic Performance of Rifle Bullets, and the "
        "Applied Ballistics software library",
        "Copyrighted commercial work. The library held at version 925 is an "
        "index with no coefficients. The measured coefficients are the "
        "author's paid tables, so they are not redistributed and the basis "
        "is not raised from them.",
    ),
    (
        "NATO RTO and AGARD technical reports",
        "No report found that tabulates measured projectile drag for "
        "small-arms bullets. The AGARD flight-test series covers weapon "
        "delivery, not bullet coefficients.",
    ),
    (
        "Open-access journals and conference proceedings",
        "Found suppressor and interior-ballistics studies, no tabulated "
        "measured coefficient for a bullet this corpus holds.",
    ),
]
GRAIN_TO_G = 0.06479891
TOLERANCE = 0.02
MASS_TOLERANCE = 0.01
BRANDS = {"Berger", "Hornady", "Sierra", "Nosler", "Lapua", "Barnes"}
STOP = {"cal", "gr", "grain", "grains", "bullet", "bullets", "match", "the", "and"}
ALIAS = {
    "smk": "matchking",
    "bt": "ballistictip",
    "bsp": "spitzer",
    "vld": "vld",
    "hybrid": "hybrid",
    "otm": "otm",
    "rdf": "rdf",
}


def load(name):
    return json.loads((SRC / f"{name}.json").read_text(encoding="utf-8"))


def tokens(text):
    out = set()
    for t in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if len(t) < 3 or t in STOP:
            continue
        out.add(ALIAS.get(t, t))
    return out


def build_index():
    index = {}
    for b in load("apg_litz_g7")["bullets"]:
        maker = b["manufacturer"] if b["manufacturer"] in BRANDS else None
        index.setdefault(round(b["diameter_in"], 3), []).append(
            {
                "source": "apg_litz_g7",
                "maker": maker,
                "mass_gr": b["mass_gr"],
                "designation": b["designation"],
                "bc_g7": b["bc_g7"],
            }
        )
    for b in load("litz_dfrl")["bullets"]:
        maker = b.get("brand") if b.get("brand") in BRANDS else None
        index.setdefault(round(b["diameter_in"], 3), []).append(
            {
                "source": "litz_dfrl",
                "maker": maker,
                "mass_gr": b["mass_gr"],
                "designation": b["style"],
                "bc_g1": b["litz_g1"],
                "bc_g7": b["litz_g7"],
            }
        )
    return index


def candidates(rec, index):
    values = rec["values"]
    diameter = values.get("diameter_mm", {}).get("value")
    mass = values.get("mass_g", {}).get("value")
    if diameter is None or mass is None:
        return []
    mass_gr = mass / GRAIN_TO_G
    maker = rec.get("manufacturer", "")
    ours = tokens(" ".join(rec.get("names", [])))
    out = []
    for c in index.get(round(diameter / 25.4, 3), []):
        if c["maker"] and c["maker"].lower() != maker.lower():
            continue
        if abs(c["mass_gr"] - mass_gr) > MASS_TOLERANCE * mass_gr:
            continue
        # Strong identity: the designations share a name token.
        if not (ours & tokens(c["designation"])):
            continue
        out.append(c)
    return out


def natural_grade(source_id, sources):
    """The grade a value carries from its own source alone."""
    src = sources.get(source_id, {})
    if src.get("tier") == 1:
        return "standard"
    if src.get("tier") == 2:
        return "documented"
    if src.get("type") == "measurement" or src.get("tier") == 3:
        return "measured"
    return "claimed"


def main():
    db = json.loads(DB.read_text(encoding="utf-8"))
    sources = {
        s["source_id"]: s
        for s in json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    }
    index = build_index()
    projectiles = [r["projectile_id"] for r in db]
    conflicts = [
        c
        for c in json.loads(CONFLICTS.read_text(encoding="utf-8"))
        if c.get("entity") not in projectiles
    ]
    recorded = {
        (c.get("entity"), c.get("field"), c.get("value_a"), c.get("value_b"))
        for c in conflicts
    }
    corroborated = 0
    disagreements = 0
    for rec in db:
        # Every coefficient states the model it was measured against and
        # the basis it rests on. A measured source is independent; every
        # other source is a maker claim, and says so.
        for field, model in (("bc_g1", "G1"), ("bc_g7", "G7")):
            entry = rec["values"].get(field)
            if entry is None or entry.get("drag_model"):
                continue
            src = sources.get(entry.get("source"), {})
            entry["drag_model"] = model
            entry["basis"] = (
                "independent_measurement"
                if src.get("type") == "measurement"
                else "maker_published_secondary"
            )
            entry["edition"] = src.get("edition") or src.get("published", "")
        # Clear any corroboration from an earlier run, so a grade can
        # never persist after the evidence behind it changed.
        for field in ("bc_g1", "bc_g7"):
            entry = rec["values"].get(field)
            if entry is not None and "corroborated_by" in entry:
                del entry["corroborated_by"]
                entry["grade"] = natural_grade(entry.get("source", ""), sources)
        for candidate in candidates(rec, index):
            for field in ("bc_g1", "bc_g7"):
                entry = rec["values"].get(field)
                measured = candidate.get(field)
                if not entry or measured is None:
                    continue
                # A value cannot corroborate itself. The candidate must
                # come from a different source than the value it checks.
                if candidate["source"] == entry.get("source"):
                    continue
                diff = abs(measured - entry["value"]) / entry["value"]
                if diff <= TOLERANCE:
                    entry["grade"] = "corroborated"
                    entry.setdefault("corroborated_by", [])
                    if candidate["source"] not in entry["corroborated_by"]:
                        entry["corroborated_by"].append(candidate["source"])
                    corroborated += 1
                elif (
                    rec["projectile_id"],
                    field,
                    entry["value"],
                    measured,
                ) not in recorded:
                    recorded.add(
                        (rec["projectile_id"], field, entry["value"], measured)
                    )
                    conflicts.append(
                        {
                            "entity": rec["projectile_id"],
                            "field": field,
                            "value_a": entry["value"],
                            "source_a": entry["source"],
                            "value_b": measured,
                            "source_b": candidate["source"],
                            "resolution": "Kept the manufacturer value. Recorded the measured value.",
                            "rule_applied": "Record both. Do not average.",
                            "date": "2026-09-22",
                        }
                    )
                    disagreements += 1
    DB.write_text(json.dumps(db, indent=1) + "\n", encoding="utf-8")
    CONFLICTS.write_text(json.dumps(conflicts, indent=1) + "\n", encoding="utf-8")
    basis = write_basis_report(db, sources)
    print(
        f"coefficients corroborated: {corroborated}, disagreements recorded: {disagreements}, "
        f"basis: {basis['independent_measurement']} independent, "
        f"{basis['maker_published_secondary']} maker published"
    )


def write_basis_report(db, sources):
    """Write the basis split, and what stops the independent basis rising.

    A count on its own invites a reader to treat every coefficient alike.
    The report states which source stands behind each one, which bullets
    an independent measurement reaches, and which searches for a further
    source returned nothing usable.
    """
    counts = {"independent_measurement": 0, "maker_published_secondary": 0}
    per_source = {}
    without_g7 = 0
    for rec in db:
        for field in ("bc_g1", "bc_g7"):
            entry = rec["values"].get(field)
            if not isinstance(entry, dict) or not entry.get("basis"):
                continue
            counts[entry["basis"]] = counts.get(entry["basis"], 0) + 1
            key = (entry.get("source", ""), field)
            per_source[key] = per_source.get(key, 0) + 1
        if "bc_g7" not in rec["values"] and "bc_g1" in rec["values"]:
            without_g7 += 1
    total = sum(counts.values())
    lines = [
        "# Ballistic coefficient basis",
        "",
        "Generated by `tools/validation/gen_bc_corroboration.py`.",
        "Do not edit by hand.",
        "",
        "| Basis | Coefficients |",
        "|---|---|",
        f"| independent_measurement | {counts['independent_measurement']} |",
        f"| maker_published_secondary | {counts['maker_published_secondary']} |",
        f"| Total | {total} |",
        "",
        "A coefficient is independent when its source measured the drag by "
        "firing. Every other coefficient is a maker claim, including a maker "
        "claim that states a G7 model.",
        "",
        "## What stands behind each coefficient",
        "",
        "| Source | Model | Tier | Type | Licence | Basis | Coefficients |",
        "|---|---|---|---|---|---|---|",
    ]
    for (sid, field), count in sorted(per_source.items(), key=lambda kv: -kv[1]):
        src = sources.get(sid, {})
        model = "G7" if field == "bc_g7" else "G1"
        basis = (
            "independent_measurement"
            if src.get("type") == "measurement"
            else "maker_published_secondary"
        )
        lines.append(
            f"| {sid} | {model} | {src.get('tier', '')} | {src.get('type', '')} "
            f"| {src.get('licence', '')} | {basis} | {count} |"
        )
    lines += ["", "## The independent sources", ""]
    for sid in sorted({sid for sid, _ in per_source}):
        if sources.get(sid, {}).get("type") != "measurement":
            continue
        src = sources[sid]
        note = MEASUREMENT_SOURCES.get(sid, "")
        lines.append(
            f"- `{sid}`: {src.get('title', '')}. Edition {src.get('edition', '')}."
        )
        if note:
            lines.append(f"  {note}")
    lines += [
        "",
        "## Reach of the independent basis",
        "",
        f"{without_g7} projectiles carry a maker coefficient and no measured "
        "G7 coefficient. They are the commercial hunting and match bullets. "
        "No held measurement covers them.",
        "",
        "## Searches for a further independent source",
        "",
    ]
    for searched, result in SEARCHES:
        lines.append(f"- Searched {searched}. {result}")
    BASIS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return counts


if __name__ == "__main__":
    main()
