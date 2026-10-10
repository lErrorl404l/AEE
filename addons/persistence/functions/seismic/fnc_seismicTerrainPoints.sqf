#include "..\..\script_component.hpp"

/*
Seismic terrain-deformation grid for the engine setTerrainHeight command.

setTerrainHeight is a real Arma 3 command (since 2.10):
    setTerrainHeight [positionAndAltitudeArray, adjustObjects]
where positionAndAltitudeArray is an array of [x, y, newASLHeight] entries.
This kernel builds that array so a caller can raise or lower the terrain by a
smooth profile.  It produces only the geometry.  The caller runs the command,
on the server, because the height change is JIP-queued and synced.

A positive delta raises the ground (a landslide deposit); a negative delta
lowers it (liquefaction subsidence, or the source scar of a landslide).  Each
grid point is offset by the delta with a cosine taper from the full value at
the centre to zero at the cell edge.  The taper keeps the edge free of the
vertical cliff the engine warns against.

This mirrors fnc_heaveTerrainPoints (frost heave) and fnc_craterTerrainPoints
(craters): the same setTerrainHeight point-array contract with a different
profile.

Engine limits, recorded honestly: setTerrainHeight stores every change in the
JIP queue and does NOT remove a change that restores the default value.  A
repeated deformation cycle would grow the JIP queue without bound, and extreme
changes can make a terrain section invisible or throw a walking unit.  So the
caller must apply at most one deformation per cell and must clamp the delta to
a modest magnitude.

Input:  [_centreASL, _radiusM, _deltaM, _stepM] - cell centre (ASL), cell
        radius (m), vertical delta (m, positive raises), grid step (m).
Output: [[x, y, z], ...] - one entry per grid point (empty on bad input).
Public: No
*/

params [
    ["_centre", [0, 0, 0], [[]]],
    ["_radius", 10, [0]],
    ["_delta", 0.2, [0]],
    ["_step", 2, [0]]
];

if (_radius <= 0 || _step <= 0 || _delta == 0) exitWith { [] };

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
            // Cosine taper: full delta at the centre, zero at the edge.
            private _weight = 0.5 * (1 + cos (180 * (_r / _radius)));
            _points pushBack [_cx + _dx, _cy + _dy, _cz + (_delta * _weight)];
        };
    };
};

_points
