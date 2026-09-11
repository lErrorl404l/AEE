#include "..\script_component.hpp"

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

if (!EGVAR(core,opticsEnabled)) exitWith {
    missionNamespace setVariable [QGVAR(rainOnOptics), 0];
    0
};

private _rainRate = rain;
if (isNil "_rainRate") then { _rainRate = 0; };

private _droplets = missionNamespace getVariable [QGVAR(rainOnOptics), 0];

if (_rainRate > 0.2) then {
    switch (true) do {
        case (_rainRate > 10): { _droplets = _droplets + 0.01; };
        case (_rainRate > 2):  { _droplets = _droplets + 0.005; };
        default                { _droplets = _droplets + 0.002; };
    };
    _droplets = _droplets min 1;
} else {
    _droplets = (_droplets - 0.02) max 0;
};

missionNamespace setVariable [QGVAR(rainOnOptics), _droplets];

_droplets
