#!/usr/bin/env python3
"""Generate the runtime cartridge resolver from the verified database.

The research database under data/ballistics/ is the source of truth. This
tool projects the cartridge layer into one SQF function that resolves an
ammunition classname to a real cartridge record at run time.

Performance. The common classname carries the calibre as a whole token,
so the resolver first splits the classname and looks each token up in a
hash index. Only when no token matches does it fall back to a substring
scan that also reads the magazine displayName. The index is built once
per mission, and every result is cached by classname, because the Fired
event calls the resolver on every shot.

Run:  python3 tools/validation/gen_runtime_cartridges.py
"""

import json
import re
import sys
from pathlib import Path

DATA = Path(__file__).parents[2] / "data" / "ballistics"
OUT = Path(__file__).parents[2] / "addons/ballistics/functions/fnc_getCartridgeData.sqf"
BANDS_OUT = (
    Path(__file__).parents[2] / "addons/ballistics/functions/fnc_getCartridgeBands.sqf"
)

MIN_ALIAS = 3
# The substring fallback only trusts aliases of this length or more, so a
# short code such as 556 can match a whole classname token but cannot
# match inside an unrelated string.
SCAN_ALIAS = 4


def normalise(text):
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def derived_aliases(name):
    """Aliases a mod classname is likely to carry.

    A cartridge designation of the form 7.62x51 yields the compact form
    762x51. A name whose first token is a number yields the number plus
    the initials, so 300 Norma Mag yields 300nm.
    """
    out = set()
    cleaned = re.sub(",", ".", name)
    m = re.search(r"(\d+(?:\.\d+)?)\s*[x\u00d7]\s*(\d+(?:\.\d+)?)", cleaned)
    if m:
        out.add(re.sub(r"[^0-9x]", "", f"{m.group(1)}x{m.group(2)}"))
    tokens = re.findall(r"[A-Za-z0-9.]+", name)
    if tokens:
        digits = re.sub(r"[^0-9]", "", tokens[0])
        if len(digits) >= 3:
            out.add(digits)
    if tokens and re.fullmatch(r"\d+", tokens[0]) and len(tokens) >= 3:
        initials = "".join(t[0].lower() for t in tokens[1:] if t[:1].isalpha())
        if initials:
            out.add(tokens[0] + initials)
    return {a for a in out if len(a) >= MIN_ALIAS}


def row(rec):
    names = rec.get("names", [])
    aliases = {n for n in (normalise(x) for x in names) if len(n) >= MIN_ALIAS}
    for name in names:
        aliases |= derived_aliases(name)
    # A bare calibre token is not an identity signal, so a record may
    # exclude one by name.
    aliases -= {normalise(a) for a in rec.get("alias_exclude", [])}
    aliases = sorted(aliases)
    if not aliases:
        return None
    values = rec["values"]

    def val(field):
        entry = values.get(field)
        return entry["value"] if entry else 0

    return [
        rec["cartridge_id"],
        "|".join(aliases),
        val("calibre_mm"),
        val("standard_twist_m"),
        val("max_pressure_mpa"),
        val("proof_pressure_mpa"),
        val("standard_twist_pistol_m"),
        val("standard_twist_rifle_m"),
    ]


def band_row(rec):
    """Return one property-band row, or None when the record has no identity.

    The band is the fallback of the cartridge resolver. The cartridge type is
    the discrete token, the calibre is the primary selector and the case
    length is the secondary. Twist and the two pressures are the payload. A
    missing number is a labelled zero.
    """
    cartridge_id = rec.get("cartridge_id")
    if not cartridge_id:
        return None
    values = rec.get("values", {})
    classification = rec.get("classification", {}) or {}

    def val(field):
        entry = values.get(field)
        return entry["value"] if entry else 0

    return [
        cartridge_id,
        str(classification.get("cartridge_type", "") or ""),
        val("calibre_mm"),
        val("case_length_mm"),
        val("standard_twist_m"),
        val("max_pressure_mpa"),
        val("proof_pressure_mpa"),
        val("standard_twist_pistol_m"),
        val("standard_twist_rifle_m"),
    ]


def band_rows(db):
    """Build every band row and sort it by cartridge id."""
    rows = [r for r in (band_row(rec) for rec in db) if r]
    rows.sort(key=lambda r: r[0])
    return rows


