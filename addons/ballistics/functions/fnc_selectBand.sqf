#include "..\script_component.hpp"
/*
Property band selector (the ballistics identity fallback).

This is the shared rule behind the weapon, cartridge and projectile band
tables. It mirrors the band route of aee_vehicles_fnc_classifyVehicle: a
generated table holds the properties that identify each catalogue record,
and a live or held property selects at most one row.

A band row has four leading columns and a payload:

  0 id         string, the catalogue identity
  1 token      string, the discrete property, "" when the row states none
  2 primary    number, the primary property, 0 when the row holds none
  3 secondary  number, the secondary property, 0 when the row holds none
  4..          the payload, read by the caller

The selection is bounded and it never guesses.

  token      the row token must equal the live token, unless the live token
             is empty or the row states none.
  primary    the nearest held primary value wins. Two distinct held values
             at the same distance are ambiguous and select no row. The live
             value must also fall inside the table's own primary resolution,
             derived from the table: the relative gaps between consecutive
             held values, then the upper Tukey fence (the standard 1.5
             interquartile-range fence). No threshold is chosen by hand.
  secondary  the rows at that primary are separated by the nearest held
             secondary. A tie selects no row.

The selector returns the selected row, or an empty array. The live
properties are identity signals only. They are never written to a
catalogue.

Arguments:
  0: rows (ARRAY of ARRAY) the generated band table
  1: token (STRING, "" accepts every row)
  2: primary (NUMBER, the live primary property, 0 = unknown)
  3: secondary (NUMBER, the live secondary property, 0 = unknown)

Returns the selected row, or [].

Public: No
*/
params [
    ["_rows", [], [[]]],
    ["_token", "", [""]],
    ["_primary", 0, [0]],
    ["_secondary", 0, [0]]
];
if ((_rows isEqualTo []) || (_primary <= 0)) exitWith { [] };

// ─── The held primary values of the matching rows ────────────────────────
private _held = [];
{
    _x params ["_id", "_rowToken", "_rowPrimary"];
    if (((_token == "") || (_rowToken == _token)) && (_rowPrimary > 0)) then {
        _held pushBack _rowPrimary;
    };
} forEach _rows;
if (_held isEqualTo []) exitWith { [] };
_held sort true;

// The table's own primary resolution: the upper Tukey fence of the
// relative gaps between consecutive held values. A negative cap means too
// few gaps to measure a resolution, so no bound applies.
private _gaps = [];
for "_i" from 0 to ((count _held) - 2) do {
    private _low = _held select _i;
    if (_low > 0) then {
        _gaps pushBack (((_held select (_i + 1)) - _low) / _low);
    };
};
private _cap = -1;
if ((count _gaps) >= 2) then {
    _gaps sort true;
    private _last = (count _gaps) - 1;
    private _q1 = _gaps select (floor (_last * 0.25));
    private _q3 = _gaps select (floor (_last * 0.75));
    _cap = _q3 + (1.5 * (_q3 - _q1));
};

// ─── The nearest held primary, and whether it stands out ─────────────────
private _minDistance = -1;
{
    private _distance = abs (_x - _primary);
    if ((_minDistance < 0) || (_distance < _minDistance)) then { _minDistance = _distance; };
} forEach _held;

private _nearValue = -1;
private _nearCount = 0;
{
    if (abs (_x - _primary) == _minDistance) then {
        if (_nearCount == 0) then {
            _nearValue = _x;
            _nearCount = 1;
        } else {
            if (_x != _nearValue) then { _nearCount = 2; };
        };
    };
} forEach _held;

if ((_minDistance < 0) || (_nearCount > 1)) exitWith { [] };
if ((_cap >= 0) && (_minDistance > (_cap * _nearValue))) exitWith { [] };

// ─── The rows at that primary, separated by the secondary ────────────────
private _hits = 0;
private _best = [];
private _minSecondary = -1;
{
    _x params ["_id", "_rowToken", "_rowPrimary", "_rowSecondary"];
    if (((_token == "") || (_rowToken == _token))
        && (_rowPrimary > 0)
        && (abs (_rowPrimary - _primary) == _minDistance)) then {
        private _secondaryDistance = 0;
        if ((_rowSecondary > 0) && (_secondary > 0)) then {
            _secondaryDistance = abs (_rowSecondary - _secondary);
        };
        if ((_minSecondary < 0) || (_secondaryDistance < _minSecondary)) then {
            _minSecondary = _secondaryDistance;
            _hits = 1;
            _best = _x;
        } else {
            if (_secondaryDistance == _minSecondary) then { _hits = _hits + 1; };
        };
    };
} forEach _rows;
if ((_hits == 1) && (_best isNotEqualTo [])) exitWith { _best };
[]
