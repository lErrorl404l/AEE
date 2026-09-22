#!/usr/bin/env python3
"""Generate the runtime drag tables from the held set.

Every standard drag function the database holds is projected into one
generated function that builds a name to table map once and returns it.
The kernel then does a single hash lookup, so the tables are never
rebuilt on a shot.

Run:  python3 tools/validation/gen_runtime_drag.py
"""

import json
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
SRC = DATA / "sources" / "drag_functions.json"
OUT = Path(__file__).parents[2] / "addons/ballistics/functions/fnc_getDragTables.sqf"

HEADER = """#include "..\\script_component.hpp"
/*
Standard drag tables (issue #167).

GENERATED from data/ballistics/sources/drag_functions.json by
tools/validation/gen_runtime_drag.py. Do not edit by hand.

Every standard drag function the database holds, as Cd against Mach. The
map is built once and cached, because the drag kernel calls this on the
projectile path.

Returns a HashMap of model name to an array of [mach, cd] pairs.
*/
private _tables = missionNamespace getVariable [QGVAR(dragTables), nil];
if (isNil "_tables") then {
    _tables = createHashMapFromArray [
"""

FOOTER = """    ];
    missionNamespace setVariable [QGVAR(dragTables), _tables];
};
_tables
"""


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    models = data["models"]
    blocks = []
    for name in sorted(models):
        points = models[name]
        rows = []
        for i in range(0, len(points), 4):
            chunk = points[i : i + 4]
            rows.append(
                "            "
                + ", ".join(f"[{p['mach']:.3f}, {p['cd']:.4f}]" for p in chunk)
            )
        blocks.append(f'        ["{name}", [\n' + ",\n".join(rows) + "\n        ]]")
    OUT.write_text(HEADER + ",\n".join(blocks) + FOOTER, encoding="utf-8")
    print(
        f"drag models generated: {len(models)} "
        f"({', '.join(sorted(models))}), wrote {OUT.name} "
        f"({OUT.stat().st_size} bytes)"
    )


if __name__ == "__main__":
    main()
