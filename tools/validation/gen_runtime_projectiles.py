#!/usr/bin/env python3
"""Generate the runtime projectile resolver from the verified database.

Projects the bullet layer into one SQF function that resolves an
ammunition classname to a real bullet record.

The resolver reports the coefficients that are actually held, each with
its grade. It does not choose a drag model on the bullet's behalf: a
coefficient is defined against a specific standard, so the consumer uses
the standard it computes with. Where a coefficient is not held, the
resolver reports a zero and an empty grade rather than substituting a
derived value or the other model's coefficient.

Run:  python3 tools/validation/gen_runtime_projectiles.py
"""

import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
OUT = (
    Path(__file__).parents[2] / "addons/ballistics/functions/fnc_getProjectileData.sqf"
)
BANDS_OUT = (
    Path(__file__).parents[2] / "addons/ballistics/functions/fnc_getProjectileBands.sqf"
)

MIN_ALIAS = 3
SCAN_ALIAS = 4

# The service bullet a military chambering is loaded with. A real world
# fact, not a per-mod entry: a 5.56x45 NATO weapon fires M855.
DEFAULTS = {
    "556x45_nato": "apg_m855",
    "762x51_nato": "apg_m80",
    "50_bmg": "apg_m33",
    "762x39": "apg_7.62m43",
}


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def coefficients(values):
    """Every coefficient held, as MODEL:value:grade, joined by a pipe.

    The convention is bc_<model>, so the database can hold a coefficient
    against ANY standard, and a new standard needs no code change. A
    derived value is never reported.
    """
    out = []
    for field, entry in sorted(values.items()):
        if not field.startswith("bc_"):
            continue
        if entry.get("grade") == "derived":
            continue
        model = field[3:].upper()
        out.append(f"{model}:{entry['value']}:{entry.get('grade', '')}")
    return "|".join(out)


def row(rec):
    aliases = sorted(
        {n for n in (normalise(x) for x in rec.get("names", [])) if len(n) >= MIN_ALIAS}
    )
    if not aliases:
        return None
    values = rec["values"]

    def val(field, default=0):
        entry = values.get(field)
        return entry["value"] if entry else default

    return [
        rec["projectile_id"],
        "|".join(aliases),
        val("mass_g"),
        val("diameter_mm"),
        coefficients(values),
        val("length_mm"),
    ]


def band_row(rec):
    """Return one property-band row, or None when the record has no identity.

    The band is the fallback of the projectile resolver. The bullet diameter
    is the primary selector and the mass is the secondary. The length and the
    held coefficients are the payload. A missing number is a labelled zero.
    """
    projectile_id = rec.get("projectile_id")
    if not projectile_id:
        return None
    values = rec.get("values", {})

    def val(field, default=0):
        entry = values.get(field)
        return entry["value"] if entry else default

    return [
        projectile_id,
        "",
        val("diameter_mm"),
        val("mass_g"),
        val("length_mm"),
        coefficients(values),
    ]


def band_rows(db):
    """Build every band row and sort it by projectile id."""
    rows = [r for r in (band_row(rec) for rec in db) if r]
    rows.sort(key=lambda r: r[0])
    return rows


