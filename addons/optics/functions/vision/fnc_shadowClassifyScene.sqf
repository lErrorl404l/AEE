#include "..\..\script_component.hpp"

/*
Shadow scene classification (aee-workshop-copy item 6, part 1).

Re-derived from fn_calculatedepth.sqf in Adaptive Shadows (Workshop
3792830104).  The mod publishes no licence, so this is a re-derived numeric
kernel, not copied code.  No mod content is copied.  The weighted-percentile
fractions (near 0.50, base 0.65, far 0.75), the low-screen terrain weight
0.30, the far threshold factor 2.3 and the coherent-neighbour radius 0.09 are
UNSOURCED heuristics; they come from the mod's own tuning, not a published
measurement.  The scene thresholds are also UNSOURCED.

The kernel is PURE: no missionNamespace, no GVAR or EGVAR, no engine command.
The driver does the engine sampling and passes the samples in.  The loops are
`for` loops, not `forEach`, so every accumulator stays in the kernel's own
scope (a block lambda is a separate scope in the test interpreter).

Sample form (produced by the driver):
  [distance, weight, screenX, screenY, kind]
  kind 0 = object, 1 = terrain, 2 = sky, 3 = no-hit

Arguments:
  0: Array  - samples in the form above
  1: Number - fallback depth used when no sample is usable
  2: Array  - context [ceilingHit, horizontalHits, closeHits,
              averageContextDistance, probeCount] from the driver's probe
  3: Number - effective maximum depth in metres, the clamp and far bound
  4: Number - opening sensitivity, a percentage 3..50
  5: Number - far scene influence, a percentage 0..100

Returns:
  [depth, scene, nearDepth, farDepth, openingCoverage, interiorScore,
   terrainCoverage]
*/

params [
    ["_samples", [], [[]]],
    ["_fallback", 0, [0]],
    ["_context", [false, 0, 0, 12, 0], [[]]],
    ["_effectiveMax", 0, [0]],
    ["_openingSensitivity", 12, [0]],
    ["_farSceneInfluence", 75, [0]]
];

if (_samples isEqualTo []) exitWith {
    [_fallback, "UNKNOWN", _fallback, _fallback, 0, 0, 0]
};

// Weighted percentile over [value, weight] pairs.  `_ordered sort true`
// sorts ascending by the pair's first element (the distance).
private _weightedPercentile = {
    params ["_values", "_fraction", "_default"];

    if (count _values == 0) exitWith {_default};

    private _ordered = _values + [];
    _ordered sort true;

    private _totalWeight = 0;
    for "_i" from 0 to ((count _ordered) - 1) do {
        _totalWeight = _totalWeight + (((_ordered select _i) select 1) max 0);
    };

    if (_totalWeight <= 0) exitWith {_default};

    private _threshold = _totalWeight * ((_fraction max 0) min 1);
    private _accumulated = 0;
    private _result = (_ordered select -1) select 0;
    private _selected = false;

    for "_i" from 0 to ((count _ordered) - 1) do {
        if (!_selected) then {
            private _pair = _ordered select _i;
            _accumulated = _accumulated + ((_pair select 1) max 0);
            if (_accumulated >= _threshold) then {
                _result = _pair select 0;
                _selected = true;
            };
        };
    };

    _result
};

private _nearPairs = [];
private _totalDirectionalWeight = 0;
private _objectWeight = 0;
private _terrainWeight = 0;

for "_i" from 0 to ((count _samples) - 1) do {
    private _sample = _samples select _i;
    private _distance = _sample select 0;
    private _weight = _sample select 1;
    private _screenY = _sample select 3;
    private _kind = _sample select 4;

    private _adjustedWeight = _weight max 0;
    if (_kind == 1 && _screenY > 0.62) then {
        _adjustedWeight = _adjustedWeight * 0.30;
    };

    if (_kind != 3) then {
        _totalDirectionalWeight = _totalDirectionalWeight + _adjustedWeight;
    };

    if (_kind == 0 || _kind == 1) then {
        _nearPairs pushBack [_distance max 0, _adjustedWeight];
        if (_kind == 0) then {
            _objectWeight = _objectWeight + _adjustedWeight;
        } else {
            _terrainWeight = _terrainWeight + _adjustedWeight;
        };
    };
};

private _nearDepth = [_nearPairs, 0.50, _fallback] call _weightedPercentile;
private _baseDepth = [_nearPairs, 0.65, _nearDepth] call _weightedPercentile;
private _farThreshold = ((_nearDepth * 2.3) max 25) min (_effectiveMax max 25);

