#include "..\script_component.hpp"

/*
Fauna spawn and cull budget kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The fauna
driver calls it once per candidate position per tick and gets the three
decisions it needs.  The kernel owns no object and no side effect.

Spawn when the object is inside the spawn radius and the live count is below
the cap.  Despawn when the object is outside the despawn radius.  The
remaining allowance is the distance to the cap, never negative.

Arguments:
  0: Number - the distance to the object, metres
  1: Number - the spawn radius, metres
  2: Number - the despawn radius, metres
  3: Number - the live fauna count
  4: Number - the hard cap

Returns:
  Array - [allowed, shouldSpawn, shouldDespawn]
*/

params [
    ["_distance", 0, [0]],
    ["_spawnRadius", 350, [0]],
    ["_despawnRadius", 600, [0]],
    ["_liveCount", 0, [0]],
    ["_cap", 16, [0]]
];

private _allowed = ((_cap - _liveCount) max 0);

private _shouldSpawn = false;
if ((_distance < _spawnRadius) && (_liveCount < _cap)) then {
    _shouldSpawn = true;
};

private _shouldDespawn = false;
if (_distance > _despawnRadius) then {
    _shouldDespawn = true;
};

[_allowed, _shouldSpawn, _shouldDespawn]