BAND_TEMPLATE = """#include "..\\script_component.hpp"
/*
Projectile identity band table.

This file is GENERATED. The generator tools/validation/gen_runtime_projectiles.py
writes it from the verified database under data/ballistics/. Do not edit it
by hand.

The band table is the property fallback of the projectile resolver. A bullet
whose identity text resolves to no catalogue record is matched by its own
diameter, read from its cartridge. The diameter is the primary selector and
the mass is the secondary. The length and the held coefficients are the
payload. The selector reads the table and the live properties only. The
diameter is an identity signal, never a value source.

A row has six columns:

  0 projectile_id   string, the stable catalogue key
  1 token           string, empty: a bullet carries no discrete token
  2 diameter_mm     number, the bullet diameter in mm, 0 absent
  3 mass_g          number, the bullet mass in grams, 0 absent
  4 length_mm       number, the bullet length in mm, 0 absent
  5 coefficients    string, the held MODEL:value:grade triples, "" absent

Returns the band table, one row per projectile entry, sorted by id.

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
Projectile resolver (issue #167).

Resolves an ammunition classname to a real bullet record. This file is a
GENERATED runtime projection of the verified database held under
data/ballistics/. It is written by
tools/validation/gen_runtime_projectiles.py and must not be edited by
hand.

The coefficients are the ones actually held, each with its grade. The
resolver does not pick a drag model: a coefficient belongs to a specific
standard, so the consumer uses the standard it computes with. A zero
coefficient with an empty grade means the value is not held. A derived
value is never reported, and one standard is never substituted for
another.

Returns [projectile_id, mass_g, diameter_mm, coefficients, length_mm], or
an empty array when nothing matches. The coefficients array holds one
[MODEL, value, grade] triple per standard the database holds for the
bullet, so a caller uses the standard it computes with.

Arguments:
  0: ammo (STRING, the CfgAmmo classname, default "")
*/
params [["_ammo", "", [""]]];
if (_ammo == "") exitWith { [] };

private _cache = missionNamespace getVariable [QGVAR(projectileCache), nil];
if (isNil "_cache") then {
    _cache = createHashMap;
    missionNamespace setVariable [QGVAR(projectileCache), _cache];
};
private _cached = _cache getOrDefault [_ammo, []];
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

// ─── The projectile table ────────────────────────────────────────────────
// [id, aliases, mass g, diameter mm, coefficients, length mm]
private _TABLE = [
__ROWS__
];

private _index = missionNamespace getVariable [QGVAR(projectileIndex), nil];
if (isNil "_index" || {(count _index) == 0}) then {
    _index = createHashMap;
    {
        _x params ["_id", "_aliases", "_mass", "_diameter", "_coeffs", "_len"];
        {
            if ((_index getOrDefault [_x, []]) isEqualTo []) then {
                _index set [_x, [_id, _mass, _diameter, _coeffs, _len, count _x]];
            };
        } forEach (_aliases splitString "|");
    } forEach _TABLE;
    missionNamespace setVariable [QGVAR(projectileIndex), _index];
};

private _match = [];
private _bestLen = 0;
{
    private _hit = _index getOrDefault [_x, []];
    if ((_hit isNotEqualTo []) && {(_hit select 6) > _bestLen}) then {
        _match = _hit;
        _bestLen = _hit select 8;
    };
} forEach (toLower _ammo splitString "_- .");

if (_match isEqualTo []) then {
    // Identity text only: the classname, the raw display name and its
    // localised stringtable text. A vanilla class stores a $STR key in
    // displayName, so all three are needed. None carries a figure.
    private _rawName = "";
    {
        if (getText (configFile >> "CfgMagazines" >> configName _x >> "ammo") == _ammo) exitWith {
            _rawName = getText (configFile >> "CfgMagazines" >> configName _x >> "displayName");
        };
    } forEach ((configFile >> "CfgMagazines") call BIS_fnc_returnChildren);
    private _localName = if ((_rawName select [0,1]) == "$") then { localize _rawName } else { _rawName };

    private _query = [_ammo + " " + _rawName + " " + _localName] call _normalise;
    {
        _x params ["_id", "_aliases", "_mass", "_diameter", "_coeffs", "_len"];
        private _list = _aliases splitString "|";
        private _rowLen = 0;
        for "_i" from 0 to ((count _list) - 1) do {
            private _alias = _list select _i;
            if (_alias != "" && {count _alias >= __SCAN__} && {_query find _alias >= 0} && {count _alias > _rowLen}) then {
                _rowLen = count _alias;
            };
        };
        if (_rowLen > _bestLen) then {
            _match = [_id, _mass, _diameter, _coeffs, _len];
            _bestLen = _rowLen;
        };
    } forEach _TABLE;
};

// The service bullet of a military chambering, when the classname and the
// readable name carry no bullet identity of their own.
private _DEFAULTS = [
__DEFAULTS__
];

private _byId = missionNamespace getVariable [QGVAR(projectileById), nil];
if (isNil "_byId" || {(count _byId) == 0}) then {
    _byId = createHashMap;
    {
        _x params ["_id", "_aliases", "_mass", "_diameter", "_coeffs", "_len"];
        _byId set [_id, [_id, _mass, _diameter, _coeffs, _len]];
    } forEach _TABLE;
    missionNamespace setVariable [QGVAR(projectileById), _byId];
};

if (_match isEqualTo []) then {
    private _cartridge = [_ammo] call FUNC(getCartridgeData);
    if (_cartridge isNotEqualTo []) then {
        private _default = "";
        {
            if ((_x select 0) == (_cartridge select 0)) exitWith { _default = _x select 1; };
        } forEach _DEFAULTS;
        if (_default != "") then {
            _match = _byId getOrDefault [_default, []];
        };
    };
};

// ─── Band: the live bullet diameter ──────────────────────────────────────
// A class whose identity text resolves to no catalogue record and whose
// chambering names no service bullet is matched by the bullet diameter,
// read from its cartridge. The diameter is an identity signal, never a
// value source. A miss is an empty array, exactly as before.
if (_match isEqualTo []) then {
    private _cart = [_ammo] call FUNC(getCartridgeData);
    private _diameter = if (_cart isEqualTo []) then { 0 } else { _cart select 1 };
    if (_diameter <= 0) then {
        _diameter = ([_ammo] call FUNC(parseCaliber)) select 0;
    };
    if (_diameter > 0) then {
        private _band = [call FUNC(getProjectileBands), "", _diameter, 0]
            call FUNC(selectBand);
        if (_band isNotEqualTo []) then {
            _match = [_band select 0, _band select 3, _band select 2,
                      _band select 5, _band select 4];
        };
    };
};

private _result = if (_match isEqualTo []) then { [] } else {
    [
        _match select 0,
        _match select 1,
        _match select 2,
        (_match select 3 splitString "|") apply {
            private _parts = _x splitString ":";
            [_parts select 0, parseNumber (_parts select 1), _parts select 2]
        },
        _match select 4
    ]
};
_cache set [_ammo, _result];
_result
"""


