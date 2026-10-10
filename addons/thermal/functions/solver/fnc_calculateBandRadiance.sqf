#include "..\..\script_component.hpp"
/*
Band-limited thermal radiance (FLIR measurement equation, issue #196).

Real FLIR does not render temperature - it measures RADIANCE integrated
over the LWIR band, and the apparent radiance reaching the sensor has
three components (FLIR T810442 thermography reference):

    W = eps * tau * W_obj + (1-eps) * tau * W_refl + (1-tau) * W_atm

    W_obj   radiation emitted by the object surface
    W_refl  radiation from the surroundings reflected off the object
            ((1-eps) is reflectance by Kirchhoff's law)
    W_atm   radiation emitted by the atmosphere along the path
    tau     atmospheric transmission from fnc_calculateAtmosphericTransmission

tau and W_atm are now LIVE.  The kernel historically evaluated tau = 1, so
the (1 - tau) * W_atm term vanished and range had no physical effect.  The
caller passes tau and the path temperature; when it passes neither, tau
defaults to 1 and the atmospheric term is exactly zero, so every old caller
reproduces its old value bit for bit.  W_atm is the Planck band radiance at
the path temperature, which is the solution of the Schwarzschild transfer
equation for a HOMOGENEOUS ISOTHERMAL layer (near-horizontal boundary-layer
path below about 1 km).  It breaks on a slant path, across a temperature
inversion and over a multi-kilometre path; no slant-path integral is
computed, because the repository holds no vertical temperature profile.

The old `T * eps^0.25` scaling came from inverting Stefan-Boltzmann for
TOTAL hemispherical power - it is not valid for band-limited LWIR with a
reflection term, and it cannot represent the night behaviour that makes
real imagery look right: a low-emissivity surface (bare metal, eps ~0.1)
reflects the cold sky and reads DARK even when physically warm.

Band: the integral is parameterised by two band edges in metres.  The
default is the LWIR 8-14 um window, spanning the fielded LWIR systems
(FLIR Tau 2: 7.5-13.5 um; AN/PAS-13C/E: 8-12 um; NETD < 50 mK).  A caller
passes the MWIR 3-5 um pair for a cooled InSb or MWIR MCT detector.  The
band edges come from fnc_resolveThermalBand, which reads the per-device
band token.  Only the integration limits change; the Planck integrand is
unchanged.

The reflection temperature is the sky/ground mix the surface sees: a
horizontal panel sees the sky dome above and the ground below, weighted
by the ground view factor (0.5 for a flat surface, ~0.7 for a tyre,
~0.3 for a roof).  The SKY term is the 8-14 um atmospheric-window band
temperature - the window is semi-transparent, so the band sky is far
colder than the total-longwave sky (Tebo 1965 measured -21 to -82 C at
Flagstaff).  A clear-sky band temperature ~35 K below air is the
temperate mid-range; overcast fills the window and lifts it toward air.

Radiance is the EXACT Planck integral over 8-14 um, evaluated from the
cumulative blackbody series with CODATA 2022 constants.  The old three-
segment power-law fit is gone: it carried a 2.2 percent radiance step at
its 330 K join (inside the engine/exhaust band) and a 240 K clamp that
mis-evaluated the -40 C cold anchor.  The series needs no fit constants
and converges below 1e-9 in 40 terms over the sim's temperature range.

Arguments:
  0: surface temperature (NUMBER, C)
  1: emissivity (NUMBER, 0..1)
  2: air temperature (NUMBER, C) - drives the sky sink
  3: ground view factor (NUMBER, 0..1) - ground weight in the reflection
     mix; the sky weight is 1 - ground
  4: ground temperature (NUMBER, C) - the reflected ground term
  5: transmission (NUMBER, 0..1) - path transmission from
     fnc_calculateAtmosphericTransmission; default 1 reproduces the old
     close-range result exactly (the atmospheric term is then zero)
  6: path temperature (NUMBER, C) - air temperature along the path, for
     the isothermal path radiance W_atm; default 15, and inert while the
     transmission default of 1 holds
  7: trace flag (BOOL) - the hoisted module trace switch
  8: band short edge (NUMBER, m) - default 8e-6, the LWIR window start
  9: band long edge (NUMBER, m) - default 14e-6, the LWIR window end
 10: relative humidity (NUMBER, percent) - the band sky model input,
     default 50, the reference condition of the transmission kernel
 11: band token (STRING) - "lwir" (default) or "mwir", for the band sky
 12: reflected-solar band radiance (NUMBER, W/m2/sr) - from
     fnc_calculateReflectedSolarBand; default 0 keeps every LWIR caller
     bit-identical

Return Value:
  NUMBER - apparent band radiance (W/m2/sr), the value a FLIR sensor
  reads.  Monotonic in surface temperature for fixed environment, so it
  maps cleanly through the scene AGC.  A band whose short edge is not
  positive or whose long edge is not longer is refused with -1.
*/
private _perfT0 = diag_tickTime;
params [
    ["_tSurf", 15, [0]],
    ["_eps", 0.95, [0]],
    ["_tAir", 15, [0]],
    ["_fGround", 0.5, [0]],
    ["_tGround", 15, [0]],
    ["_tau", 1, [0]],
    ["_tPath", 15, [0]],
    // The module trace switch, hoisted by the caller.  AEE_TRACE_ON expands
    // to three namespace lookups, so this kernel is called per selection and
    // must not evaluate it per selection.  A caller that omits it keeps the
    // old behaviour (trace on).
    ["_traceOn", true],
    // Band edges in metres.  The LWIR 8-14 um default keeps every existing
    // caller bit-identical.  A caller resolves the per-device band token with
    // fnc_resolveThermalBand and passes the pair here.
    ["_lambda1M", 8e-6, [0]],
    ["_lambda2M", 14e-6, [0]],
    // Relative humidity, percent, for the band sky model (T3).  Default 50
    // matches the reference condition of the transmission kernel.
    ["_humidityPct", 50, [0]],
    // The per-device band token for the band sky model (T3).  Default lwir.
    ["_bandToken", "lwir", [""]],
    // Reflected-solar band radiance W/m2/sr (T4).  It already carries the
    // surface reflectance (1 - eps).  The default 0 keeps every LWIR caller
    // bit-identical.  A caller passes the result of
    // fnc_calculateReflectedSolarBand, which is zero for LWIR and at night.
    ["_wSolar", 0, [0]]
];

