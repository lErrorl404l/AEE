#!/usr/bin/env python3
"""Derive a missing ballistic coefficient from the other drag model.

The relationship is exact at one Mach number. The ballistic coefficient
against standard x is  BC_x = SD * Cd_x(M) / Cd_bullet(M), so the ratio
of two coefficients is the ratio of the two standard drag curves at the
same Mach:

    BC_G7 = BC_G1 * (Cd_G7(M) / Cd_G1(M))

The derived value is valid near the reference Mach only, because a
bullet's form factor varies with Mach. It is therefore stored at grade
derived with the formula and the reference Mach recorded, never as a
measured or claimed value.

Run after gen_bc_corroboration.py:
  python3 tools/validation/gen_derived_bc.py
"""

import json
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources"
DB = DATA / "projectiles.json"
REFERENCE_MACH = 2.0


def cd_at(points, mach):
    pts = sorted((p["mach"], p["cd"]) for p in points)
    if mach <= pts[0][0]:
        return pts[0][1]
    if mach >= pts[-1][0]:
        return pts[-1][1]
    for (m0, c0), (m1, c1) in zip(pts, pts[1:]):
        if m0 <= mach <= m1:
            t = (mach - m0) / (m1 - m0) if m1 > m0 else 0.0
            return c0 + t * (c1 - c0)
    return pts[-1][1]


def main():
    models = json.loads((SRC / "drag_functions.json").read_text(encoding="utf-8"))[
        "models"
    ]
    cd1 = cd_at(models["G1"], REFERENCE_MACH)
    cd7 = cd_at(models["G7"], REFERENCE_MACH)
    ratio_g7_from_g1 = cd7 / cd1
    db = json.loads(DB.read_text(encoding="utf-8"))
    derived = 0
    for rec in db:
        values = rec["values"]
        formula = (
            f"BC_other = BC * Cd_other(Mach {REFERENCE_MACH:g}) / "
            f"Cd_given(Mach {REFERENCE_MACH:g}); valid near Mach "
            f"{REFERENCE_MACH:g}"
        )
        # Derivation is the last resort: it runs only when no real
        # coefficient of either model is held, so a derived value can
        # never displace a found one.
        have_real = any(
            values.get(f) is not None and values[f].get("grade") != "derived"
            for f in ("bc_g1", "bc_g7")
        )
        if have_real:
            continue
        if "bc_g1" in values and "bc_g7" not in values:
            values["bc_g7"] = {
                "value": round(values["bc_g1"]["value"] * ratio_g7_from_g1, 4),
                "formula": formula.replace("BC_other", "BC_G7")
                .replace("Cd_other", "Cd_G7")
                .replace("Cd_given", "Cd_G1"),
                "source": "drag_functions",
                "grade": "derived",
            }
            derived += 1
        elif "bc_g7" in values and "bc_g1" not in values:
            values["bc_g1"] = {
                "value": round(values["bc_g7"]["value"] / ratio_g7_from_g1, 4),
                "formula": formula.replace("BC_other", "BC_G1")
                .replace("Cd_other", "Cd_G1")
                .replace("Cd_given", "Cd_G7"),
                "source": "drag_functions",
                "grade": "derived",
            }
            derived += 1
    DB.write_text(json.dumps(db, indent=1) + "\n", encoding="utf-8")
    print(
        f"converted coefficients: {derived} (G1 and G7 curve ratio at Mach "
        f"{REFERENCE_MACH:g} = {ratio_g7_from_g1:.4f})"
    )


if __name__ == "__main__":
    main()