def _build(db):
    rows = [r for r in (row(rec) for rec in db) if r]
    rows.sort(key=lambda r: r[0])
    return rows


def render_match(rows):
    body = ",\n".join('    ["{}", "{}", {}, {}, "{}", {}]'.format(*r) for r in rows)
    ids = {r[0] for r in rows}
    defaults = ",\n".join(
        '    ["{}", "{}"]'.format(c, p) for c, p in sorted(DEFAULTS.items()) if p in ids
    )
    return (
        TEMPLATE.replace("__ROWS__", body)
        .replace("__DEFAULTS__", defaults)
        .replace("__SCAN__", str(SCAN_ALIAS))
    )


def render_bands(rows):
    body = ",\n".join('    ["{}", "{}", {}, {}, {}, "{}"]'.format(*r) for r in rows)
    return BAND_TEMPLATE.replace("__ROWS__", body)


def _render_all():
    db = json.loads((DATA / "projectiles.json").read_text(encoding="utf-8"))
    return _build(db), band_rows(db)


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
            print(f"projectile projection: {path} is missing; run the generator")
            stale = True
            continue
        if path.read_text(encoding="utf-8") != text:
            print(f"projectile projection: {path} is stale; run the generator")
            stale = True
    if stale:
        return 1
    print(f"projectile projection: {len(rows)} rows and {len(bands)} band rows (fresh)")
    return 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--check" in argv:
        return check_outputs()
    rows, bands = write_outputs()
    print(
        f"projectile rows: {len(rows)}, band rows: {len(bands)}, "
        f"wrote {OUT.name} and {BANDS_OUT.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