// A band must be a positive, increasing pair.  Refuse a bad one with -1, the
// same refusal discipline the other kernels use.  SQF NaN compares false
// against everything, so finite is checked before the arithmetic.
if !(_lambda1M isEqualType 0) exitWith { -1 };
if !(_lambda2M isEqualType 0) exitWith { -1 };
if !(finite _lambda1M) exitWith { -1 };
if !(finite _lambda2M) exitWith { -1 };
if (_lambda1M <= 0 || _lambda2M <= _lambda1M) exitWith { -1 };

// Transmission is clamped to the physical 0..1 range; a non-finite value
// falls back to 1, the old close-range behaviour, rather than poisoning the
// result.  SQF NaN compares false against everything, so finite is the check.
if !(_tau isEqualType 0) then { _tau = 1; };
if !(finite _tau) then { _tau = 1; };
_tau = (_tau max 0) min 1;

// Clamp the physical inputs: emissivity 0..1, temps sane.
_eps = (_eps max 0.05) min 1;
private _tSurfK = _tSurf + KELVIN_OFFSET;
private _tGroundK = _tGround + KELVIN_OFFSET;

// ─── Sky temperature for the sensor band ──────────────────────────────────
// The sensor sees the ATMOSPHERIC WINDOW, which is semi-transparent, so the
// sky in the band is far colder than the total-longwave sky.  The band sky
// model fnc_calculateSkyRadiance follows the air temperature, the humidity
// and the overcast.  It replaces the retired fixed offset.  At 15 C and
// 50 percent humidity the clear-sky band temperature is about -16 C, within
// 5 K of the old offset, so night cold-sky contrast does not regress.
private _overcast = overcast max 0 min 1;
private _tSkyC = [_bandToken, _tAir, _humidityPct, _overcast] call FUNC(calculateSkyRadiance);
// Published for the cross-module solar/sky invariant INV-5.  Grade:
// derived-from-measurement, the Tebo 1965 8-14 um band envelope that
// fnc_calculateSkyRadiance applies.  This is the last computed band sky
// temperature; the solver arithmetic is unchanged.
missionNamespace setVariable ["aee_thermal_skyBandTempC", _tSkyC];
private _tSkyK = _tSkyC + KELVIN_OFFSET;

// ─── Reflected environment: sky/ground mix by view factor ────────────────
private _tReflK = _fGround * _tGroundK + (1 - _fGround) * _tSkyK;

// ─── Planck band integral, exact ──────────────────────────────────────────
// The integral lives once, in fnc_planckBandRadiance.  See that kernel for
// the cumulative-blackbody series and the CODATA 2022 constants.
private _wObj = [_tSurfK, _lambda1M, _lambda2M] call FUNC(planckBandRadiance);
private _wRefl = [_tReflK, _lambda1M, _lambda2M] call FUNC(planckBandRadiance);
private _tPathK = (_tPath + KELVIN_OFFSET) max 200 min 350;
private _wAtm = [_tPathK, _lambda1M, _lambda2M] call FUNC(planckBandRadiance);
private _wTransmitted = _tau * (_eps * _wObj + (1 - _eps) * _wRefl + _wSolar);
private _wBand = _wTransmitted + (1 - _tau) * _wAtm;
if (_traceOn) then {
    // The clock read above is deliberate and unconditional.  One engine call
    // per invocation costs less than a second guard, and the flag arrives as
    // an argument now: the caller resolves AEE_TRACE_ON once per pass, so the
    // three namespace lookups behind it are not repeated per selection.
    private _us = round ((diag_tickTime - _perfT0) * 1000);
    private _bandMsg = format ["bandRadiance %1 ms | tau %2 | eps %3 | surf %4 C | refl %5 C | path %6 C | W %7",
        _us, _tau toFixed 4, _eps toFixed 3, _tSurf, _tReflK - KELVIN_OFFSET, _tPath, _wBand toFixed 6];
    AEE_LOG_DEBUG(_bandMsg);
};
_wBand
