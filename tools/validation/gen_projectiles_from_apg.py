#!/usr/bin/env python3
"""Add the military service bullets from the Aberdeen Proving Ground list.

The list states a measured G7 coefficient and the bullet mass for the US
service bullets, so the vanilla chamberings get a real bullet instead of
none. The coefficient is a measurement. The mass and the diameter are
stated by the source.

Run after gen_projectiles.py:
  python3 tools/validation/gen_projectiles_from_apg.py
"""

import json
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources" / "apg_litz_g7.json"
DB = DATA / "projectiles.json"
GRAIN_TO_G = 0.06479891
PREFIX = "apg_"


def main():
    src = json.loads(SRC.read_text(encoding="utf-8"))
    db = json.loads(DB.read_text(encoding="utf-8"))
    existing = {r["projectile_id"] for r in db}
    added = 0
    for b in src["bullets"]:
        if b["manufacturer"] != "APG G7":
            continue
        design = b["designation"].strip()
        pid = PREFIX + design.lower().replace(" ", "_")
        if pid in existing:
            continue
        diameter_in = b["diameter_in"]
        sd = (b["mass_gr"] / 7000) / (diameter_in**2)
        db.append(
            {
                "projectile_id": pid,
                "names": [design, f"{b['mass_gr']:g} gr {design}"],
                "manufacturer": "US military",
                "note": "Aberdeen Proving Ground measured G7 coefficient.",
                "values": {
                    "mass_g": {
                        "value": round(b["mass_gr"] * GRAIN_TO_G, 4),
                        "unit": "g",
                        "source": "apg_litz_g7",
                        "grade": "documented",
                    },
                    "diameter_mm": {
                        "value": round(diameter_in * 25.4, 4),
                        "unit": "mm",
                        "source": "apg_litz_g7",
                        "grade": "documented",
                    },
                    "bc_g7": {
                        "value": b["bc_g7"],
                        "source": "apg_litz_g7",
                        "grade": "measured",
                    },
                    "drag_model": {
                        "value": "G7",
                        "source": "apg_litz_g7",
                        "grade": "documented",
                    },
                    "sectional_density": {
                        "value": round(sd, 4),
                        "formula": "SD = (mass_gr / 7000) / (diameter_in ^ 2)",
                        "source": "apg_litz_g7",
                        "grade": "derived",
                    },
                },
            }
        )
        added += 1
    db.sort(key=lambda r: r["projectile_id"])
    DB.write_text(json.dumps(db, indent=1) + "\n", encoding="utf-8")
    print(f"projectiles: {len(db)} (military bullets added: {added})")


if __name__ == "__main__":
    main()
