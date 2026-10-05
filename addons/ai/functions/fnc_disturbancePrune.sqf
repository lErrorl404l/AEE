#include "..\script_component.hpp"

/*
Disturbance prune kernel (reusable AI substrate).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Drops every
cell older than the age horizon.  When the survivors still exceed the cap it
keeps the cap cells with the largest decayed magnitude.  The decay reuses
fnc_stimulusDecay with the stimulus half-life.  Deterministic, so two
machines with the same field and the same time prune to the same field.

The cap and the horizon are the field owner's policy and arrive as
arguments.  The cell size, the half-life, the horizon and the cap are
modelling choices, UNSOURCED.  See the per-constant register in the
wildlife-ambience dossier.

Arguments:
  0: Array - the field, an array of [key, magnitude, time] entries
  1: Number - the current time, seconds
  2: Number - the cell cap
  3: Number - the age horizon, seconds

Returns:
  Array - the pruned field
*/

params [
    ["_cells", [], [[]]],
    ["_now", 0, [0]],
    ["_cap", 256, [0]],
    ["_horizon", 120, [0]]
];

private _count = count _cells;
private _fresh = [];

for "_i" from 0 to (_count - 1) do {
    private _entryAge = _cells select _i;
    if ((_now - (_entryAge select 2)) <= _horizon) then {
        _fresh pushBack _entryAge;
    };
};

private _freshCount = count _fresh;
if (_freshCount <= _cap) exitWith { _fresh };
if (_cap < 1) exitWith { [] };

private _scores = [];
for "_i" from 0 to (_freshCount - 1) do {
    private _entryScore = _fresh select _i;
    private _decayed = [_entryScore select 1, _now - (_entryScore select 2), AI_STIMULUS_HALF_LIFE] call FUNC(stimulusDecay);
    _scores pushBack _decayed;
};

_scores sort true;

private _cutoff = _scores select (_freshCount - _cap);
private _out = [];
private _kept = 0;

for "_i" from 0 to (_freshCount - 1) do {
    if (_kept < _cap) then {
        private _entryKeep = _fresh select _i;
        private _scoreKeep = [_entryKeep select 1, _now - (_entryKeep select 2), AI_STIMULUS_HALF_LIFE] call FUNC(stimulusDecay);
        if (_scoreKeep >= _cutoff) then {
            _out pushBack _entryKeep;
            _kept = _kept + 1;
        };
    };
};

_out
