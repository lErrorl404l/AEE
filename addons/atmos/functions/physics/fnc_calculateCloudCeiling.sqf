#include "..\..\script_component.hpp"

/*
Compute cloud base height (Lifting Condensation Level) from ambient
temperature and relative humidity using the Espy formula.

Uses a simplified Magnus approximation for dew point.

Sets  QGVAR(cloudCeiling_m).
Returns cloud ceiling in metres.
*/

// ─── Inputs ──────────────────────────────────────────────────────────────
private _temp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if (isNil "_temp") then { _temp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15]; };

private _rh = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if (isNil "_rh") then { _rh = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50]; };

private _overcast = overcast;
if (isNil "_overcast") then { _overcast = 0; };

// ─── Dew point (simplified Magnus) ───────────────────────────────────────
// Td ≈ T - (100 - RH) / 5
private _td = _temp - (100 - _rh) / 5;

// ─── LCL height via Espy formula ─────────────────────────────────────────
// LCL (m) = 125 × (T - Td)
private _ceiling = 125 * (_temp - _td);

// ─── Overcast-based adjustments ──────────────────────────────────────────
// Sparse cloud — no defined ceiling
if (_overcast < 0.2) then { _ceiling = _ceiling max 5000; };

// Fully overcast + near-saturated — low stratus deck
if (_overcast > 0.9 && (_rh > 95)) then { _ceiling = _ceiling min 100; };

// ─── Clamp ───────────────────────────────────────────────────────────────
_ceiling = 0 max _ceiling min 5000;

// ─── Store & return ──────────────────────────────────────────────────────
missionNamespace setVariable [QEGVAR(core,cloudCeiling_m), _ceiling];
_ceiling
