#include "..\..\script_component.hpp"

/*
Visibility reduction modifier from precipitation (0.05–1.0).

Computes a multiplier applied to visual range:
  1.0  = clear (no reduction)
  0.05 = near-zero visibility (heavy rain/snow combined with fog)

Rain rate drives reduction with the Atlas (1954) power law:
  • Extinction coefficient: σ = 0.21 · R^0.74  (km⁻¹)
  • Koschmieder visual range: V = 3.912 / σ  (km)
  • Modifier: V / 20, clamped to [0.05, 1.0]

The Arma 3 rain value is abstract (0..1), not mm/h.  Map it to a rain
rate with _rainMMH = rain * 25, so 1.0 rain equals 25 mm/h (heavy rain).

Snow cover adds a multiplicative 0.7 penalty.  The result is
combined with existing fog density (fog takes the tighter bound).

Stored in QGVAR(precipVisibilityModifier) for consumption by
visual-range and sensor simulation systems.
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith { 0 };  // no unit on dedicated server

// ─── Inputs ────────────────────────────────────────────────────────────
private _rainRate  = ([] call EFUNC(core,getSmoothedWeather)) select 0;
private _fogValue  = missionNamespace getVariable [QEGVAR(core,currentFogDensity), 0];
private _snowDepth = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];

if (isNil "_rainRate") then { _rainRate = 0; };

// ─── Rain visibility modifier (Atlas 1954 extinction) ─────────────────
// Abstract engine rain (0..1) maps to mm/h: 1.0 rain = 25 mm/h heavy rain.
private _rainMMH = _rainRate * 25;

private _rainMod = 1.0;

if (_rainMMH > 0) then {
    // Extinction coefficient σ = 0.21 · R^0.74 (km⁻¹), R in mm/h.
    private _sigma = 0.21 * (_rainMMH ^ 0.74);

    // Koschmieder visual range V = 3.912 / σ (km).
    private _visualRangeKm = 3.912 / _sigma;

    // Fraction of the 20 km clear-day baseline, clamped.
    _rainMod = (_visualRangeKm / 20) max 0.05 min 1.0;
};

// ─── Snow penalty ─────────────────────────────────────────────────────
// Snow cover scatters and occludes light, adding to visibility loss
if (_snowDepth > 0) then {
    _rainMod = _rainMod * (missionNamespace getVariable [QGVAR(snowVisibilityPenalty), 0.7]);
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
