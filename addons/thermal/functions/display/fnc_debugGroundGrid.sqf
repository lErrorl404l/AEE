#include "..\..\script_component.hpp"
/*
In-game TI-visible ground-tile grid (issue #204).

Spawns a 5x5 grid of runway_beton proxy planes (the land_decal road
pieces that render into the terrain surface pass TI mode samples - the
verified TI-visible path, see fnc_debugRoadTest).  Each tile is painted
with a feathered heat tile at a smooth radial gradient: hot at the
centre, cold at the edge.  Tiles overlap (scale 1.3x spacing) so the
feathered edges blend.

Usage (debug console):
    [] call aee_thermal_fnc_debugGroundGrid;
*/
params [["_lifetime", 120, [0]], ["_radius", 12, [0]], ["_grid", 5, [0]]];
private _centre = getPosATL player;
_centre set [2, 0];

private _step = (2 * _radius) / (_grid - 1);
// runway_beton natural size is ~15m; scale ~0.35 gives a 5m tile.
// This is the tile footprint, NOT the grid step (the step*1.3 bug
// scaled each tile to ~8x, merging the whole grid into one road).
private _tileScale = 0.35;
private _tiles = [];
for "_y" from 0 to (_grid - 1) do {
    for "_x" from 0 to (_grid - 1) do {
        private _dx = (_x - (_grid - 1) / 2) * _step;
        private _dy = (_y - (_grid - 1) / 2) * _step;
        private _pos = [_centre select 0 + _dx, _centre select 1 + _dy, 0];
        // radial heat: centre HOT (7) -> edges cold (0)
        private _dist = sqrt (_dx * _dx + _dy * _dy) / _radius;
        private _heat = round (7 * (1 - (_dist min 1)));
        private _tile = createSimpleObject ["a3\roads_f\runway\runway_beton_F.p3d", _pos];
        _tile setDir (random 360);
        _tile setObjectScale _tileScale;
        _tile setObjectTexture [0, format ["\z\aee\addons\thermal\data\ground\ground_heat_%1.paa", _heat]];
        _tiles pushBack _tile;
    };
};

systemChat format ["AEE ground grid: %1x%1 road-proxy tiles, radius %2m, %3s", _grid, _radius, _lifetime];

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
