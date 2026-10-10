#include "..\script_component.hpp"
/*
Driver for the internal-wave and thermocline model (issue #17).

Runs once per second from XEH_postInit.  It reads the sea-surface
temperature, the map latitude and the operator settings, then calls the
pure kernels and publishes the state for consumers.  The future underwater
acoustics model (#113) reads the thermocline profile.

Two-layer reduction.  The continuous ocean is reduced to two layers: a warm
mixed layer of thickness h1 = the thermocline depth, and a cold deep layer
of thickness h2.  The mixed-layer temperature is the sea-surface
temperature computed by calculateSeaSurfaceTemperature.  The deep-water
temperature is the abyssal value (4 degC, Stewart 2008).  Each layer
density comes from the linear equation of state
(fnc_calculateSeawaterDensity).

Internal tide.  The thermocline is displaced at the M2 tidal period
(12.4206 h) with the configured amplitude.  The internal tide exists only
where the M2 frequency exceeds the inertial frequency f = 2*Omega*sin(lat).
Above the critical latitude (about 74.5 deg) the internal tide is
evanescent, so the model reports it inactive and the displacement and the
currents are zero.  The inertial period T_i = 2*pi/f bounds the
internal-wave band.

Engine ceiling.  The engine renders its own sea surface and has no
thermocline.  This driver publishes physical state; it does not fight the
engine render.

State (missionNamespace):
  aee_maritime_thermoclineDepth_m        thermocline centre depth (m)
  aee_maritime_thermoclineWidth_m        thermocline half-width (m)
  aee_maritime_mixedLayerTempC           mixed-layer temperature (degC)
  aee_maritime_deepTempC                 deep-water temperature (degC)
  aee_maritime_reducedGravity_ms2        g' (m/s2)
  aee_maritime_internalWaveSpeed_ms      two-layer phase speed c (m/s)
  aee_maritime_internalTidePeriod_h      M2 period (h)
  aee_maritime_internalWaveAmplitude_m   interface displacement eta (m)
  aee_maritime_internalCurrentUpper_ms   upper-layer current u1 (m/s)
  aee_maritime_internalCurrentLower_ms   lower-layer current u2 (m/s)
  aee_maritime_inertialPeriod_h          inertial period 2*pi/f (h)
  aee_maritime_internalTideActive        boolean (M2 above the inertial frequency)
  aee_maritime_thermoclineProfile        [[depth_m, tempC], ...] for the sound-speed model

Input:  none
Output: the published state array
*/

// ─── Physical constants ────────────────────────────────────────────────────
private _g = 9.80665;            // standard gravity (ISO 80000-3)
private _omega = 7.2921e-5;      // Earth rotation rate, rad/s (Stewart 2008)
private _deepTempC = 4;          // abyssal temperature, degC (Stewart 2008)
private _salinity = 35;          // reference salinity, psu
private _rho0 = 1027.8;          // reference density at 4 degC, 35 psu (kg/m3)
private _alpha = 1.7e-4;         // thermal expansion, per degC (Stewart 2008)
private _beta = 7.6e-4;          // haline contraction, per psu (Stewart 2008)
private _m2PeriodS = 44714;      // M2 period 12.4206 h (Admiralty/NOAA)
private _deepLayerM = 1000;      // deep-layer thickness h2 (m)
private _profileDepths = [0, 10, 20, 30, 40, 50, 75, 100, 150, 200];

// ─── Operator settings ─────────────────────────────────────────────────────
private _zTc = missionNamespace getVariable [QGVAR(thermoclineDepth), 50];
if !(_zTc isEqualType 0) then { _zTc = 50; };
private _width = missionNamespace getVariable [QGVAR(thermoclineWidth), 30];
if !(_width isEqualType 0) then { _width = 30; };
private _amp = missionNamespace getVariable [QGVAR(internalTideAmplitude), 20];
if !(_amp isEqualType 0) then { _amp = 20; };

// ─── Mixed-layer temperature (from the SST model) ──────────────────────────
private _mixedTempC = missionNamespace getVariable [QEGVAR(maritime,seaSurfaceTemperature), 15];
if !(_mixedTempC isEqualType 0) then { _mixedTempC = 15; };
// In a stable column the mixed layer is not colder than the deep water.
_mixedTempC = _mixedTempC max _deepTempC;

// ─── Layer densities and the two-layer phase speed ─────────────────────────
private _rho1 = [_mixedTempC, _salinity, _rho0, _alpha, _beta, _deepTempC, _salinity]
    call FUNC(calculateSeawaterDensity);
private _rho2 = [_deepTempC, _salinity, _rho0, _alpha, _beta, _deepTempC, _salinity]
    call FUNC(calculateSeawaterDensity);

private _h1 = _zTc max 1;
private _wave = [_rho1, _rho2, _h1, _deepLayerM, _g] call FUNC(calculateInternalWaveSpeed);
private _speed = _wave select 0;
private _gPrime = _wave select 1;

// ─── Inertial frequency and the M2 critical latitude ───────────────────────
private _lat = ([] call EFUNC(lib,getWorldLocation)) select 0;
if !(_lat isEqualType 0) then { _lat = 50; };
private _f = abs (2 * _omega * sin _lat);
private _inertialPeriodH = if (_f > 1e-6) then { 2 * pi / _f / 3600 } else { 0 };
private _tideActive = (2 * pi / _m2PeriodS) > _f;

// ─── Internal tide displacement and layer currents ─────────────────────────
private _tide = [_amp, _m2PeriodS, CBA_missionTime, _speed, _h1, _deepLayerM]
    call FUNC(calculateInternalTide);
private _eta = _tide select 0;
private _u1 = _tide select 1;
private _u2 = _tide select 2;
if (!_tideActive) then {
    _eta = 0;
    _u1 = 0;
    _u2 = 0;
};

// ─── Thermocline temperature profile (input for the sound-speed model) ─────
private _profile = _profileDepths apply {
    [_x, [_x, _mixedTempC, _deepTempC, _zTc, _width] call FUNC(calculateThermoclineTemperature)]
};

// ─── Publish ───────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(thermoclineDepth_m), _zTc];
missionNamespace setVariable [QGVAR(thermoclineWidth_m), _width];
missionNamespace setVariable [QGVAR(mixedLayerTempC), _mixedTempC];
missionNamespace setVariable [QGVAR(deepTempC), _deepTempC];
missionNamespace setVariable [QGVAR(reducedGravity_ms2), _gPrime];
missionNamespace setVariable [QGVAR(internalWaveSpeed_ms), _speed];
missionNamespace setVariable [QGVAR(internalTidePeriod_h), _m2PeriodS / 3600];
missionNamespace setVariable [QGVAR(internalWaveAmplitude_m), _eta];
missionNamespace setVariable [QGVAR(internalCurrentUpper_ms), _u1];
missionNamespace setVariable [QGVAR(internalCurrentLower_ms), _u2];
missionNamespace setVariable [QGVAR(inertialPeriod_h), _inertialPeriodH];
missionNamespace setVariable [QGVAR(internalTideActive), _tideActive];
missionNamespace setVariable [QGVAR(thermoclineProfile), _profile];

[_speed, _gPrime, _eta, _u1, _u2, _tideActive]
