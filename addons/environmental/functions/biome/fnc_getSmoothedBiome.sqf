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
//
// Each sample costs a surfaceType query, so the ring is eight terrain
// reads per call, and this runs every environment tick on every machine.
// The answer depends only on where the position sits and on the radius,
// and neither moves while the player stays put. It is cached per 100 m
// cell: the biome boundary is kilometres wide, so a 100 m quantisation is
// far below the feature the ring is measuring.
private _px = _posASL select 0;
private _py = _posASL select 1;
private _pz = _posASL select 2;
private _cellKey = format ["%1_%2_%3",
    floor (_px / 100), floor (_py / 100), round _radius];
private _ringCache = missionNamespace getVariable [QGVAR(biomeRingCache), createHashMap];
if (_cellKey in _ringCache) exitWith { _ringCache get _cellKey };

private _votes = createHashMap;
private _count = 0;
for "_i" from 0 to 7 do {
    private _angle = _i * 45;
    private _rad = _angle * (pi / 180);
    private _sample = [
        _px + (_radius * sin _rad),
        _py + (_radius * cos _rad),
        _pz
    ];
    private _code = [_sample] call EFUNC(environmental,getBiomeAtPosition);
    if (_code != "") then {
        _votes set [_code, (_votes getOrDefault [_code, 0]) + 1];
        _count = _count + 1;
    };
};

if (_count == 0) exitWith {
    private _fallback = [_posASL] call EFUNC(environmental,getBiomeAtPosition);
    _ringCache set [_cellKey, _fallback];
    missionNamespace setVariable [QGVAR(biomeRingCache), _ringCache];
    _fallback
};

// ─── The dominant biome, with the centre breaking a tie ──────────────────
// A tie means the position is exactly on the boundary, and then the tile
// underfoot decides. That keeps the answer stable and explainable.
private _best = "";
private _bestVotes = -1;
private _tie = false;
{
    if (_y > _bestVotes) then {
        _best = _x;
        _bestVotes = _y;
        _tie = false;
    } else {
        if (_y == _bestVotes) then { _tie = true; };
    };
} forEach _votes;

private _result = if (_tie) then {
    [_posASL] call EFUNC(environmental,getBiomeAtPosition)
} else {
    _best
};
_ringCache set [_cellKey, _result];
missionNamespace setVariable [QGVAR(biomeRingCache), _ringCache];

_result
