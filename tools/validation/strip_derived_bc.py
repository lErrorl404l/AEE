#!/usr/bin/env python3
"""Remove derived coefficients from the projectile records.

A coefficient computed from the other drag standard is not a found value.
Derivation remains available as an explicit tool, but the database holds
only real values, so nothing speculative can reach the simulation.

Run after gen_bc_corroboration.py:
  python3 tools/validation/strip_derived_bc.py
"""

import json
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
DB = DATA / "projectiles.json"


def main():
    db = json.loads(DB.read_text(encoding="utf-8"))
    removed = 0
    for rec in db:
        for field in ("bc_g1", "bc_g7"):
            entry = rec["values"].get(field)
            if entry is not None and entry.get("grade") == "derived":
                del rec["values"][field]
                removed += 1
    DB.write_text(json.dumps(db, indent=1) + "\n", encoding="utf-8")
    print(f"derived coefficients removed: {removed}")


if __name__ == "__main__":
    main()
