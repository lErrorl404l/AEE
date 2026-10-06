#include "..\..\script_component.hpp"
/*
Clear-sky band effective temperature (aee-thermal-realism T3).

The sensor sees the ATMOSPHERIC WINDOW, which is semi-transparent, so the sky
in the band is far colder than the total-longwave sky.  This pure kernel
replaces the retired fixed -35 K offset with a model that follows the air
temperature, the humidity and the overcast.

SOURCE LADDER FOR THE BAND EMISSIVITY.
  Rung 1, grade standard: the Idso 1981 8-14 um band equation.  Not
  retrievable (the paper is closed and no peer-reviewed secondary quotes the
  band form).  Attempts are recorded in the register.
  Rung 2, grade derived-from-measurement: the Tebo 1965 measured 8-14 um band
  envelope.  Tebo ("Effective Clear Sky Temperatures in the 8- to 14-Micron
  Band", Flagstaff AZ) reports a whole-sky band temperature depression dT of
  45 K at a water-vapour partial pressure eHPa <= 4 and 21 K at eHPa >= 15.
  The depression is interpolated linearly in log(eHPa).  That interpolation
  is UNSOURCED and is marked in the register.

The full-spectrum clear-sky emissivity is Idso 1981:

    epsFull = 0.70 + 5.95e-5 * eHPa * exp(1500 / (T_air + 273.15))

(Idso, Water Resources Research 17(2):295-304, 1981, DOI
10.1029/WR017i002p00295).  It is sourced and quoted.

WHY THE BAND EMISSIVITY IS THE RADIANCE RATIO.  The measured quantity is a
band SKY TEMPERATURE, T_sky = T_air - dT, not a band emissivity.  The band
emissivity consistent with the exact Planck band integral is therefore
epsBand = B_band(T_sky) / B_band(T_air).  The Stefan-Boltzmann quartic
((T_air - dT)/T_air)^4 is the SB-equivalent (about 0.63 at 15 C and 50 percent
humidity, near the prior implied 0.60).  Using the quartic directly with the
Planck inversion would warm the band sky by about 6 K, because the band
radiance scales steeper than T^4.  The exact ratio reproduces the measured
depression, so night cold-sky contrast does not regress.

The result is clamped to at most the full-spectrum emissivity, which bounds
the window band from above for a clear sky.

OVERCAST.  Cloud fills the window, so the depression is blended toward zero
by (1 - overcast).

Arguments:
  0: bandToken (STRING, "lwir" or "mwir", default "lwir")
  1: tAirC (NUMBER, C)
  2: humidityPct (NUMBER, percent, clamped 0..100)
  3: overcast (NUMBER, 0..1, clamped)

Return Value: NUMBER - the clear-sky band effective temperature in C.
Example: ["lwir", 15, 50, 0] call aee_thermal_fnc_calculateSkyRadiance
Public: No
*/
params [
    ["_bandToken", "lwir", [""]],
    ["_tAirC", 15, [0]],
    ["_humidityPct", 50, [0]],
    ["_overcast", 0, [0]]
];

// Non-finite inputs are replaced by the reference condition, rather than
// poisoning the exponent.  SQF NaN compares false against everything.
if !(finite _tAirC) then { _tAirC = 15; };
if !(finite _humidityPct) then { _humidityPct = 50; };
if !(finite _overcast) then { _overcast = 0; };
_tAirC = (_tAirC max -80) min 60;
_humidityPct = _humidityPct max 0 min 100;
_overcast = _overcast max 0 min 1;

private _bandEdges = [_bandToken] call FUNC(resolveThermalBand);
private _lambda1M = _bandEdges select 0;
private _lambda2M = _bandEdges select 1;

private _tAirK = _tAirC + 273.15;

// ─── Water-vapour partial pressure, Magnus saturation curve ───────────────
// e_s(T) = 6.112 * exp(17.67 * T / (T + 243.5)) hPa (Magnus, Bolton 1980).
private _eHPa = 6.112 * exp (17.67 * _tAirC / (_tAirC + 243.5)) * (_humidityPct / 100);

// ─── Idso 1981 full-spectrum clear-sky emissivity (sourced) ───────────────
private _epsFull = 0.70 + 5.95e-5 * _eHPa * exp (1500 / _tAirK);

// ─── Tebo 1965 band depression envelope (derived-from-measurement) ────────
private _dT = 21;
if (_eHPa <= 4) then {
    _dT = 45;
} else {
    if (_eHPa < 15) then {
        // Linear in log(eHPa) between (4, 45) and (15, 21).  UNSOURCED.
        private _f = (ln _eHPa - ln 4) / (ln 15 - ln 4);
        _dT = 45 + (21 - 45) * _f;
    };
};

// Cloud fills the window: blend the depression toward zero.
_dT = _dT * (1 - _overcast);

// ─── Band emissivity and the measured band sky radiance ───────────────────
private _wAir = [_tAirK, _lambda1M, _lambda2M] call FUNC(planckBandRadiance);
private _wSky = [(_tAirK - _dT), _lambda1M, _lambda2M] call FUNC(planckBandRadiance);
private _epsBand = (_wSky / _wAir) min 1;
// A clear-sky window band emissivity is at most the full-spectrum
// emissivity (Idso 1981).  Overcast fills the window and can exceed it.
if (_overcast <= 0) then {
    _epsBand = _epsBand min _epsFull;
};

// ─── Invert the Planck band integral by bisection ─────────────────────────
// Find T with B_band(T) = epsBand * B_band(T_air).  B is monotone in T.
private _target = _epsBand * _wAir;
private _lo = 1;
private _hi = _tAirK;
for "_i" from 1 to 40 do {
    private _mid = (_lo + _hi) / 2;
    private _wMid = [_mid, _lambda1M, _lambda2M] call FUNC(planckBandRadiance);
    if (_wMid < _target) then {
        _lo = _mid;
    } else {
        _hi = _mid;
    };
};

((_lo + _hi) / 2) - 273.15
