#include "..\script_component.hpp"

/*
Habitat-boundary kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It keeps an animal inside its suitable patch.  A group at or above the stay
threshold stays.  Below it the animal moves to the best neighbour, or avoids
the worst neighbour when no neighbour beats it.  A rare excursion lets a
small, seeded, deterministic fraction of the calls leave the patch.  The same
inputs on any machine give the same result.

The caller seeds the animal id with the mission time bin, so the seed already
carries the time.  The integer hash is the exactly-representable pattern
fnc_speciesForBiome used, so two machines agree.  The default exception rate
is UNSOURCED and rare.

Arguments:
  0: Number - the score at the current cell, 0 to 1
  1: Array  - the neighbour scores
  2: Number - the stay threshold, 0 to 1
  3: Number - the animal seed
  4: Number - the excursion rate, 0 to 1

Returns:
  Array - [decision, excursion] with decision 0 stay, 1 move to the best
          neighbour, 2 avoid the worst neighbour
*/

params [
    ["_hereScore", 0, [0]],
    ["_neighbourScores", [], [[]]],
    ["_stayThreshold", 0.5, [0]],
    ["_seed", 0, [0]],
    ["_exceptionRate", 0.02, [0]]
];

private _best = _hereScore;
private _worst = _hereScore;
for "_i" from 0 to ((count _neighbourScores) - 1) do {
    private _score = _neighbourScores select _i;
    if (_score > _best) then { _best = _score; };
    if (_score < _worst) then { _worst = _score; };
};

private _decision = 0;
if (_hereScore < _stayThreshold) then {
    if (_best > _hereScore) then {
        _decision = 1;
    } else {
        if (_worst < _hereScore) then { _decision = 2; };
    };
};

private _hash = ((_seed * 101) + 37) mod 997;
if (_hash < 0) then { _hash = -_hash; };
private _roll = (_hash mod 1000) / 1000;

private _excursion = false;
if ((_exceptionRate > 0) && (_roll < _exceptionRate)) then { _excursion = true; };

[_decision, _excursion]
