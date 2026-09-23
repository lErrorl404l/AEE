#include "..\..\script_component.hpp"

/*
Biome boundary smoothing (issue: the biomeTransitionRadius setting).

The biome sampler is per-position and discrete: a desert tile returns BWh
and the grass beside it returns Cfb, with a hard edge between them. Real
climatic boundaries are not lines. Vegetation, soil and the surface energy
balance change gradually, so a transition zone reads as a blend of both
neighbours rather than either one alone.

This samples the biome in a ring at the user's radius and returns the
DOMINANT one. The effect is that a position near a boundary resolves to
whichever biome actually surrounds it, instead of to whichever tile it
happens to stand on: a lone grass patch in a desert reads as desert,
which is the climatic truth of its neighbourhood.

The radius is the width of the transition zone, so the setting decides how
wide the boundary is, not what the biome is. A radius of 0 disables the
smoothing and the sampler answers for the exact tile.

Argument:
  0: position (ARRAY, PositionASL, default [])

Returns the dominant biome code, or the exact-tile code when the radius is
zero.
*/

params [["_posASL", [], [[]]]];
if (count _posASL < 2) exitWith { "" };
if (count _posASL < 3) then { _posASL = [_posASL select 0, _posASL select 1, 0]; };

private _radius = missionNamespace getVariable [QEGVAR(core,biomeTransitionRadius), 5000];
if !(_radius isEqualType 0) then { _radius = 5000; };

// The exact tile is the answer when smoothing is off.
if (_radius <= 0) exitWith {
    [_posASL] call EFUNC(environmental,getBiomeAtPosition)
};

// ─── Sample the ring and count the votes ─────────────────────────────────
// Eight points at the radius, so the neighbourhood is sampled evenly and
// the dominant biome is the one that actually surrounds the position.
private _x = _posASL select 0;
private _y = _posASL select 1;
private _z = _posASL select 2;

private _votes = createHashMap;
private _count = 0;
for "_i" from 0 to 7 do {
    private _angle = _i * 45;
    private _rad = _angle * (pi / 180);
    private _sample = [
        _x + (_radius * sin _rad),
        _y + (_radius * cos _rad),
        _z
    ];
    private _code = [_sample] call EFUNC(environmental,getBiomeAtPosition);
    if (_code != "") then {
        _votes set [_code, (_votes getOrDefault [_code, 0]) + 1];
        _count = _count + 1;
    };
};

if (_count == 0) exitWith {
    [_posASL] call EFUNC(environmental,getBiomeAtPosition)
};

// ─── The dominant biome, with the centre breaking a tie ──────────────────
// A tie means the position is exactly on the boundary, and then the tile
// underfoot decides. That keeps the answer stable and explainable.
private _best = "";
private _bestVotes = -1;
private _tie = false;
{
    if (_x > _bestVotes) then {
        _best = _y;
        _bestVotes = _x;
        _tie = false;
    } else {
        if (_x == _bestVotes) then { _tie = true; };
    };
} forEach _votes;

if (_tie) exitWith {
    [_posASL] call EFUNC(environmental,getBiomeAtPosition)
};

_best
