#include "..\script_component.hpp"

/*
Raise a ring of disturbance cells around a position through the substrate.

Client-local field only.  A gunshot sends a wave of disturbance outward, so
the cells around the shooter go quiet for the stimulus half-life.  The field
is the substrate's local missionNamespace field.

Arguments:
  0: Array  - the centre position
  1: Number - the stimulus magnitude, 0 to 1

Returns:
  Nothing.
*/

params [
    ["_position", [0, 0, 0], [[]]],
    ["_magnitude", 1, [0]]
];

if (!hasInterface) exitWith {};

private _field = missionNamespace getVariable [EGVAR(ai,disturbance), []];
if !(_field isEqualType []) then { _field = []; };

private _now = CBA_missionTime;
private _rings = [0, 60, 120];

for "_r" from 0 to ((count _rings) - 1) do {
    private _radius = _rings select _r;
    for "_a" from 0 to 7 do {
        private _angle = _a * 45;
        private _point = [
            (_position select 0) + (_radius * (sin _angle)),
            (_position select 1) + (_radius * (cos _angle)),
            0
        ];
        private _key = [_point] call EFUNC(ai,disturbanceKey);
        _field = [_field, _key, _magnitude, _now] call EFUNC(ai,disturbanceApply);
    };
};

missionNamespace setVariable [EGVAR(ai,disturbance), _field];
