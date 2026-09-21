#include "..\..\script_component.hpp"
/*
In-game TI-visible ground-tile grid (issue #204) - WORKING mechanism.

The terrain overlay is Land_DirtPatch_03_F decals painted via
setObjectTexture ["usertexture", tile] - the decal's engine-projected
texture hook.  Verified in-game: the painted decal reads DIFFERENTLY in
thermals from the surrounding ground (all other vanilla flat pieces are
material-baked with no paintable slot; the road pieces' tex/mats are
[]; only the usertexture selection on DirtPatch accepts a paint).

Spawns a 5x5 grid of DirtPatch tiles, each painted with a feathered
heat tile at a smooth radial gradient: hot centre (7) fading to cold
edges (0).  Tiles overlap (1.15x scale) so the feathered edges blend.

Usage (debug console):
    [] call aee_thermal_fnc_debugGroundGrid;
*/
params [["_lifetime", 120, [0]], ["_radius", 12, [0]], ["_grid", 5, [0]]];
private _centre = getPosATL player;
_centre set [2, 0];

private _step = (2 * _radius) / (_grid - 1);
// DirtPatch natural size 10x10m; scale 0.55 ~ 5.5m tile footprint.
// 1.15x overlap lets the feathered edges blend into a continuous ramp.
private _tileScale = _step * 0.11;
private _tiles = [];
for "_y" from 0 to (_grid - 1) do {
    for "_x" from 0 to (_grid - 1) do {
        private _dx = (_x - (_grid - 1) / 2) * _step;
        private _dy = (_y - (_grid - 1) / 2) * _step;
        private _pos = [_centre select 0 + _dx, _centre select 1 + _dy, 0];
        // radial heat: centre HOT (7) -> edges cold (0)
        private _dist = sqrt (_dx * _dx + _dy * _dy) / _radius;
        private _heat = round (7 * (1 - (_dist min 1)));
        private _tile = createVehicle ["Land_DirtPatch_03_F", _pos, [], 0, "CAN_COLLIDE"];
        _tile setDir (random 360);
        _tile setObjectScale _tileScale;
        _tile setObjectTexture ["usertexture", format ["\z\aee\addons\thermal\data\ground\ground_heat_%1.paa", _heat]];
        _tiles pushBack _tile;
    };
};

systemChat format ["AEE ground grid: %1x%1 DirtPatch tiles, radius %2m, scale %3", _grid, _radius, _tileScale];

[
    {
        params ["_tiles"];
        { if (!isNull _x) then { deleteVehicle _x }; } forEach _tiles;
        systemChat "AEE ground grid: cleaned up";
    },
    [_tiles],
    _lifetime
] call CBA_fnc_waitAndExecute;

[]
