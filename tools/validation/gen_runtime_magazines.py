#!/usr/bin/env python3
"""Generate the magazine-mass resolver for the load-carriage library.

A magazine is the heaviest repeated item a soldier carries, so the load
model needs its mass. The research data holds the maker-published mass for
76 magazines. A mod classname is matched on two signals the classname
carries: the capacity before "Rnd" (30Rnd) and the chambering token
(556x45). Several magazines can share both, so the table holds the median
of the group and the count, and the resolver returns the median.

The resolver lives in the physiology addon, because the carried load is
its data. The research database is the source of truth.

Run:  python3 tools/validation/gen_runtime_magazines.py
"""

import json
import re
import statistics
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
OUT = (
    Path(__file__).parents[2]
    / "addons/physiology/functions/clothing/fnc_getMagazineMass.sqf"
)

# The capacity tiers, used when the classname states no capacity. The
# values are the median of the published masses for that capacity.
CAPACITY_TIERS = {
    5: 85,
    7: 71,
    10: 85,
    15: 105,
    17: 90,
    20: 113,
    25: 200,
    30: 142,
    40: 187,
    50: 227,
    60: 250,
    75: 300,
    100: 500,
}


def calibre_key(text):
    text = (text or "").lower().replace("\u00d7", "x").replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)", text)
    if match:
        return re.sub(r"[^0-9x]", "", f"{match.group(1)}x{match.group(2)}")
    match = re.search(r"(\d)", text)
    return re.sub(r"[^a-z0-9]", "", text)[:8]


def main():
    source = json.loads(
        (DATA / "sources" / "magazine_mass.json").read_text(encoding="utf-8")
    )
    groups = {}
    for row in source["magazines"]:
        mass = row.get("empty_mass_g")
        if not mass:
            continue
        key = (calibre_key(row.get("chambering", "")), int(row["capacity"]))
        groups.setdefault(key, []).append(float(mass))
    rows = []
    for (calibre, capacity), masses in sorted(groups.items()):
        rows.append(
            [calibre, capacity, round(statistics.median(masses), 1), len(masses)]
        )

    table = ",\n".join('    ["{}", {}, {}, {}]'.format(*row) for row in rows)
    tiers = ",\n".join(
        f"    [{cap}, {mass}]" for cap, mass in sorted(CAPACITY_TIERS.items())
    )
    text = TEMPLATE.replace("__ROWS__", table).replace("__TIERS__", tiers)
    OUT.write_text(text, encoding="utf-8")
    print(
        f"magazine groups: {len(rows)}, wrote {OUT.name} ({OUT.stat().st_size} bytes)"
    )


TEMPLATE = """#include "..\\..\\script_component.hpp"
/*
Magazine mass (the load-carriage library). GENERATED FILE.

This is a runtime projection of the magazine research data under
data/ballistics/. It is written by
tools/validation/gen_runtime_magazines.py and must not be edited by hand.

A mod classname carries two signals: the capacity before "Rnd" and the
chambering token, as in "30Rnd_556x45_Stanag". The table holds the median
of the published masses for each capacity and chambering, so an unknown
magazine still resolves. A classname that states no capacity falls back to
the capacity tier.

Argument:
  0: magazine (STRING, a CfgMagazines classname, default "")

Returns the empty magazine mass in kg, or 0 when nothing matches.
*/

params [["_magazine", "", [""]]];
if (_magazine == "") exitWith { 0 };

private _lower = toLower _magazine;

// The capacity: the digits that precede "rnd".
private _capacity = 0;
private _marker = _lower find "rnd";
if (_marker > 0) then {
    private _digits = "";
    private _index = _marker - 1;
    while {_index >= 0} do {
        private _character = _lower select [_index, 1];
        if !(_character in "0123456789") exitWith {};
        _digits = _character + _digits;
        _index = _index - 1;
    };
    if (_digits != "") then { _capacity = parseNumber _digits; };
};

// [chambering token, capacity, empty mass g, published count]
private _TABLE = [
__ROWS__
];

private _match = 0;
{
    _x params ["_calibre", "_cap", "_mass"];
    if ((_lower find _calibre >= 0) && _cap == _capacity) exitWith {
        _match = _mass;
    };
} forEach _TABLE;

if (_match == 0 && _capacity == 0) then {
    // No capacity stated: the first row for the chambering. A stated
    // capacity that the table lacks falls through to the tier instead,
    // so a 75 round magazine never takes a 30 round mass.
    {
        _x params ["_calibre", "_cap", "_mass"];
        if (_lower find _calibre >= 0) exitWith { _match = _mass; };
    } forEach _TABLE;
};

if (_match == 0) then {
    // The capacity tier.
    private _tiers = [
__TIERS__
    ];
    {
        _x params ["_cap", "_mass"];
        if (_cap == _capacity) exitWith { _match = _mass; };
    } forEach _tiers;
};

if (_match == 0) exitWith { 0 };
_match / 1000
"""


if __name__ == "__main__":
    main()
