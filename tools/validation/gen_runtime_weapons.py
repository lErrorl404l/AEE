#!/usr/bin/env python3
"""Generate the runtime weapon resolver from the weapon catalogue.

The weapon layer holds one datum: the rifling twist. The resolver matches
a weapon identity and returns that weapon's own barrel properties, so a
rifle whose barrel differs from the cartridge standard (an M24 at 1:11.2
against an M14 at 1:12) is resolved correctly.

The twist is used with the muzzle velocity to give the spin rate:

    omega = 2 pi v / T

Run:  python3 tools/validation/gen_runtime_weapons.py
"""

import json
import re
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
DB = DATA / "weapons.json"
OUT = Path(__file__).parents[2] / "addons/ballistics/functions/fnc_getWeaponData.sqf"

MIN_ALIAS = 3
SCAN_ALIAS = 4


def row(rec):
    aliases = {a for a in rec.get("aliases", []) if len(a) >= MIN_ALIAS}
    if not aliases:
        return None
    values = rec["values"]

    def val(field, default=0):
        entry = values.get(field)
        return entry["value"] if entry else default

    return [
        rec["weapon_id"],
        "|".join(sorted(aliases)),
        val("twist_m"),
        val("grooves"),
        rec.get("cartridge_id", ""),
        val("mass_kg"),
    ]


TEMPLATE = """#include "..\\script_component.hpp"
/*
Weapon resolver (issue #167).

Resolves a weapon to its own barrel properties. This file is a GENERATED
runtime projection of the weapon catalogue under data/ballistics/. It is
written by tools/validation/gen_runtime_weapons.py and must not be edited
by hand.

Only the rifling twist is stored per weapon. The barrel length is measured
from the model, and the cartridge comes from the ammunition. A weapon
that the catalogue does not hold returns an empty array, and the caller
then uses the cartridge standard twist, so nothing is unsupported.

Returns [weapon_id, twist_m, grooves, cartridge_id, mass_kg], or an empty
array. The mass is the maker's published mass of the weapon, and a zero
means it is not held.

Arguments:
  0: weapon (STRING, the CfgWeapons classname, default "")
*/
params [["_weapon", "", [""]]];
if (_weapon == "") exitWith { [] };

private _cache = missionNamespace getVariable [QGVAR(weaponCache), nil];
if (isNil "_cache") then {
    _cache = createHashMap;
    missionNamespace setVariable [QGVAR(weaponCache), _cache];
};
private _cached = _cache getOrDefault [_weapon, []];
if (_cached isNotEqualTo []) exitWith { _cached };

private _normalise = {
    params ["_text"];
    private _out = "";
    {
        if ((_x >= 48 && _x <= 57) || (_x >= 97 && _x <= 122)) then {
            _out = _out + toString [_x];
        };
    } forEach (toArray (toLower _text));
    _out
};

// ─── The weapon table ────────────────────────────────────────────────────
// [id, aliases, twist m per turn, grooves, cartridge id, mass kg]
private _TABLE = [
__ROWS__
];

private _index = missionNamespace getVariable [QGVAR(weaponIndex), nil];
if (isNil "_index" || {(count _index) == 0}) then {
    _index = createHashMap;
    {
        _x params ["_id", "_aliases", "_twist", "_grooves", "_cartridge", "_mass"];
        {
            if ((_index getOrDefault [_x, []]) isEqualTo []) then {
                _index set [_x, [_id, _twist, _grooves, _cartridge, _mass, count _x]];
            };
        } forEach (_aliases splitString "|");
    } forEach _TABLE;
    missionNamespace setVariable [QGVAR(weaponIndex), _index];
};

// The query: the classname plus the readable name from CfgWeapons.
private _name = getText (configFile >> "CfgWeapons" >> _weapon >> "displayName");
private _query = [_weapon + " " + _name] call _normalise;

private _match = [];
private _bestLen = 0;
{
    private _hit = _index getOrDefault [_x, []];
    if ((_hit isNotEqualTo []) && {(_hit select 5) > _bestLen}) then {
        _match = _hit;
        _bestLen = _hit select 5;
    };
} forEach (toLower (_weapon + " " + _name) splitString "_- .");

if (_match isEqualTo []) then {
    {
        _x params ["_id", "_aliases", "_twist", "_grooves", "_cartridge", "_mass"];
        private _list = _aliases splitString "|";
        private _rowLen = 0;
        for "_i" from 0 to ((count _list) - 1) do {
            private _alias = _list select _i;
            if (_alias != "" && {count _alias >= __SCAN__} && {_query find _alias >= 0} && {count _alias > _rowLen}) then {
                _rowLen = count _alias;
            };
        };
        if (_rowLen > _bestLen) then {
            _match = [_id, _twist, _grooves, _cartridge, _mass];
            _bestLen = _rowLen;
        };
    } forEach _TABLE;
};

private _result = if (_match isEqualTo []) then { [] } else {
    [_match select 0, _match select 1, _match select 2, _match select 3,
     _match select 4]
};
_cache set [_weapon, _result];
_result
"""


def main():
    db = json.loads(DB.read_text(encoding="utf-8"))
    rows = [r for r in (row(rec) for rec in db) if r]
    rows.sort(key=lambda r: r[0])
    body = ",\n".join(
        '    ["{}", "{}", {}, {}, "{}", {}]'.format(*r) for r in rows)
    text = TEMPLATE.replace("__ROWS__", body).replace("__SCAN__", str(SCAN_ALIAS))
    OUT.write_text(text, encoding="utf-8")
    print(f"weapon rows: {len(rows)}, wrote {OUT.name} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
