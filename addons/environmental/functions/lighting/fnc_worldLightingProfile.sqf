#include "..\..\script_component.hpp"

/*
Map a lighting class and the overcast fraction to four bounded run-time scales.

The class table is keyed by CLIMATE CLASS, never by map.  Every value is an
UNSOURCED aesthetic proxy chosen for the eye.

Arguments:
  0: worldClass  string from fnc_worldLightingClass (default "TEMPERATE")
  1: overcast    engine overcast fraction 0..1 (number)

Return: [nightFactor, starScale, grainScale, hazeScale].
*/

params [
    ["_worldClass", "TEMPERATE", [""]],
    ["_overcast", 0, [0]]
];

private _nightFactor = 0.7;
private _starScale = 1.0;
private _grainScale = 1.0;
private _hazeScale = 0.5;

if (_worldClass == "POLAR") then {
    _nightFactor = 1.0;
    _starScale = 1.30;
    _grainScale = 0.60;
    _hazeScale = 0.20;
};
if (_worldClass == "SUBARCTIC") then {
    _nightFactor = 0.9;
    _starScale = 1.20;
    _grainScale = 0.70;
    _hazeScale = 0.30;
};
if (_worldClass == "MONTANE") then {
    _nightFactor = 0.9;
    _starScale = 1.30;
    _grainScale = 0.70;
    _hazeScale = 0.30;
};
if (_worldClass == "TEMPERATE_COOL") then {
    _nightFactor = 0.8;
    _starScale = 1.10;
    _grainScale = 0.90;
    _hazeScale = 0.40;
};
if (_worldClass == "MEDITERRANEAN") then {
    _nightFactor = 0.6;
    _starScale = 1.15;
    _grainScale = 0.80;
    _hazeScale = 0.40;
};
if (_worldClass == "ARID") then {
    _nightFactor = 0.5;
    _starScale = 1.25;
    _grainScale = 0.60;
    _hazeScale = 0.80;
};
if (_worldClass == "TROPICAL") then {
    _nightFactor = 0.6;
    _starScale = 0.90;
    _grainScale = 1.10;
    _hazeScale = 0.70;
};
if (_worldClass == "TROPICAL_HUMID") then {
    _nightFactor = 0.5;
    _starScale = 0.80;
    _grainScale = 1.20;
    _hazeScale = 0.90;
};
if (_worldClass == "MARITIME") then {
    _nightFactor = 0.7;
    _starScale = 0.95;
    _grainScale = 1.10;
    _hazeScale = 0.70;
};

// Overcast response: cloud hides stars and lifts haze and grain.
_hazeScale = (_hazeScale * (1 + _overcast)) min 1.5;
_starScale = (_starScale * (1 - 0.5 * _overcast)) max 0.2;
_grainScale = (_grainScale * (0.5 + _overcast)) min 1.5;
_nightFactor = (_nightFactor * (1 + 0.25 * _overcast)) min 1.0;

[_nightFactor max 0, _starScale max 0, _grainScale max 0, _hazeScale max 0]
