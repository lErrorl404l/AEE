#include "..\script_component.hpp"

/*
Classifies the surface at a given position into one of:
  Normal   — dry, temperate ground
  Mud      — wet soil from recent rainfall
  Dusty    — loose dry soil mobilised by wind (arid biomes)
  Frozen   — sub-zero ground with moisture
  Snow     — snow/ice coverage

Stored in GVAR(groundState) for use by visual effects, vehicle
traction modifiers, and concealment calculations.
*/

params [["_posASL", [], [[]]]];

// ─── Rain history (leaky integrator) ──────────────────────────────────
// Tracks recent precipitation; decays 3 %/tick (~5 min half-life at 5 s ticks)
private _rainAccum = missionNamespace getVariable [QEGVAR(core,rainAccum), 0];
_rainAccum = (_rainAccum * 0.97) + (rain * 0.03);
missionNamespace setVariable [QEGVAR(core,rainAccum), _rainAccum];

// ─── Position ─────────────────────────────────────────────────────────
private _pos2D = [];
if (_posASL isEqualTo []) then {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player") then { _pos2D = getPos _player; };
} else {
    _pos2D = _posASL select [0, 2];
};

// ─── Inputs ───────────────────────────────────────────────────────────
private _T = EGVAR(core,currentTemperature);
private _biome = EGVAR(core,biome);
private _windSpeed = vectorMagnitude wind;

private _surface = "";
if (_pos2D isNotEqualTo []) then {
    _surface = toLower (surfaceType _pos2D);
};

// ─── Classification (most specific → least) ──────────────────────────
private _state = "Normal";

if (_surface in ["#gdtsnow","#gdtice","#gdtglacier","#gdttundra"]) then {
    _state = "Snow";
} else {
    if (!isNil "_T" && (_T < -2) && (_rainAccum > 0.05)) then {
        _state = "Frozen";
    } else {
        if (_rainAccum > 0.2 && (!isNil "_T") && (_T > 2)) then {
            _state = "Mud";
        } else {
            if (!isNil "_biome" && (_biome in ["BWh","BWk","BSh","BSk"]) && (_windSpeed > 5) && (_rainAccum < 0.05)) then {
                _state = "Dusty";
            };
        };
    };
};

missionNamespace setVariable [QEGVAR(core,groundState), _state];
