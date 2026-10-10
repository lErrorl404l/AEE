#!/usr/bin/env python3
"""Generate the runtime fuel and coolant constant table from the corpus.

The corpus is ``data/physics/fuel.json`` (schema ``aee.physics.fuel/1``). The
generator projects it to ``addons/vehicles/functions/fnc_getFuelData.sqf``, a
pure lookup that returns a hashmap of the engine classes, the fuels, the
rolling-resistance anchors, the terrain multipliers and the thermal
constants. The runtime never reads the corpus: it reads the generated table.

The generator refuses to emit a corpus that does not validate, so the runtime
can never hold a value the validator would reject.

Run:
    python3 tools/gen_fuel_data.py
    python3 tools/gen_fuel_data.py --check
Exit 0 when fresh, 1 when stale or missing under --check.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.validation import validate_fuel_data as validator  # noqa: E402

DATA = REPO / "data" / "physics" / "fuel.json"
OUT = REPO / "addons" / "vehicles" / "functions" / "fnc_getFuelData.sqf"

HEADER = """#include "..\\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_fuel_data.py

The runtime fuel and coolant constant table (issue #111), projected from
data/physics/fuel.json by tools/gen_fuel_data.py. The corpus is the only home
for a value; this table is the runtime projection. The generator refuses a
corpus that does not validate, so no value here can be one the validator would
reject.

Sections, each a hashmap:
  engine_classes      id -> [bsfc_g_kwh, fuel_id]
  fuels               id -> [density_g_l, lhv_mj_kg]
  rolling_resistance  id -> crr
  terrain_multipliers ground_state -> multiplier
  thermal             id -> value

Arguments: none.
Return Value: HASHMAP - the five sections.
Public: No
*/

private _table = createHashMapFromArray [
"""

FOOTER = """];

_table
"""


def _num(value) -> str:
    """Emit a JSON number as an SQF literal, keeping its written precision."""
    if isinstance(value, bool):
        raise TypeError("a boolean is not a numeric constant")
    if isinstance(value, int):
        return f"{value}.0"
    text = repr(float(value))
    return text


def _entries(pairs) -> list[str]:
    lines = [f'        ["{key}", {val}],' for key, val in pairs]
    if lines:
        lines[-1] = lines[-1].rstrip(",")
    return lines


def render(data: dict) -> str:
    lines: list[str] = [HEADER.rstrip("\n")]

    engine = [
        (c["id"], f'[{_num(c["bsfc_g_kwh"])}, "{c["fuel"]}"]')
        for c in data["engine_classes"]
    ]
    fuels = [
        (f["id"], f"[{_num(f['density_g_l'])}, {_num(f['lhv_mj_kg'])}]")
        for f in data["fuels"]
    ]
    rolling = [(r["id"], _num(r["crr"])) for r in data["rolling_resistance"]]
    terrain = [(t["id"], _num(t["multiplier"])) for t in data["terrain_multipliers"]]
    thermal = [(t["id"], _num(t["value"])) for t in data["thermal"]]

    for name, pairs in (
        ("engine_classes", engine),
        ("fuels", fuels),
        ("rolling_resistance", rolling),
        ("terrain_multipliers", terrain),
        ("thermal", thermal),
    ):
        lines.append(f'    ["{name}", createHashMapFromArray [')
        lines.extend(_entries(pairs))
        lines.append("    ]],")

    # The final section closes with the outer array; drop the trailing comma.
    lines[-1] = lines[-1].rstrip(",")
    return "\n".join(lines) + "\n" + FOOTER


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    check = "--check" in args

    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"gen_fuel_data: FAIL\n  cannot read {DATA}: {exc}")
        return 1

    errors = validator.validate(data)
    if errors:
        print("gen_fuel_data: FAIL (the corpus does not validate)")
        for error in errors:
            print(f"  {error}")
        return 1

    rendered = render(data)

    if check:
        existing = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if existing != rendered:
            print(f"gen_fuel_data: STALE {OUT} (run: python3 tools/gen_fuel_data.py)")
            return 1
        print(f"gen_fuel_data: fresh {OUT}")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(rendered, encoding="utf-8")
    print(f"gen_fuel_data: wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
