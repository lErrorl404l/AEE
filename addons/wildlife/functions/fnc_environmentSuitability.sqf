#include "..\script_component.hpp"

/*
Habitat suitability kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It scores one species group against one environment sample from its own
habitat weights, so a cricket on concrete and a woodland bird over a treeless
apron score low, and a shorebird scores on water.  A missing factor field is
a weight of 0, never an error.  The result is clamped 0 to 1.

The surface factor comes from the material votes: the cold materials
(concrete, asphalt, metal, glass, water) do not warm a basking group, so its
surface score is the fraction of the votes that are not cold.

Arguments:
  0: Array - the environment sample
             [foliageFrac, surfaceVotes, waterFrac, structureFrac, meanElev]
             where surfaceVotes is an array of [materialClass, count] rows
  1: Array - the habitat weights [foliage, surface, water, structures]

Returns:
  Number - the suitability, 0 to 1
*/

params [
    ["_environment", [], [[]]],
    ["_habitatRules", [], [[]]]
];

if (_environment isEqualTo []) exitWith { 0 };
if (_habitatRules isEqualTo []) exitWith { 0 };

private _foliage = 0;
private _votes = [];
private _water = 0;
private _structure = 0;
if ((count _environment) >= 1) then { _foliage = _environment select 0; };
if ((count _environment) >= 2) then { _votes = _environment select 1; };
if ((count _environment) >= 3) then { _water = _environment select 2; };
if ((count _environment) >= 4) then { _structure = _environment select 3; };

private _wFoliage = 0;
private _wSurface = 0;
private _wWater = 0;
private _wStructure = 0;
if ((count _habitatRules) >= 1) then { _wFoliage = (_habitatRules select 0) max 0; };
if ((count _habitatRules) >= 2) then { _wSurface = (_habitatRules select 1) max 0; };
if ((count _habitatRules) >= 3) then { _wWater = (_habitatRules select 2) max 0; };
if ((count _habitatRules) >= 4) then { _wStructure = (_habitatRules select 3) max 0; };

// The warm fraction of the surface votes: 1 minus the cold material share.
private _total = 0;
private _cold = 0;
for "_v" from 0 to ((count _votes) - 1) do {
    private _vote = _votes select _v;
    if ((count _vote) >= 2) then {
        private _material = toLower (_vote select 0);
        private _count = (_vote select 1) max 0;
        _total = _total + _count;
        if ((_material == "concrete") || (_material == "asphalt") || (_material == "metal") || (_material == "glass") || (_material == "water")) then {
            _cold = _cold + _count;
        };
    };
};
private _surfaceScore = 0.5;
if (_total > 0) then { _surfaceScore = (_total - _cold) / _total; };

private _denom = _wFoliage + _wSurface + _wWater + _wStructure;
if (_denom <= 0) exitWith { 0 };

private _score = (
    (_wFoliage * (((_foliage max 0) min 1)))
    + (_wSurface * _surfaceScore)
    + (_wWater * (((_water max 0) min 1)))
    + (_wStructure * (((_structure max 0) min 1)))
) / _denom;

((_score max 0) min 1)
