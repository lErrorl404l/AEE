#include "..\..\script_component.hpp"

/*
Meteor state for one shower at one date and place.

Composes the shared sidereal-time kernel with the shower activity, radiant
projection and rate kernels.  Pure: it reads no engine state beyond its
arguments, so the caller owns the NELM chain and the night/cloud gates.

Arguments:
  0: Array  - mission date [year, month, day]
  1: Number - observer latitude, degrees
  2: Number - limiting magnitude
  3: Array  - shower row (fnc_meteorShowers format)
Returns:
  Array [active, altDeg, azDeg, rate] - whether the shower is active, the
  radiant altitude and azimuth, and the expected meteors per hour.
*/

params [
    ["_date", date, [[]]],
    ["_latDeg", 0, [0]],
    ["_limitingMag", 6.5, [0]],
    ["_shower", [], [[]]]
];

private _lstDeg = [_date] call FUNC(siderealTime);
private _month = _date select 1;
private _day = _date select 2;

private _active = [_month, _day, _shower] call FUNC(showerIsActive);
private _horizontal = [_shower select 9, _shower select 10, _latDeg, _lstDeg] call FUNC(radiantHorizontal);
private _altDeg = _horizontal select 0;
private _azDeg = _horizontal select 1;

private _rate = 0;
if (_active) then {
    _rate = [_shower select 13, _shower select 12, _altDeg, _limitingMag] call FUNC(meteorRate);
};

[_active, _altDeg, _azDeg, _rate]
