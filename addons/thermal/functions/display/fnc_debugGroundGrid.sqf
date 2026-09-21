#include "..\..\script_component.hpp"
/*
In-game TI-visible ground-tile test (issue #204).

Spawns a 5x5 grid of drop-billboard ground decals (the engine's own
surface-decal renderer - the same one bullet holes and footprints use,
which the TI pass reads).  Each tile is painted with a feathered heat
tile at a smooth radial gradient: hot at the centre, cold at the edge.

The object-decal route (Land_DirtPatch_03_F) failed because those
render as terrain projections the TI pass ignores.  This tests whether
the drop-billboard path enters the thermal image.

Usage (debug console):
    [] call aee_thermal_fnc_debugGroundGrid;
*/
params [["_lifetime", 60, [0]], ["_radius", 12, [0]], ["_grid", 5, [0]]];
private _centre = getPosATL player;
_centre set [2, 0];

private _step = (2 * _radius) / (_grid - 1);
for "_y" from 0 to (_grid - 1) do {
    for "_x" from 0 to (_grid - 1) do {
        private _dx = (_x - (_grid - 1) / 2) * _step;
        private _dy = (_y - (_grid - 1) / 2) * _step;
        private _pos = [_centre select 0 + _dx, _centre select 1 + _dy, 0];
        // radial heat: distance from centre -> 0 hot .. 1 cold
        private _dist = sqrt (_dx * _dx + _dy * _dy) / _radius;
        private _heat = round (7 * (_dist min 1));
        private _tile = format ["\z\aee\addons\thermal\data\ground\ground_heat_%1.paa", _heat];
        private _size = _step * 1.3;   // overlap: feathered edges blend
        drop [
            [_tile, 1, 0, 1, 0],
            "",
            "Billboard",
            0.5,
            _lifetime,
            _pos,
            [0, 0, 0],
            0,
            1,
            1,
            0.5,
            [_size, _size],
            [[1, 0.10, 0.20, 0.9], [1, 0.10, 0.20, 0]],
            [1000, 0],
            0,
            0,
            "",
            "",
            objNull,
            0,
            true,
            0
        ];
    };
};

systemChat format ["AEE ground grid: %1x%1 tiles, radius %2m", _grid, _radius];

[]