BAND_TEMPLATE = """#include "..\\script_component.hpp"
/*
Cartridge identity band table.

This file is GENERATED. The generator tools/validation/gen_runtime_cartridges.py
writes it from the verified database under data/ballistics/. Do not edit it
by hand. The research database is the source of truth.

The band table is the property fallback of the cartridge resolver. A
cartridge whose identity text resolves to no catalogue alias is matched by
its own calibre, read through the caliber parser. The type is the discrete
token, the calibre is the primary selector and the case length is the
secondary. The selector reads the table and the live properties only. The
calibre is an identity signal, never a value source.

A row has nine columns:

  0 cartridge_id      string, the stable catalogue key
  1 cartridge_type    string, the discrete token (rifle/pistol/shotgun)
  2 calibre_mm        number, the bullet diameter in mm, 0 absent
  3 case_length_mm    number, the case length in mm, 0 absent
  4 twist_m           number, the standard twist in metres per turn, 0 absent
  5 pressure_mpa      number, the maximum average pressure, 0 absent
  6 proof_mpa         number, the proof pressure, 0 absent
  7 twist_pistol_m    number, the pistol test-barrel twist, 0 absent
  8 twist_rifle_m     number, the rifle test-barrel twist, 0 absent

Returns the band table, one row per cartridge entry, sorted by id.

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
Cartridge resolver (issue #167).

Resolves an ammunition classname to a real cartridge record. This file
is a GENERATED runtime projection of the verified database held under
data/ballistics/. It is written by
tools/validation/gen_runtime_cartridges.py and must not be edited by
hand. The research database is the source of truth.

Order of work:
  1. The classname is split on its separators and each token is looked
     up in a hash index of the cartridge aliases. A whole-token hit is
     the common case and it is exact.
  2. Only when no token matches does the resolver read the readable name
     from the first magazine that fires the ammo, and scan the aliases as
     substrings. A longer alias beats a shorter one.
  3. The result is cached by classname, because the Fired event calls
     this on every shot.

Returns [cartridge_id, calibre_mm, twist_m, pressure_mpa, proof_mpa,
twist_pistol_m, twist_rifle_m], or an empty array when nothing matches. A
zero means the value is not held. A cartridge that a standards body
registers for both a pistol and a rifle test barrel carries both rates;
the caller selects by the weapon type.

Arguments:
  0: ammo (STRING, the CfgAmmo classname, default "")
*/
params [["_ammo", "", [""]]];
if (_ammo == "") exitWith { [] };

private _cache = missionNamespace getVariable [QGVAR(cartridgeCache), nil];
if (isNil "_cache") then {
    _cache = createHashMap;
    missionNamespace setVariable [QGVAR(cartridgeCache), _cache];
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

// ─── The cartridge table ─────────────────────────────────────────────────
// [id, aliases (lower case alphanumerics, pipe separated), calibre mm,
//  twist m per turn, pressure MPa, proof MPa, pistol twist, rifle twist]
private _TABLE = [
__ROWS__
];

// The alias index, built once per mission. The value is the record plus
// the alias length, which is the tie-break when two aliases match.
private _index = missionNamespace getVariable [QGVAR(cartridgeIndex), nil];
if (isNil "_index" || {(count _index) == 0}) then {
    _index = createHashMap;
    {
        _x params ["_id", "_aliases", "_calibre", "_twist", "_pressure", "_proof", "_twistP", "_twistR"];
        {
            _index set [_x, [_id, _calibre, _twist, _pressure, _proof, _twistP, _twistR, count _x]];
        } forEach (_aliases splitString "|");
    } forEach _TABLE;
    missionNamespace setVariable [QGVAR(cartridgeIndex), _index];
};

private _match = [];

// ─── Fast path: whole tokens of the classname ────────────────────────────
private _bestLen = 0;
{
    private _hit = _index getOrDefault [_x, []];
    if ((_hit isNotEqualTo []) && {(_hit select 7) > _bestLen}) then {
        _match = _hit;
        _bestLen = _hit select 7;
    };
} forEach (toLower _ammo splitString "_- .");

if (_match isEqualTo []) then {
    // ─── Fallback: the readable name, matched as substrings ──────────────
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
        _x params ["_id", "_aliases", "_calibre", "_twist", "_pressure", "_proof", "_twistP", "_twistR"];
        private _list = _aliases splitString "|";
        private _rowLen = 0;
        for "_i" from 0 to ((count _list) - 1) do {
            private _alias = _list select _i;
            if (_alias != "" && {count _alias >= __SCAN__} && {_query find _alias >= 0} && {count _alias > _rowLen}) then {
                _rowLen = count _alias;
            };
        };
        if (_rowLen > _bestLen) then {
            _match = [_id, _calibre, _twist, _pressure, _proof, _twistP, _twistR];
            _bestLen = _rowLen;
        };
    } forEach _TABLE;
};

// ─── Band: the live calibre ──────────────────────────────────────────────
// A class whose identity text resolves to no catalogue alias is matched by
// its own calibre, read through the caliber parser. The parser fills a
// caliber the alias tables do not name from the numeric token. The caliber
// is an identity signal, never a value source. A miss is an empty array,
// exactly as before.
if (_match isEqualTo []) then {
    private _calibre = ([_ammo] call FUNC(parseCaliber)) select 0;
    if (_calibre > 0) then {
        private _band = [call FUNC(getCartridgeBands), "", _calibre, 0]
            call FUNC(selectBand);
        if (_band isNotEqualTo []) then {
            _match = [_band select 0, _band select 2, _band select 4,
                      _band select 5, _band select 6, _band select 7,
                      _band select 8];
        };
    };
};

private _result = if (_match isEqualTo []) then { [] } else {
    [_match select 0, _match select 1, _match select 2, _match select 3,
     _match select 4, _match select 5, _match select 6]
};
_cache set [_ammo, _result];
_result
"""


