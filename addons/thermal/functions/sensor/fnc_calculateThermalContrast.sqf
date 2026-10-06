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
  - NETD (Noise Equivalent Temperature Difference) is the temperature
    change that produces a signal equal to the sensor's own noise, that is a
    signal-to-noise ratio of 1.  Modern uncooled microbolometers run ~0.05 C.
    Atmospheric path noise grows with range squared and humidity adds
    water-vapour noise; the noise floor is computed below.

COEFFICIENT PROVENANCE.  Every coefficient in the contrast terms is
UNSOURCED.  The thresholds 35 and 5 and the factors 0.7 and 1.2 are declared
display heuristics, not measured values.  They are recorded as UNSOURCED in
the per-constant register (docs/wiki/chapters/sensor-value-audit.md).

Stored in GVAR(currentThermalContrast) (0-1) and
GVAR(currentThermalNoise) (0-1) for external query by sensor simulations,
FLIR overlay systems, or AI target-acquisition modifiers.
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

// currentHumidity is 0..100 percent, not a fraction.  Normalise to 0..1.
// It survives here only for the NETD noise term below; the contrast kernel
// no longer applies it.
private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if !(_RH isEqualType 0) then { _RH = 50; };
private _humidity = (_RH / 100) max 0 min 1;

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

// ─── NETD-based noise floor ───────────────────────────────────────────────
// NETD is the device's sensitivity: ~0.025 C cooled InSb/MCT, ~0.05 C
// uncooled microbolometer (issue #215: the thermal device classifier
// resolves the mounted device's researched NETD).  Noise grows with range
// squared: the atmospheric path adds scintillation and absorption noise.
// The range source is a real target range (see fnc_calculateThermalNoise);
// it is no longer the engine view distance.
private _range = 1000;
if !(_range isEqualType 0) then { _range = 1000; };
_range = _range max 100 min 5000;

// The device properties need a player to hold the device. A dedicated
// server has none, so the call is guarded and the sensor falls back to the
// uncooled default the resolver itself returns for an unknown device:
// [netdDegC, resX, resY, weightKg, refreshHz, cooled].
private _player = call CBA_fnc_currentUnit;
private _dev = if (isNil "_player" || {isNull _player}) then {
    [0.05, 640, 480, 1.5, 30, 0]
} else {
    [player, (vehicle player)] call EFUNC(thermal,getThermalDeviceProperties)
};
private _netd = _dev select 0;
if !(_netd isEqualType 0) then { _netd = 0.05; };
private _noise = _netd * ((_range / 1000) ^ 2);

// Detector resolution: a low-res detector samples the scene coarsely,
// adding spatial noise on top of the NETD floor.  The reference is the
// 640x480 uncooled class (the normalised detector area scales the
// noise up for a smaller array).
private _resX = _dev select 1;
if !(_resX isEqualType 0) then { _resX = 640; };
_noise = _noise * (640 / (_resX max 1));

_noise = _noise * (1 + _humidity * 0.5);
_noise = _noise max 0 min 1;

missionNamespace setVariable [QGVAR(currentThermalContrast), _contrast];
missionNamespace setVariable [QGVAR(currentThermalNoise), _noise];
