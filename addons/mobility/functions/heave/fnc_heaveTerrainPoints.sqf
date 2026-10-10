#include "..\..\script_component.hpp"

/*
Frost heave terrain grid for the engine setTerrainHeight command.

setTerrainHeight is a real Arma 3 command (since 2.10):
    setTerrainHeight [positionAndAltitudeArray, adjustObjects]
where positionAndAltitudeArray is an array of [x, y, newASLHeight] entries.
This kernel builds that array so a caller can raise the terrain by a heave
profile.  It produces only the geometry.  The caller runs the command, on the
server, because the height change is JIP-queued and synced.

A heave cell is a broad rise, not a crater.  The kernel raises each grid point
by the heave height H with a smooth cosine taper from full H at the centre to
zero at the cell edge.  The taper is what keeps the edge free of the vertical
cliff that the engine warns against.

Sources for the command and its limits: the Arma 3 command reference
(setTerrainHeight).  Heave physics is in fnc_calculateFrostHeave.

Engine limits, recorded honestly: setTerrainHeight stores every change in the
JIP queue and does NOT remove a change that restores the default value.  A
seasonal heave-then-subsidence cycle would therefore grow the JIP queue without
bound, and can make a terrain section invisible or throw a walking unit.  So the
seasonal cycle is a ceiling: apply at most one raise per cell, clamp it to the
maximum-heave setting, and never call this in a per-tick loop.

Input:  [_centreASL, _radiusM, _heaveM, _stepM] - cell centre (ASL), cell
        radius (m), heave height (m), grid step (m).
Output: [[x, y, z], ...] - one entry per grid point (empty on bad input).
Public: No
*/

params [
    ["_centre", [0, 0, 0], [[]]],
    ["_radius", 10, [0]],
    ["_heave", 0.05, [0]],
    ["_step", 1, [0]]
];

if (_radius <= 0 || _heave <= 0 || _step <= 0) exitWith { [] };

private _cx = _centre select 0;
private _cy = _centre select 1;
private _cz = _centre select 2;
private _steps = ceil (_radius / _step);
private _points = [];

for "_i" from -_steps to _steps do {
    for "_j" from -_steps to _steps do {
        private _dx = _i * _step;
        private _dy = _j * _step;
        private _r = sqrt (_dx * _dx + _dy * _dy);
        if (_r <= _radius) then {
            // Cosine taper: full heave at the centre, zero at the edge.
            private _weight = 0.5 * (1 + cos (180 * (_r / _radius)));
            _points pushBack [_cx + _dx, _cy + _dy, _cz + (_heave * _weight)];
        };
    };
};

_points
