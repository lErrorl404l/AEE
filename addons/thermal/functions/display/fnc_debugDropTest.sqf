#include "..\..\script_component.hpp"
/*
Isolating drop-billboard visibility (issue #204).

Spawns ONE drop billboard 2m in front of the player, painted with the
mid heat tile.  Reports via systemChat whether it was spawned.  Use in
NORMAL vision first: if the tile renders, the drop path + texture works
and the issue is TI-specific.  If it does not render, the drop call or
the .paa-as-particle-sprite is broken.

Usage (debug console):
    [] call aee_thermal_fnc_debugDropTest;
*/
private _pos = player modelToWorld [0, 2, 0];
_pos set [2, 0];
private _tile = "\z\aee\addons\thermal\data\ground\ground_heat_04.paa";
drop [
    [_tile, 1, 0, 1, 0],
    "",
    "Billboard",
    0.5,
    30,
    _pos,
    [0, 0, 0],
    0,
    1,
    1,
    0.5,
    [3, 3],
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
systemChat format ["AEE drop test: spawned at %1 (%2m in front), 30s", _pos, player distance _pos];

[]
