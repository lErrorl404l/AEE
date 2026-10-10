#include "..\..\script_component.hpp"

/*
Rotate a wind vector by a meteorological veer.

The wind vector is [east, north].  Its meteorological direction is the
direction the wind blows FROM, in compass degrees clockwise from north:

  from = atan2(east, north) + 180

A veer is a clockwise change of the FROM direction (a backing is
anticlockwise).  The front passage veers the wind clockwise by 40-90 deg
(FAA AC 00-6B; WW2010): ahead of a cold front the wind is south-westerly,
behind it west-north-westerly.  The magnitude is preserved; only the
direction changes.  The rotated vector is rebuilt from the new FROM
direction (the wind blows toward from - 180).

Arguments:
  0: wind vector [east, north] in m/s (Array)
  1: veer in degrees, positive = clockwise (Number)

Return Value: ARRAY [east, north] in m/s
Example: [[-5, 5], 90] call aee_atmos_fnc_calculateFrontWind
Public: No
*/

params [["_windVec", [0, 0], [[]]], ["_veerDeg", 0, [0]]];

if ((count _windVec) < 2) exitWith { _windVec };
if !(_veerDeg isEqualType 0) then { _veerDeg = 0; };

private _x = _windVec select 0;
private _y = _windVec select 1;
if !(_x isEqualType 0) then { _x = 0; };
if !(_y isEqualType 0) then { _y = 0; };

private _mag = sqrt (_x * _x + _y * _y);
if (_mag <= 0.0001) exitWith { [_x, _y] };

private _fromDeg = (_x atan2 _y) + 180 + _veerDeg;
private _towardDeg = _fromDeg - 180;

[_mag * (sin _towardDeg), _mag * (cos _towardDeg)]
