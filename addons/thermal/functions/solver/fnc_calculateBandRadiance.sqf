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

Radiance is computed with a THREE-SEGMENT power-law fit to the Planck
integral over 8-14 um (validated in test_two_node.py / test_thermal:
night 250-290 K err <0.9%, day 290-330 K err <0.6%, hot 330-450 K err
<2.7%).  A full Planck quadrature per selection per tick is too slow;
the fit holds well inside the sim's range.

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
params [
    ["_tSurf", 15, [0]],
    ["_eps", 0.95, [0]],
    ["_tAir", 15, [0]],
    ["_fGround", 0.5, [0]],
    ["_tGround", 15, [0]],
    ["_tau", 1, [0]],
    ["_tPath", 15, [0]]
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

// ─── Planck-integral fit (8-14 um), three segments ───────────────────────
// Each segment: L = A * T^n, coefficients fitted to the exact integral
// (test_thermal: night err <0.9%, day <0.6%, hot <2.7%).
private _fnRad = {
    params ["_tk"];
    _tk = (_tk max 240) min 460;
    private _A = 2.152412e-11;   // night: 250-290 K
    private _n = 5.0121;
    if (_tk > 290) then {
        _A = 4.971094e-10;       // day: 290-330 K
        _n = 4.4580;
    };
    if (_tk > 330) then {
        _A = 3.885869e-08;       // hot: 330-450 K
        _n = 3.7101;
    };
    _A * (_tk ^ _n)
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
_wTransmitted + (1 - _tau) * _wAtm
