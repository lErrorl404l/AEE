#include "..\..\script_component.hpp"
/*
Band sky effective temperature (aee-thermal-realism T3).

The sensor sees the ATMOSPHERIC WINDOW, which is semi-transparent, so the sky
in the band is far colder than the total-longwave sky.  This pure kernel
replaces the retired fixed -35 K offset with a model that follows the air
temperature, the humidity and the overcast.

BAND EMITTANCE.  Idso 1981 (Water Resources Research 17(2):295-304, DOI
10.1029/WR017i002p00295), the 8-14 um clear-sky emittance at the zenith:

    epsBand = 0.24 + 2.98e-8 * eHPa^2 * exp(3000 / T_K)

e the screen-level water-vapour pressure in hPa, T the screen-level air
temperature in K (quoted with its validation against an independent 8-14 um
radiometer, within 2-10 C, in Clay et al. 1998, arXiv astro-ph/9810496,
eq. 3).  The emittance is the band sky radiance over the band blackbody
radiance at the air temperature, so the band sky temperature is the Planck
inversion of epsBand * B_band(T_air).  Idso's equation is for 8-14 um; the
MWIR band uses it too (no clear-sky 3-5 um relation is held).

OVERCAST.  Cloud fills the window: a water cloud of ordinary thickness is
black in 8-14 um (Stephens 1978, J Atmos Sci 35:2123), so the emittance is
epsBand + (1 - epsBand) * N, the cloud base taken at the air temperature.

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

private _tAirK = _tAirC + KELVIN_OFFSET;

// ─── Water-vapour partial pressure, Magnus saturation curve ───────────────
// e_s(T) = 6.112 * exp(17.67 * T / (T + 243.5)) hPa (Magnus, Bolton 1980).
private _eHPa = 6.112 * exp (17.67 * _tAirC / (_tAirC + 243.5)) * (_humidityPct / 100);

// ─── Idso 1981 8-14 um clear-sky emittance, then cloud ────────────────────
private _epsClear = (0.24 + 2.98e-8 * (_eHPa ^ 2) * exp (3000 / _tAirK)) min 1;
private _epsBand = (_epsClear + (1 - _epsClear) * _overcast) min 1;
private _wAir = [_tAirK, _lambda1M, _lambda2M] call FUNC(planckBandRadiance);

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

((_lo + _hi) / 2) - KELVIN_OFFSET
