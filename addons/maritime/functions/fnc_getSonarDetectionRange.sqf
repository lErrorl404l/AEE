#include "..\script_component.hpp"
/*
Sonar detection range (issue #113).

Answers "can this sonar hear that target, and at what range" from the
published environmental acoustics (fnc_updateUnderwaterAcoustics) and the
caller's sonar parameters.

The noise level comes from the published ambient noise, keyed to the mod's
sea state (Wenz 1962).  The absorption comes from the published seawater
absorption at the reference frequency (Francois-Garrison 1982).  The range
then follows from the sonar equation (Urick):

    passive:  EL = SL - NL + DI - DT
    active:   EL = (SL + TS - NL + DI - DT) / 2
    TL(r)  = logFactor * log10(r) + alpha * r
    detection when SE = (SL .. ) >= DT, i.e. TL(r) <= EL

The kernels fnc_calculateSonarEquation and fnc_calculateDetectionRange do
the arithmetic; this function only binds them to the environment.

Argument defaults.  Source level, directivity and detection threshold are
the caller's.  The active target strength defaults to a submarine-scale
value.  These are typical Urick values, marked UNSOURCED because the
primary text was not re-read; a scenario sets the real figures.

Input:  [mode, sourceLevel, directivity, targetStrength, threshold, spreading]
          mode            "passive" (default) or "active"
          sourceLevel     SL, dB re 1 uPa at 1 m
          directivity     DI, dB (default 0)
          targetStrength  TS, dB (active only; default 15, UNSOURCED)
          threshold       DT, dB (default 6, UNSOURCED)
          spreading       "spherical" (default) or "cylindrical"
Output: detection range in metres (0 when the environment does not support
        detection).  Also returns the signal excess at 1 km is NOT provided;
        call fnc_calculateSonarEquation for that.
*/

params [
    ["_mode", "passive", [""]],
    ["_sourceLevel", 200, [0]],
    ["_directivity", 0, [0]],
    ["_targetStrength", 15, [0]],
    ["_threshold", 6, [0]],
    ["_spreading", "spherical", [""]]
];

private _noise = missionNamespace getVariable [QGVAR(ambientNoiseDb), 60];
if !(_noise isEqualType 0) then { _noise = 60; };

private _absorption = missionNamespace getVariable [QGVAR(absorptionDbPerKm), 0];
if !(_absorption isEqualType 0) then { _absorption = 0; };

[
    _mode, _sourceLevel, _noise, _directivity,
    _targetStrength, _threshold, _absorption, _spreading
] call FUNC(calculateDetectionRange)
