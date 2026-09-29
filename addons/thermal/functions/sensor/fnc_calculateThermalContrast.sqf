#include "..\..\script_component.hpp"

/*
Thermal contrast coefficient (0–1) for the FLIR/thermal display gain stage,
plus a NETD-based sensor noise floor.

  1.0 = full display contrast
  0.0 = no usable contrast

WHAT THIS COEFFICIENT IS AND IS NOT.  This is a DISPLAY DEGRADATION FACTOR,
not a sensor figure of merit and not a gain.  The engine ALREADY renders the
native thermal image with its own gain; this stage only adds the
environmental degradation the engine does not model, so its clear-air value
is exactly 1.0 and only weather and extreme heat can lower it.  A
scene-derived term that moves with the scene cannot be a sensor property,
because sensor sensitivity is fixed, so no vehicle-minus-ground gap enters
here.  The system figure of merit is MRTD, which joins NETD to spatial
frequency into one curve.  NETD (Noise Equivalent Temperature Difference) is
the temperature difference that produces a signal equal to the sensor's own
noise, that is a signal-to-noise ratio of 1.  This coefficient is NEITHER of
these; it is the display degradation factor.

Physics basis - DEGRADATION ONLY, NO BASE GAIN:
  - The ENGINE renders the native thermal image with its own gain, so this
    stage must not add a second one.  Its output is a dimensionless
    degradation factor with a base of exactly 1.0: no weather, no extreme
    heat and no cold means no change.  1.0 is also the consumer's declared
    default (fnc_applyThermalVision.sqf:79), so the two agree.  An earlier
    revision derived a base contrast from the vehicle-minus-ground
    temperature gap over an arbitrary 8 °C span; that was an undocumented
    second gain stage on top of the engine's own render and it is removed.
  - Rain absorbs LWIR, fog scatters it, and water vapour (humidity)
    absorbs it.  Each multiplies the factor down.
  - Heat (>35 °C) flattens the thermal gradient: everything approaches
    air temperature, so the object-background gap narrows.
  - Cold (<5 °C) widens the gap: objects stay warm while the background
    cools, so it can partly restore a factor that rain or fog lowered.
  - NETD (Noise Equivalent Temperature Difference) is the temperature
    change that produces a signal equal to the sensor's own noise.
    Modern uncooled microbolometers run ~0.05 °C.  Atmospheric path
    noise grows with range squared (more air means more scintillation
    and absorption), and humidity adds water-vapour noise.

Stored in GVAR(currentThermalContrast) (0–1) and
GVAR(currentThermalNoise) (0–1) for external query by sensor
simulations, FLIR overlay systems, or AI target-acquisition modifiers.
*/

// ─── Shared inputs ────────────────────────────────────────────────────────
private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_T isEqualType 0) then { _T = 15; };

private _fog = missionNamespace getVariable [QEGVAR(core,currentFogDensity), 0];
if !(_fog isEqualType 0) then { _fog = 0; };

// currentHumidity is 0..100 percent, not a fraction.  Normalise to 0..1.
private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if !(_RH isEqualType 0) then { _RH = 50; };
private _humidity = (_RH / 100) max 0 min 1;

// ─── Base contrast ────────────────────────────────────────────────────────
// No base gain is derived here.  The engine renders the native thermal
// image with its own gain, and this stage adds only the environmental
// degradation the engine does not model.  The base is therefore exactly 1.0
// (full, undegraded display contrast), which is also the consumer's
// declared default in fnc_applyThermalVision.sqf:79.  In clear conditions
// the published value is 1.0 and no second amplifier exists.
private _contrast = 1.0;

// ─── Atmospheric attenuation ──────────────────────────────────────────────
// Rain absorbs LWIR, fog scatters it, water vapour absorbs it.
_contrast = _contrast * (1 - rain * 0.4);
_contrast = _contrast * (1 - _fog * 0.6);
_contrast = _contrast * (1 - _humidity * 0.3);

// ─── Extreme heat — gradient flattens ────────────────────────────────────
if (_T > 35) then {
    _contrast = _contrast - ((_T - 35) / 10) * 0.7; // linear to 0.3 at 45 °C
};

// ─── Cold boost — widened thermal gap ────────────────────────────────────
if (_T < 5) then {
    _contrast = (_contrast * 1.2) min 1.0;
};

_contrast = _contrast max 0 min 1;

// ─── NETD-based noise floor ───────────────────────────────────────────────
// NETD (Noise Equivalent Temperature Difference) is the device's
// sensitivity: ~0.025 C cooled InSb/MCT, ~0.05 C uncooled microbolometer
// (issue #215: the thermal device classifier resolves the mounted
// device's researched NETD).  Noise grows with range squared: the
// atmospheric path adds scintillation and absorption noise.  Range is
// the sensor's working range, proxied by the engine view distance; a
// dedicated server has no player, so fall back to 1000 m.
private _range = viewDistance;
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
