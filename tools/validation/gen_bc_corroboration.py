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
    corroborated = 0
    disagreements = 0
    for rec in db:
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
                else:
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
    print(
        f"coefficients corroborated: {corroborated}, disagreements recorded: {disagreements}"
    )


if __name__ == "__main__":
    main()
