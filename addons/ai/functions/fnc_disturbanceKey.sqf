#include "..\script_component.hpp"

/*
Disturbance cell key kernel (reusable AI substrate).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Maps a
position to its grid cell as the integer pair
[floor(x / cellSize), floor(y / cellSize)].  Deterministic, so two machines
at the same position land in the same cell.  The 50 m cell size is a
modelling choice, UNSOURCED.

Arguments:
  0: Array - position [x, y] or [x, y, z]
  1: Number - cell size, metres

Returns:
  Array - the cell index pair [cx, cy]
*/

params [
    ["_pos", [0, 0, 0], [[]]],
    ["_cellSize", 50, [0]]
];

private _size = (_cellSize max 0.000001);

[floor ((_pos select 0) / _size), floor ((_pos select 1) / _size)]
