#include "..\script_component.hpp"

/*
Visibility reduction modifier from precipitation (0.05–1.0).

Computes a multiplier applied to visual range:
  1.0  = clear (no reduction)
  0.05 = near-zero visibility (heavy rain/snow combined with fog)

Rain rate drives piecewise linear reduction:
  • 0 mm/h         → 1.0   (no reduction)
  • 0–2 mm/h       → 1.0–0.6  (light rain)
  • 2–10 mm/h      → 0.6–0.3  (moderate rain)
  • >10 mm/h       → 0.3–0.05 (heavy rain)

Snow cover adds a multiplicative 0.7 penalty.  The result is
combined with existing fog density (fog takes the tighter bound).

Stored in QGVAR(precipVisibilityModifier) for consumption by
visual-range and sensor simulation systems.
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith { 0 };  // no unit on dedicated server

// ─── Inputs ────────────────────────────────────────────────────────────
private _rainRate  = rain;
private _fogArray  = missionNamespace getVariable ["ace_fog_currentFog", [0, 0, 0]];
private _fogValue  = _fogArray param [0, 0];
private _snowDepth = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];

if (isNil "_rainRate") then { _rainRate = 0; };

// ─── Rain visibility modifier (piecewise linear) ──────────────────────
private _rainMod = 1.0;

if (_rainRate > 0) then {
    switch (true) do {
        case (_rainRate <= 2): {
            // Light: 1.0 → 0.6
            _rainMod = 1.0 - (_rainRate / 2) * 0.4;
        };
        case (_rainRate <= 10): {
            // Moderate: 0.6 → 0.3
            _rainMod = 0.6 - ((_rainRate - 2) / 8) * 0.3;
        };
        default {
            // Heavy: 0.3 → 0.05 as rate approaches 30 mm/h
            _rainMod = 0.3 - ((_rainRate - 10) / 20) * 0.25;
        };
    };
    _rainMod = _rainMod max 0.05;
};

// ─── Snow penalty ─────────────────────────────────────────────────────
// Snow cover scatters and occludes light, adding to visibility loss
if (_snowDepth > 0) then {
    _rainMod = _rainMod * 0.7;
};

// ─── Combine with existing fog ────────────────────────────────────────
// Fog density already represents a visibility ceiling; use the tighter bound
private _fogMod  = 1 - _fogValue;
private _result  = _rainMod min _fogMod;

// Guard
_result = _result max 0.05 min 1.0;

// ─── Store ─────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(precipVisibilityModifier), _result];

_result
