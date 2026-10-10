#include "..\script_component.hpp"

/*
Resource target kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The caller
supplies the water and the vegetation provider, so the search is deterministic
and testable.  The runtime supplies providers that read the published
environmental facts: EFUNC(weather,getCoastDistance) for water and
aee_weather_terrainSignals for the vegetation score.

Walks an eight point ring at each increasing radius and returns the highest
scoring point, or [0,0,0] when every score is zero.  The scoring is
fnc_resourceScore.

Arguments:
  0: Array  - the search centre
  1: Bool   - true to want water, false for food
  2: Number - the search radius, metres
  3: Number - the ring step, metres
  4: Code   - the water provider, called with a point, returns 0 to 1
  5: Code   - the vegetation provider, called with a point, returns 0 to 1

Returns:
  Array - the best point, or [0,0,0]
*/

params [
    ["_pos", [0, 0, 0], [[]]],
    ["_wantWater", false, [false]],
    ["_searchRadius", 100, [0]],
    ["_step", 25, [0]],
    ["_waterProvider", {}, [{}]],
    ["_vegProvider", {}, [{}]]
];

if ((count _pos) < 2) exitWith { [0, 0, 0] };
if (_step <= 0) exitWith { [0, 0, 0] };
if (_searchRadius <= 0) exitWith { [0, 0, 0] };

private _best = [0, 0, 0];
private _bestScore = 0;
private _steps = ((ceil (_searchRadius / _step)) max 1);

for "_r" from 1 to _steps do {
    private _radius = _r * _step;
    for "_a" from 0 to 7 do {
        private _angle = _a * 45;
        private _point = [
            (_pos select 0) + (_radius * (sin _angle)),
            (_pos select 1) + (_radius * (cos _angle)),
            0
        ];
        private _water = [_point] call _waterProvider;
        if !(_water isEqualType 0) then { _water = 0; };
        private _veg = [_point] call _vegProvider;
        if !(_veg isEqualType 0) then { _veg = 0; };

        private _score = [_radius, _water, _veg, _wantWater] call FUNC(resourceScore);
        if (_score > _bestScore) then {
            _bestScore = _score;
            _best = _point;
        };
    };
};

_best
