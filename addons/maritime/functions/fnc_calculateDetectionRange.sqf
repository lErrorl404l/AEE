#include "..\script_component.hpp"
/*
Detection range from the sonar equation (issue #113).

Urick, "Principles of Underwater Sound", 3rd ed., McGraw-Hill 1983,
ISBN 0-07-066087-5.  Corroborated by the US Naval Academy ES310
sonar-propagation notes.

Detection occurs when the signal excess SE reaches the detection threshold
DT.  Rearranged, the one-way transmission loss must not exceed the allowed
loss EL:

    passive:  EL = SL - NL + DI - DT
    active:   EL = (SL + TS - NL + DI - DT) / 2      (2 TL in the equation)

The range follows from the transmission-loss law (fnc_calculateTransmissionLoss):

    TL(r) = logFactor * log10(r) + (alpha / 1000) * r

  logFactor  20 for spherical spreading, 10 for cylindrical

This is solved by bisection between 1 m and 1e7 m.  With absorption present
the equation has no closed form; without absorption it reduces to
r = 10^(EL / logFactor).  The bisection handles both.

  SL   source level, dB re 1 uPa at 1 m
  NL   ambient noise spectrum level, dB (from fnc_calculateAmbientNoise)
  DI   directivity index, dB
  TS   target strength, dB (active only)
  DT   detection threshold, dB
  alphaDbKm  absorption, dB/km (from fnc_calculateAbsorptionWater)

Input:  [mode, SL, NL, DI, TS, DT, alphaDbKm, spreading]
Output: detection range in metres.  Zero when no range satisfies the
        equation (EL <= 0).  Capped at 1e7 m.
*/

params [
    ["_mode", "passive", [""]],
    ["_SL", 0, [0]],
    ["_NL", 0, [0]],
    ["_DI", 0, [0]],
    ["_TS", 0, [0]],
    ["_DT", 0, [0]],
    ["_alphaDbKm", 0, [0]],
    ["_spreading", "spherical", [""]]
];

private _el = if (_mode == "active") then {
    (_SL + _TS - _NL + _DI - _DT) / 2
} else {
    _SL - _NL + _DI - _DT
};

if (_el <= 0) exitWith { 0 };

private _logFactor = [20, 10] select (_spreading == "cylindrical");
private _lo = 1;
private _hi = 1e7;

for "_i" from 1 to 60 do {
    private _mid = (_lo + _hi) / 2;
    private _tl = (_logFactor * (log _mid)) + ((_alphaDbKm / 1000) * _mid);
    if (_tl > _el) then { _hi = _mid; } else { _lo = _mid; };
};

(_lo + _hi) / 2
