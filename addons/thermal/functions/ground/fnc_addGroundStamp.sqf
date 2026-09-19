#include "..\..\script_component.hpp"
/*
Record a ground thermal stamp (issue #124 - thermal painting).

A stamp is a transient temperature offset laid on the ground at a
position by a heat/contact event: a boot standing on soil, a tyre
track, the cool patch left where a vehicle parked and shaded the
ground.  The offset decays exponentially with the ground's lumped
inertia:

  offset(t) = offset0 * exp(-dt / tau)

and is ADDED to the equilibrium ground solve at that position
(fnc_calculateGroundTemperature).  The physics is the same transient
ground coupling the equilibrium solve already models - a covered patch
relaxes toward its shaded equilibrium while covered, then back toward
the sun equilibrium after the cover leaves.

Stamps are bounded (GVAR(groundStamps), cap 200): the oldest expired
stamps are dropped first, so the memory cost is fixed regardless of how
long the session runs.

Input:
  0: position (ARRAY, ATL or ASL) - where the stamp lands
  1: offset temperature (NUMBER, Celsius) - signed: + warm event
     (tyre/boot contact), - cool event (shade patch)
  2: tau (NUMBER, seconds) - decay time constant (ground material
     inertia; ~600 s soil, faster for a shallow contact)

Output: nothing
*/

params [
    ["_pos", [], [[]]],
    ["_offset", 0, [0]],
    ["_tau", 600, [0]]
];

if (count _pos < 2) exitWith {};
if (_offset == 0) exitWith {};
if (_tau <= 0) exitWith { _tau = 600; };

private _stamps = missionNamespace getVariable [QGVAR(groundStamps), []];
if (isNil "_stamps") then { _stamps = []; };

// Grid-cell key: coarse 5 m cells, so close events merge into one
// stamp instead of unbounded growth.  The offset is the accumulated
// peak; a later event in the same cell overwrites (the newest contact
// dominates the patch).
private _cell = format [
    "%1_%2",
    round ((_pos select 0) / 5),
    round ((_pos select 1) / 5)
];

// Find an existing stamp in this cell - replace it (newest wins).
private _found = false;
{
    if ((_x select 0) == _cell) exitWith {
        _x set [1, _offset];
        _x set [2, _tau];
        _x set [3, CBA_missionTime + _tau];  // expiry
        _found = true;
    };
} forEach _stamps;

if (!_found) then {
    _stamps pushBack [_cell, _offset, _tau, CBA_missionTime + _tau];
};

// Bound the list: drop the oldest expired stamps first.
if (count _stamps > 200) then {
    _stamps sort false;  // newest expiry first
    while { count _stamps > 200 } do {
        _stamps deleteAt (count _stamps - 1);
    };
};

missionNamespace setVariable [QGVAR(groundStamps), _stamps];
