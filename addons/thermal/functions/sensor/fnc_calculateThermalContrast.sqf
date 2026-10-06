#include "..\..\script_component.hpp"

/*
Thermal contrast coefficient (0-1) for the FLIR/thermal display gain stage,
plus a NETD-based sensor noise floor.

  1.0 = full display contrast
  0.0 = no usable contrast

WHAT THIS COEFFICIENT IS AND IS NOT.  This is a DISPLAY DEGRADATION FACTOR,
not a sensor figure of merit and not a gain.  The engine ALREADY renders the
native thermal image with its own gain; this stage only adds the
environmental degradation the engine does not model, so its clear-air value
is exactly 1.0 and only extreme heat or cold can move it.  It carries NO
weather term of its own: rain absorption, fog scattering and water-vapour
absorption are modelled ONCE, in fnc_calculateAtmosphericTransmission on the
radiance path.  An earlier revision also multiplied rain, fog and humidity
in here, which double-counted the atmosphere.  That is removed.

Physics basis - DEGRADATION ONLY, NO BASE GAIN, NO WEATHER:
  - The ENGINE renders the native thermal image with its own gain, so this
    stage must not add a second one.  Its output is a dimensionless
    degradation factor with a base of exactly 1.0: no extreme heat and no
    cold means no change.  1.0 is also the consumer's declared default
    (fnc_applyThermalVision.sqf:95), so the two agree.
  - The driver is the surface-to-air temperature gap where the ground solve
    has published a surface temperature (EGVAR(core,surfaceTemperature),
    written by fnc_calculateThermalCrossover).  A wide gap above 35 flattens
    the factor; a narrow gap below 5 scales a lowered factor back up.  Where
    no surface temperature is available, the air temperature is the only
    reference and the same thresholds apply to it.
  - The NETD noise floor is a separate, pure kernel, fnc_calculateThermalNoise.
    It is no longer computed here, because its range is a REAL sensor-to-
    target range supplied by the caller, not a global engine read.

COEFFICIENT PROVENANCE.  Every coefficient in the contrast terms is
UNSOURCED.  The thresholds 35 and 5 and the factors 0.7 and 1.2 are declared
display heuristics, not measured values.  They are recorded as UNSOURCED in
the per-constant register (docs/wiki/chapters/sensor-value-audit.md).

Stored in GVAR(currentThermalContrast) (0-1) for query by the display path
(fnc_applyThermalVision.sqf:95).
*/

// ─── Shared inputs ────────────────────────────────────────────────────────
private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_T isEqualType 0) then { _T = 15; };

// Surface-to-air gap where a surface temperature exists.  The default is a
// non-Number sentinel, so an unset variable (a dedicated server before the
// first ground tick, or a scenario with no ground solve) falls back to the
// air temperature as the only reference instead of reading a zero surface.
private _surfaceTemp = missionNamespace getVariable [QEGVAR(core,surfaceTemperature), ""];
private _gap = if (_surfaceTemp isEqualType 0) then { _surfaceTemp - _T } else { _T };

// ─── Base contrast ────────────────────────────────────────────────────────
// No base gain is derived here.  The engine renders the native thermal
// image with its own gain, and this stage adds only the environmental
// degradation the engine does not model.  The base is therefore exactly 1.0
// (full, undegraded display contrast), which is also the consumer's
// declared default in fnc_applyThermalVision.sqf:95.  In clear conditions
// the published value is 1.0 and no second amplifier exists.
private _contrast = 1.0;

// ─── Extreme heat — gradient flattens ────────────────────────────────────
// UNSOURCED thresholds: 35, 10 and 0.7 are declared display heuristics.
if (_gap > 35) then {
    _contrast = _contrast - ((_gap - 35) / 10) * 0.7;
};

// ─── Cold — widened thermal gap ──────────────────────────────────────────
// UNSOURCED coefficients: 5 and 1.2 are declared display heuristics.
if (_gap < 5) then {
    _contrast = (_contrast * 1.2) min 1.0;
};

_contrast = _contrast max 0 min 1;

missionNamespace setVariable [QGVAR(currentThermalContrast), _contrast];