def _build(db):
    rows = [r for r in (row(rec) for rec in db) if r]

    # An alias shared by two cartridges is not an identity signal, so it
    # is dropped from the index. A cartridge keeps its own longer aliases.
    counts = {}
    for r in rows:
        for alias in r[1].split("|"):
            counts[alias] = counts.get(alias, 0) + 1
    for r in rows:
        kept = [a for a in r[1].split("|") if counts[a] == 1]
        if kept:
            r[1] = "|".join(kept)
    ambiguous = sum(1 for c in counts.values() if c > 1)
    rows.sort(key=lambda r: r[0])
    return rows, ambiguous


def render_match(rows):
    body = ",\n".join(
        '    ["{}", "{}", {}, {}, {}, {}, {}, {}]'.format(*r) for r in rows
    )
    return TEMPLATE.replace("__ROWS__", body).replace("__SCAN__", str(SCAN_ALIAS))


def render_bands(rows):
    body = ",\n".join(
        '    ["{}", "{}", {}, {}, {}, {}, {}, {}, {}]'.format(*r) for r in rows
    )
    return BAND_TEMPLATE.replace("__ROWS__", body)


def _render_all():
    db = json.loads((DATA / "cartridges.json").read_text(encoding="utf-8"))
    rows, ambiguous = _build(db)
    return rows, band_rows(db), ambiguous


def write_outputs():
    rows, bands, ambiguous = _render_all()
    OUT.write_text(render_match(rows), encoding="utf-8")
    BANDS_OUT.write_text(render_bands(bands), encoding="utf-8")
    return rows, bands, ambiguous


def check_outputs():
    """Return 0 when every generated file matches a fresh render."""
    rows, bands, _ = _render_all()
    stale = False
    expected = ((OUT, render_match(rows)), (BANDS_OUT, render_bands(bands)))
    for path, text in expected:
        if not path.is_file():
            print(f"cartridge projection: {path} is missing; run the generator")
            stale = True
            continue
        if path.read_text(encoding="utf-8") != text:
            print(f"cartridge projection: {path} is stale; run the generator")
            stale = True
    if stale:
        return 1
    print(f"cartridge projection: {len(rows)} rows and {len(bands)} band rows (fresh)")
    return 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--check" in argv:
        return check_outputs()
    rows, bands, ambiguous = write_outputs()
    print(
        f"cartridge rows: {len(rows)}, band rows: {len(bands)}, "
        f"ambiguous aliases dropped: {ambiguous}, "
        f"wrote {OUT.name} and {BANDS_OUT.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
