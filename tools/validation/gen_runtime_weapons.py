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
import sys
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
DB = DATA / "weapons.json"
OUT = Path(__file__).parents[2] / "addons/ballistics/functions/fnc_getWeaponData.sqf"
BANDS_OUT = (
    Path(__file__).parents[2] / "addons/ballistics/functions/fnc_getWeaponBands.sqf"
)

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


def band_row(rec):
    """Return one property-band row, or None when the record has no identity.

    The band is the fallback of the weapon resolver. A row carries the
    chambering (the discrete token), the maker's published mass (the primary
    selector), and the twist and groove count as the payload. A missing
    number is a labelled zero.
    """
    weapon_id = rec.get("weapon_id")
    if not weapon_id:
        return None
    values = rec.get("values", {})

    def val(field, default=0):
        entry = values.get(field)
        return entry["value"] if entry else default

    return [
        weapon_id,
        rec.get("cartridge_id", "") or "",
        val("mass_kg"),
        val("twist_m"),
        val("grooves"),
    ]


def band_rows(db):
    """Build every band row and sort it by weapon id."""
    rows = [r for r in (band_row(rec) for rec in db) if r]
    rows.sort(key=lambda r: r[0])
    return rows


BAND_TEMPLATE = """#include "..\\script_component.hpp"
/*
Weapon identity band table.

This file is GENERATED. The generator tools/validation/gen_runtime_weapons.py
writes it from the weapon catalogue under data/ballistics/. Do not edit it
by hand. Edit the corpus and regenerate it.

The band table is the property fallback of the weapon resolver. A weapon
whose identity text resolves to no catalogue alias is matched by its own
chambering and its engine weapon mass. The chambering is the token, the
published mass is the primary selector, and the twist and groove count are
the payload. The selector reads the table and the live properties only. The
engine mass is an identity signal, never a value source.

A row has five columns:

  0 weapon_id     string, the stable catalogue key
  1 cartridge_id  string, the chambering, the discrete token
  2 mass_kg       number, the published weapon mass in kg, 0 absent
  3 twist_m       number, the rifling twist in metres per turn, 0 absent
  4 grooves       number, the groove count, 0 absent

Returns the band table, one row per weapon entry, sorted by weapon id.

Arguments: none.
Public: No
*/

private _table = [
__ROWS__
];

_table
"""


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

// Identity text only: the classname, the raw display name and its localised
// stringtable text. A vanilla class stores a $STR key in displayName, so all
// three are needed. None carries a figure.
private _rawName = getText (configFile >> "CfgWeapons" >> _weapon >> "displayName");
private _localName = if (_rawName == "") then { "" } else { localize _rawName };
private _identity = _weapon + " " + _rawName + " " + _localName;
private _query = [_identity] call _normalise;

private _match = [];
private _bestLen = 0;
{
    private _hit = _index getOrDefault [_x, []];
    if ((_hit isNotEqualTo []) && {(_hit select 5) > _bestLen}) then {
        _match = _hit;
        _bestLen = _hit select 5;
    };
} forEach (toLower _identity splitString "_- .");

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

// ─── Band: the live chambering and engine mass ───────────────────────────
// A class whose identity text resolves to no catalogue alias is matched by
// its own properties. The chambering is the cartridge its first magazine
// fires, read through the cartridge resolver; the mass is the engine's own
// weapon mass. Both are identity signals, never a value source. A miss is
// an empty array, and the caller then falls back to the cartridge standard,
// exactly as before.
if (_match isEqualTo []) then {
    private _cartridgeKey = "";
    {
        private _ammo = getText (configFile >> "CfgMagazines" >> _x >> "ammo");
        if (_ammo != "") exitWith {
            private _cart = [_ammo] call FUNC(getCartridgeData);
            if (_cart isNotEqualTo []) then { _cartridgeKey = _cart select 0; };
        };
    } forEach (getArray (configFile >> "CfgWeapons" >> _weapon >> "magazines"));
    private _liveMass = getNumber (configFile >> "CfgWeapons" >> _weapon >> "WeaponSlotsInfo" >> "mass");
    if ((_cartridgeKey != "") && (_liveMass > 0)) then {
        private _band = [call FUNC(getWeaponBands), _cartridgeKey, _liveMass, 0]
            call FUNC(selectBand);
        if (_band isNotEqualTo []) then {
            _match = [_band select 0, _band select 4, _band select 5,
                      _band select 1, _band select 2];
        };
    };
};

private _result = if (_match isEqualTo []) then { [] } else {
    [_match select 0, _match select 1, _match select 2, _match select 3,
     _match select 4]
};
_cache set [_weapon, _result];
_result
"""


def render_match(rows):
    body = ",\n".join('    ["{}", "{}", {}, {}, "{}", {}]'.format(*r) for r in rows)
    return TEMPLATE.replace("__ROWS__", body).replace("__SCAN__", str(SCAN_ALIAS))


def render_bands(rows):
    body = ",\n".join('    ["{}", "{}", {}, 0, {}, {}]'.format(*r) for r in rows)
    return BAND_TEMPLATE.replace("__ROWS__", body)


def _render_all():
    db = json.loads(DB.read_text(encoding="utf-8"))
    rows = [r for r in (row(rec) for rec in db) if r]
    rows.sort(key=lambda r: r[0])
    return rows, band_rows(db)


def write_outputs():
    rows, bands = _render_all()
    OUT.write_text(render_match(rows), encoding="utf-8")
    BANDS_OUT.write_text(render_bands(bands), encoding="utf-8")
    return rows, bands


def check_outputs():
    """Return 0 when every generated file matches a fresh render."""
    rows, bands = _render_all()
    stale = False
    expected = ((OUT, render_match(rows)), (BANDS_OUT, render_bands(bands)))
    for path, text in expected:
        if not path.is_file():
            print(f"weapon projection: {path} is missing; run the generator")
            stale = True
            continue
        if path.read_text(encoding="utf-8") != text:
            print(f"weapon projection: {path} is stale; run the generator")
            stale = True
    if stale:
        return 1
    print(f"weapon projection: {len(rows)} rows and {len(bands)} band rows (fresh)")
    return 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--check" in argv:
        return check_outputs()
    rows, bands = write_outputs()
    print(
        f"weapon rows: {len(rows)}, band rows: {len(bands)}, "
        f"wrote {OUT.name} and {BANDS_OUT.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