private _farCandidates = [];
for "_i" from 0 to ((count _samples) - 1) do {
    private _sample = _samples select _i;
    private _distance = _sample select 0;
    private _weight = _sample select 1;
    private _screenX = _sample select 2;
    private _screenY = _sample select 3;
    private _kind = _sample select 4;

    private _adjustedWeight = _weight max 0;
    if (_kind == 1 && _screenY > 0.62) then {
        _adjustedWeight = _adjustedWeight * 0.30;
    };

    if (
        _kind == 2
        || ((_kind == 0 || _kind == 1) && _distance >= _farThreshold)
    ) then {
        _farCandidates pushBack [_distance, _adjustedWeight, _screenX, _screenY, _kind];
    };
};

private _farPairs = [];
private _coherentFarWeight = 0;
private _centerFarWeight = 0;

for "_candidateIndex" from 0 to ((count _farCandidates) - 1) do {
    private _candidate = _farCandidates select _candidateIndex;
    private _distance = _candidate select 0;
    private _weight = _candidate select 1;
    private _screenX = _candidate select 2;
    private _screenY = _candidate select 3;
    private _hasNeighbour = false;

    for "_otherIndex" from 0 to ((count _farCandidates) - 1) do {
        if (_otherIndex != _candidateIndex) then {
            private _other = _farCandidates select _otherIndex;
            private _deltaX = (_other select 2) - _screenX;
            private _deltaY = (_other select 3) - _screenY;
            if (((_deltaX * _deltaX) + (_deltaY * _deltaY)) <= 0.09) then {
                _hasNeighbour = true;
            };
        };
    };

    if (_hasNeighbour) then {
        _farPairs pushBack [_distance, _weight];
        _coherentFarWeight = _coherentFarWeight + _weight;

        if (
            _screenX >= 0.24 && _screenX <= 0.76
            && _screenY >= 0.24 && _screenY <= 0.76
        ) then {
            _centerFarWeight = _centerFarWeight + _weight;
        };
    };
};

private _openingCoverage = 0;
if (_totalDirectionalWeight > 0) then {
    _openingCoverage = (_coherentFarWeight / _totalDirectionalWeight) min 1;
};

private _farDepth = [_farPairs, 0.75, _baseDepth] call _weightedPercentile;

private _objectCoverage = 0;
private _terrainCoverage = 0;
if (_totalDirectionalWeight > 0) then {
    _objectCoverage = _objectWeight / _totalDirectionalWeight;
    _terrainCoverage = _terrainWeight / _totalDirectionalWeight;
};

private _contextData = if (count _context >= 5) then {
    _context
} else {
    [false, 0, 0, 12, 0]
};
private _ceilingHit = _contextData select 0;
private _closeHits = _contextData select 2;
private _probeCount = _contextData select 4;

private _horizontalCapacity = ((_probeCount - 1) max 1);
private _contextScore = ([0, 0.45] select _ceilingHit) + (0.55 * ((_closeHits / _horizontalCapacity) min 1));
private _nearFactor = 1 - ((_nearDepth / 40) min 1);
private _screenInterior = _objectCoverage * (0.55 + (0.45 * _nearFactor)) * (1 - _openingCoverage);
private _interiorScore = (_contextScore max (_screenInterior * 0.80)) min 1;

private _sensitivity = (((_openingSensitivity / 100) max 0.03) min 0.50);
private _farInfluence = (((_farSceneInfluence / 100) max 0) min 1);
private _scene = "NEAR";

if (_interiorScore >= 0.62) then {
    if (_openingCoverage >= _sensitivity) then {
        _scene = "OPENING";
    } else {
        if (_centerFarWeight > 0 && {_farDepth >= (_nearDepth * 1.8)}) then {
            _scene = "CORRIDOR";
        } else {
            _scene = "INTERIOR";
        };
    };
} else {
    if (_openingCoverage >= 0.45) then {
        _scene = "OPEN";
    } else {
        if (_objectCoverage >= 0.40 && _openingCoverage >= _sensitivity) then {
            _scene = "URBAN";
        } else {
            if (_openingCoverage >= _sensitivity) then {
                _scene = "MIXED";
            };
        };
    };
};

private _depth = _baseDepth;
if (_farPairs isNotEqualTo [] && (_openingCoverage >= _sensitivity || _scene isEqualTo "CORRIDOR")) then {
    private _coverageFactor = (_openingCoverage / 0.55) min 1;
    private _blend = _coverageFactor * _farInfluence;
    if (_scene isEqualTo "CORRIDOR") then {
        _blend = _blend max (0.35 * _farInfluence);
    };
    _depth = _baseDepth + ((_farDepth - _baseDepth) * _blend);
};

_depth = (_depth max 0) min (_effectiveMax max 0);

[_depth, _scene, _nearDepth, _farDepth, _openingCoverage, _interiorScore, _terrainCoverage]
