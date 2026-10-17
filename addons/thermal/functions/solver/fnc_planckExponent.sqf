#include "..\..\script_component.hpp"
/*
Band-resolved Planck exponent at a temperature (issue #255).

The thermal closed forms differentiate the band radiance and need its local
power-law exponent n.  The retired constants (5.0121 / 4.4580 / 3.7101) came
from a three-segment power-law fit that fnc_calculateBandRadiance no longer
uses: the band integral is the exact Planck cumulative-blackbody series in
fnc_planckBandRadiance.  The constants were therefore STALE, and because the
kernels took no band they were also BAND-BLIND - an MWIR device reused the
LWIR exponents.

This kernel derives n from the exact model instead.  With L the band
radiance,

    n = d(ln L) / d(ln T) = (T / L) * (dL / dT)

evaluated as a central difference over a 1 K step.  The slope is a property
of the band: at a 15 C background it is about 4.73 for the LWIR 8-14 um
window and about 11.3 for the MWIR 3-5 um window, so the two detector
classes no longer share an exponent.

Arguments:
  0: temperature (NUMBER, K) - the background temperature
  1: band token (STRING, "lwir" or "mwir", default "lwir")

Return Value: NUMBER, the local log-log slope, or -1 when an input is
unusable (non-Number, non-finite, non-positive temperature, or an unusable
band from fnc_planckBandRadiance).
Example: [288.15, "mwir"] call aee_thermal_fnc_planckExponent
Public: No
*/

params [["_tk", 300, [0]], ["_bandToken", "lwir", [""]]];

if !(_tk isEqualType 0) exitWith { -1 };
if !(finite _tk) exitWith { -1 };
if (_tk <= 0) exitWith { -1 };

// The band edges come from the one band resolver, so this kernel and the
// radiance kernel cannot disagree on the window.
private _band = [_bandToken] call FUNC(resolveThermalBand);
private _lambda1M = _band select 0;
private _lambda2M = _band select 1;

private _h = 1;   // K, central-difference step
private _l0 = [_tk, _lambda1M, _lambda2M] call FUNC(planckBandRadiance);
if (_l0 <= 0) exitWith { -1 };
// The lower sample is clamped at 1 K, which cannot change the slope over the
// simulation's temperature range but stops a non-positive radiance sample.
private _lHi = [(_tk + _h), _lambda1M, _lambda2M] call FUNC(planckBandRadiance);
private _lLo = [((_tk - _h) max 1), _lambda1M, _lambda2M] call FUNC(planckBandRadiance);
if (_lHi <= 0 || _lLo <= 0) exitWith { -1 };

(_tk / _l0) * ((_lHi - _lLo) / (2 * _h))
