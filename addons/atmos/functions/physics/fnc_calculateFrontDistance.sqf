#include "..\..\script_component.hpp"

/*
Signed distance from an observer to a weather front line.

The front is a straight line through the anchor point, with a unit normal
along its direction of motion (the bearing).  The front line has advanced
_frontDistKm along that normal.  The signed distance is the observer's
projection onto the normal, measured from the front line:

  d = dot(observer - anchor, normal) - frontDistKm

A positive d puts the observer ahead of the front (the side the front moves
toward); a negative d puts the observer behind it.  Positions are in metres
and the front distance is in kilometres, so the projection is divided by
1000.  This is the "signed distance to the front" the issue maps to a phase
factor.

Arguments:
  0: observer position 2D [x, y] in metres (Array)
  1: anchor position 2D [x, y] in metres (Array)
  2: bearing, direction of motion in compass degrees (Number)
  3: front distance along the bearing from the anchor, km (Number)

Return Value: NUMBER, signed distance in kilometres
Example: [[1000, 0], [0, 0], 90, 0] call aee_atmos_fnc_calculateFrontDistance
Public: No
*/

params [
    ["_observer2D", [], [[]]],
    ["_anchor2D", [], [[]]],
    ["_bearingDeg", 0, [0]],
    ["_frontDistKm", 0, [0]]
];

if ((count _observer2D) < 2 || {(count _anchor2D) < 2}) exitWith { 0 };
if !(_bearingDeg isEqualType 0) then { _bearingDeg = 0; };
if !(_frontDistKm isEqualType 0) then { _frontDistKm = 0; };

// Compass bearing to a unit normal: east = sin(bearing), north = cos(bearing).
private _nx = sin _bearingDeg;
private _ny = cos _bearingDeg;

private _along = ((_observer2D select 0) - (_anchor2D select 0)) * _nx
    + ((_observer2D select 1) - (_anchor2D select 1)) * _ny;

(_along / 1000) - _frontDistKm
