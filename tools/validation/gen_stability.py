#!/usr/bin/env python3
"""Compute the required twist from the bullet geometry.

A bullet whose maker publishes no minimum twist still has a real
stability requirement, and the Miller twist rule computes it from the
bullet's own mass, diameter and length. That is physics from measured
geometry, not a guess:

    T = sqrt(30 m / (SG * L * (1 + (L/d)^2)))     at SG = 1.5

m is in grains, T and L in inches, d in inches. The rule is shape-blind:
its denominator assumes a boat tail, so a flat base bullet needs a
slightly faster twist than the result states.

Run after gen_derived_bc.py has been replaced by real values:
  python3 tools/validation/gen_stability.py
"""

import json
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
DB = DATA / "projectiles.json"
GRAIN_TO_G = 0.06479891
SG_TARGET = 1.5
FORMULA = (
    "T = sqrt(30 m / (SG L (1 + (L/d)^2))) at SG=1.5; "
    "Miller twist rule; shape-blind, assumes a boat tail"
)


def main():
    db = json.loads(DB.read_text(encoding="utf-8"))
    computed = 0
    for rec in db:
        values = rec["values"]
        if not all(k in values for k in ("mass_g", "diameter_mm", "length_mm")):
            continue
        mass_gr = values["mass_g"]["value"] / GRAIN_TO_G
        diameter_in = values["diameter_mm"]["value"] / 25.4
        length_in = values["length_mm"]["value"] / 25.4
        ratio = length_in / diameter_in
        twist_in = (30 * mass_gr / (SG_TARGET * length_in * (1 + ratio * ratio))) ** 0.5
        values["required_twist_m"] = {
            "value": round(twist_in * 0.0254, 4),
            "unit": "m per turn",
            "formula": FORMULA,
            "source": "miller_rule",
            "grade": "derived",
        }
        computed += 1
    DB.write_text(json.dumps(db, indent=1) + "\n", encoding="utf-8")
    print(f"required twist computed from geometry: {computed}")


if __name__ == "__main__":
    main()
