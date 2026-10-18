#include "..\..\script_component.hpp"

/*
Compute cloud base height (Lifting Condensation Level) from ambient
temperature and relative humidity using the Espy formula, and the
convective cloud top from the parcel model.

Uses a simplified Magnus approximation for dew point.

Sets  QGVAR(cloudCeiling_m) - the cloud BASE
      QEGVAR(core,cloudTop_m) - the cloud TOP (level of neutral buoyancy)
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

// ─── Cloud top (issue #238) ──────────────────────────────────────────────
// The base is the LCL above.  The lightning ice-phase gate needs the cloud
// TOP, not the base: the depth of the mixed-phase region is what separates
// charge, and the base is clamped to 5000 m so it can never reach the gate.
// The top is the level of neutral buoyancy from the parcel model (parcel
// theory; Holton, An Introduction to Dynamic Meteorology, s.2.9), the same
// model fnc_calculateCloudDevelopment already runs.  A stable sky has no
// positive-buoyancy layer, so the top falls back to the base and the gate
// stays closed.
private _ps = missionNamespace getVariable [QEGVAR(core,currentPressure), 1013.25];
if !(_ps isEqualType 0) then { _ps = 1013.25; };
private _parcel = [_temp, _rh, _ps] call FUNC(calculateParcelCape);
private _cloudTop = ((_parcel select 3) max (_parcel select 1) max _ceiling) min 16000;
missionNamespace setVariable [QEGVAR(core,cloudTop_m), _cloudTop];

// ─── Store & return ──────────────────────────────────────────────────────
missionNamespace setVariable [QEGVAR(core,cloudCeiling_m), _ceiling];
_ceiling
