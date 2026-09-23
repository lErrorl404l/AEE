#include "..\..\script_component.hpp"

/*
Rain droplet accumulation on optical lenses (0–1).

Water droplets build up on scope, binocular, and camera lenses during
precipitation, creating a blurred/distorted overlay.

Accumulation:
  • Rain rate > 0.2 mm/h  → +0.002 per tick (light drizzle)
  • Rain rate > 2 mm/h    → +0.005 per tick (moderate rain)
  • Rain rate > 10 mm/h   → +0.01  per tick (heavy downpour)

Decay:
  • Rain rate ≤ 0.2 mm/h  → −0.02 per tick (clears ~4 min)

Stored in QGVAR(rainOnOptics) for consumption by visual overlay systems.
*/

params [];

if (!(missionNamespace getVariable [QEGVAR(core,opticsEnabled), true])) exitWith {
    missionNamespace setVariable [QGVAR(rainOnOptics), 0];
    0
};

private _rainRate = rain;
if (isNil "_rainRate") then { _rainRate = 0; };

private _droplets = missionNamespace getVariable [QGVAR(rainOnOptics), 0];

// Rates are per-tick; scale by the update interval so behaviour is
// interval-independent (5 s baseline).
private _intervalScale = (missionNamespace getVariable [QEGVAR(core,updateInterval), 5]) / 5;
private _accumRate = (missionNamespace getVariable [QGVAR(rainAccumRate), 0.01]) * _intervalScale;
private _decayRate = (missionNamespace getVariable [QGVAR(rainDecayRate), 0.02]) * _intervalScale;

if (_rainRate > 0.2) then {
    switch (true) do {
        case (_rainRate > 10): { _droplets = _droplets + _accumRate; };
        case (_rainRate > 2):  { _droplets = _droplets + (_accumRate / 2); };
        default                { _droplets = _droplets + (_accumRate / 5); };
    };
    _droplets = _droplets min 1;
} else {
    _droplets = (_droplets - _decayRate) max 0;
};

missionNamespace setVariable [QGVAR(rainOnOptics), _droplets];

_droplets
