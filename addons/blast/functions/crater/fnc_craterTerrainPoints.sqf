#include "..\..\script_component.hpp"

/*
Crater terrain grid for the engine setTerrainHeight command.

setTerrainHeight is a real Arma 3 command:
    setTerrainHeight [positionAndAltitudeArray, adjustObjects]
where positionAndAltitudeArray is an array of [x, y, newASLHeight] entries.
This kernel builds that array so a caller can lower the terrain into a
paraboloid crater.  It produces only the geometry.  The caller runs the
command, on the server, because the height change is JIP-queued and synced.

The apparent crater is a paraboloid:
    z(r) = -D_a * (1 - (r / R_a)^2)        for r <= R_a
plus a raised lip that tapers from H_lip at r = R_a to 0 at r = R_lip.

Sources: TM 5-855-1; UFC 3-340-02; Kinney and Graham (1985).

Engine limits, recorded honestly: setTerrainHeight stores every change in the
JIP queue and does not remove a change that restores the default.  Extreme
changes can make a terrain section invisible and can throw a walking unit.
The caller must clamp the crater to a modest depth and edit positions by
terrain section where possible.

Input:  [_centreASL, _rA, _dA, _hLip, _stepM] - crater centre (ASL), apparent
        radius (m), apparent depth (m), lip height (m), grid step (m).
Output: [[x, y, z], ...] - one entry per grid point (empty on bad input).
Public: No
*/

params [
    ["_centre", [0, 0, 0], [[]]],
    ["_rA", 1, [0]],
    ["_dA", 1, [0]],
    ["_hLip", 0, [0]],
    ["_stepM", 1, [0]]
];

if (_rA <= 0 || _dA <= 0 || _stepM <= 0) exitWith { [] };

private _cx = _centre select 0;
private _cy = _centre select 1;
private _cz = _centre select 2;
private _rLip = 1.25 * _rA;
private _steps = ceil (_rLip / _stepM);
private _points = [];

for "_i" from -_steps to _steps do {
    for "_j" from -_steps to _steps do {
        private _dx = _i * _stepM;
        private _dy = _j * _stepM;
        private _r = sqrt (_dx * _dx + _dy * _dy);
        if (_r <= _rLip) then {
            private _dz = 0;
            if (_r <= _rA) then {
                _dz = -_dA * (1 - (_r / _rA) ^ 2);
            } else {
                _dz = _hLip * (1 - ((_r - _rA) / (_rLip - _rA)));
            };
            _points pushBack [_cx + _dx, _cy + _dy, _cz + _dz];
        };
    };
};

_points
