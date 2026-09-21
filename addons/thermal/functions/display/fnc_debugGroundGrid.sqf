#include "..\..\script_component.hpp"
/*
In-game feathered ground-tile test (issue #204).

Spawns a 5x5 grid of Land_DirtPatch_03_F decals around the player,
each painted with a feathered heat tile (ground_heat_XX.paa) at a
smooth radial gradient: hot at the centre, cold at the edge.  The
feathered alpha of each tile should blend with its neighbours - the
transition reads as a continuous ramp, not a grid seam.

Usage (debug console):
    [] call aee_thermal_fnc_debugGroundGrid;

Cleans up after _lifetime seconds.
*/
params [["_lifetime", 60, [0]], ["_radius", 12, [0]], ["_grid", 5, [0]]];
private _centre = getPosATL player;
_centre set [2, 0];

private _tiles = [];
private _step = (2 * _radius) / (_grid - 1);
private _tileScale = _step * 1.3;   // overlap: feathered edges blend
private _heatTiles = [];
for "_i" from 0 to 7 do {
    _heatTiles pushBack format ["\z\aee\addons\thermal\data\ground\ground_heat_%1.paa", _i];
};

for "_y" from 0 to (_grid - 1) do {
    for "_x" from 0 to (_grid - 1) do {
        private _dx = (_x - (_grid - 1) / 2) * _step;
        private _dy = (_y - (_grid - 1) / 2) * _step;
        private _pos = [_centre select 0 + _dx, _centre select 1 + _dy, 0];
        // radial heat: distance from centre -> 0 hot .. 1 cold
        private _dist = sqrt (_dx * _dx + _dy * _dy) / _radius;
        private _heat = round (7 * (_dist min 1));
        private _tile = createVehicle ["Land_DirtPatch_03_F", _pos, [], 0, "CAN_COLLIDE"];
        _tile setDir (random 360);
        _tile setObjectScale _tileScale;
        // TI-readable material FIRST (same as fnc_spawnHeatStain): the
        // decal's own StageTI would render cold grey in the TI pass and
        // hide the painted tile.  The FPN rvmat's white Stage1 lets the
        // heat tile show, perlinNoise Stage2 adds the mottle.
        _tile setObjectMaterial [0, "\z\aee\addons\thermal\data\ti_fpn.rvmat"];
        _tile setObjectTexture [0, _heatTiles select _heat];
        _tiles pushBack _tile;
    };
};

systemChat format ["AEE ground grid: %1 tiles at heat %2..%3", count _tiles, _heatTiles select 0, _heatTiles select 7];

[
    {
        params ["_tiles"];
        { if (!isNull _x) then { deleteVehicle _x }; } forEach _tiles;
        systemChat "AEE ground grid: cleaned up";
    },
    [_tiles],
    _lifetime
] call CBA_fnc_waitAndExecute;
