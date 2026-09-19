#include "..\script_component.hpp"
/*
Sum the decayed ground-thermal stamps at a position (issue #124).

Returns the net offset in Celsius to ADD to the equilibrium ground
solve at [x, y].  Each stamp decays exponentially from its recorded
peak with its material tau:

  offset(t) = offset0 * exp(-dt / tau)      dt = now - stampTime

Expired stamps (offset below 0.05 C, or past their recorded expiry)
are pruned from the list on the way through, so the list stays bounded
without a separate GC pass.

The decayed-sum approximation is valid because ground equilibrium
changes slowly (tau ~600 s soil) relative to the stamp lifetime: the
patch relaxes back to whatever the local equilibrium is, and the
exponential captures that relaxation.

Input:
  0: position (ARRAY) - ATL/ASL; only the x/y cell matters

Output: NUMBER, Celsius offset to add to the ground temperature
*/

params [["_pos", [], [[]]]];

private _stamps = missionNamespace getVariable [QGVAR(groundStamps), []];
if (isNil "_stamps") exitWith { 0 };
if (count _stamps == 0) exitWith { 0 };
if (count _pos < 2) exitWith { 0 };

private _cell = format [
    "%1_%2",
    round ((_pos select 0) / 5),
    round ((_pos select 1) / 5)
];

private _total = 0;
private _now = CBA_missionTime;
private _live = [];
{
    _x params ["_key", "_offset0", "_tau", "_expiry"];
    if (isNil "_key" || {isNil "_offset0"} || _tau <= 0) then { continue; };
    // A stamp is either expired by time or decayed below 0.05 C.
    private _dt = _now - (_expiry - _tau);
    if (_dt < 0) then { _dt = 0; };
    private _decayed = _offset0 * exp (-_dt / _tau);
    if (_now < _expiry && {abs _decayed >= 0.05}) then {
        _live pushBack _x;
        if (_key == _cell) then {
            _total = _total + _decayed;
        };
    };
} forEach _stamps;

missionNamespace setVariable [QGVAR(groundStamps), _live];
_total
