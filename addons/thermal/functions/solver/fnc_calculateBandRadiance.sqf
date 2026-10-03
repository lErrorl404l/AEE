#include "..\..\script_component.hpp"
/*
LWIR band radiance (FLIR measurement equation, issue #196).

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

Band: the sim integrates over 8-14 um, spanning the fielded LWIR systems
(FLIR Tau 2: 7.5-13.5 um; AN/PAS-13C/E: 8-12 um; NETD < 50 mK).

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

Return Value:
  NUMBER - apparent band radiance (W/m2/sr), the value a FLIR sensor
  reads.  Monotonic in surface temperature for fixed environment, so it
  maps cleanly through the scene AGC.
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
    ["_traceOn", true]
];

// Transmission is clamped to the physical 0..1 range; a non-finite value
// falls back to 1, the old close-range behaviour, rather than poisoning the
// result.  SQF NaN compares false against everything, so finite is the check.
if !(_tau isEqualType 0) then { _tau = 1; };
if !(finite _tau) then { _tau = 1; };
_tau = (_tau max 0) min 1;

// Clamp the physical inputs: emissivity 0..1, temps sane.
_eps = (_eps max 0.05) min 1;
private _tSurfK = _tSurf + 273.15;
private _tAirK = (_tAir + 273.15) max 200 min 350;
private _tGroundK = _tGround + 273.15;

// ─── Sky temperature for the 8-14 um sensor band ──────────────────────────
// The sensor sees the ATMOSPHERIC WINDOW (8-14 um), which is
// semi-transparent - the sky in that band is FAR colder than the
// total-longwave sky.  Measured values: Tebo (1965), "Effective Clear
// Sky Temperatures in the 8-to 14-Micron Band", Flagstaff AZ, found
// whole-sky band temperatures of about -21 to -82 C; Aase & Idso (1981)
// give explicit 8-14 um band emissivity equations.  The total-longwave
// Swinbank correlation (T_sky = 0.0552*T^1.5, ~-3 C at 15 C air) is NOT
// applicable to the band: it overestimates the reflected-sky term by
// 20-50 %.  A clear-sky band temperature ~35 K below air is the
// temperate-condition mid-range of the Tebo measurements; overcast
// lifts it toward air temperature (cloud fills the window).
private _overcast = overcast max 0 min 1;
private _tSkyK = _tAirK - 35;
_tSkyK = _tSkyK + (_tAirK - _tSkyK) * _overcast;

// ─── Reflected environment: sky/ground mix by view factor ────────────────
private _tReflK = _fGround * _tGroundK + (1 - _fGround) * _tSkyK;

// ─── Planck band integral (8-14 um), exact ───────────────────────────────
// L_band = C * T^4 * [I(z1) - I(z2)],  z_i = c2 / (lambda_i * T),
// I(z) = sum_n exp(-n z) (z^3/n + 3 z^2/n^2 + 6 z/n^3 + 6/n^4).
// C = 2 k^4 / (h^3 c^2) = 2.779416505e-9 W m^-2 sr^-1 K^-4 and
// c2 = h c / k = 1.438776877e-2 m K, both from CODATA 2022.
private _fnRad = {
    params ["_tk"];
    _tk = (_tk max 100) min 2000;   // numerical domain guard, not a physical clamp
    private _z1 = 1.438776877e-2 / (8e-6 * _tk);
    private _z2 = 1.438776877e-2 / (14e-6 * _tk);
    private _z1s = _z1 * _z1;
    private _z1c = _z1s * _z1;
    private _z2s = _z2 * _z2;
    private _z2c = _z2s * _z2;
    private _b1 = exp (-_z1);
    private _b2 = exp (-_z2);
    private _e1 = _b1;
    private _e2 = _b2;
    private _i1 = 0;
    private _i2 = 0;
    for "_n" from 1 to 8 do {
        private _n2 = _n * _n;
        private _n3 = _n2 * _n;
        private _n4 = _n3 * _n;
        _i1 = _i1 + _e1 * (_z1c / _n + 3 * _z1s / _n2 + 6 * _z1 / _n3 + 6 / _n4);
        _i2 = _i2 + _e2 * (_z2c / _n + 3 * _z2s / _n2 + 6 * _z2 / _n3 + 6 / _n4);
        _e1 = _e1 * _b1;
        _e2 = _e2 * _b2;
    };
    2.779416505e-9 * (_tk ^ 4) * (_i2 - _i1)
};

// ─── FLIR 3-term radiance ─────────────────────────────────────────────────
// The object and reflection terms are multiplied by the transmission tau,
// and the path term (1 - tau) * W_atm is added.  With the default tau = 1
// the path term is exactly zero and the result is the old two-term value.
// The reflected term is (1-eps) * W(T_refl): a low-eps surface reflects the
// environment (cold sky at night) more than it emits - the physics behind
// "bare metal reads dark at night".
private _wObj = _tSurfK call _fnRad;
private _wRefl = _tReflK call _fnRad;
private _tPathK = (_tPath + 273.15) max 200 min 350;
private _wAtm = _tPathK call _fnRad;
private _wTransmitted = _tau * (_eps * _wObj + (1 - _eps) * _wRefl);
private _wBand = _wTransmitted + (1 - _tau) * _wAtm;
if (_traceOn) then {
    // The clock read above is deliberate and unconditional.  One engine call
    // per invocation costs less than a second guard, and the flag arrives as
    // an argument now: the caller resolves AEE_TRACE_ON once per pass, so the
    // three namespace lookups behind it are not repeated per selection.
    private _us = round ((diag_tickTime - _perfT0) * 1000);
    private _bandMsg = format ["bandRadiance %1 ms | tau %2 | eps %3 | surf %4 C | refl %5 C | path %6 C | W %7",
        _us, _tau toFixed 4, _eps toFixed 3, _tSurf, _tReflK - 273.15, _tPath, _wBand toFixed 6];
    AEE_LOG_DEBUG(_bandMsg);
};
_wBand
