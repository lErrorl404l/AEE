#include "..\script_component.hpp"
/*
Sonar detection range (issue #113).

Answers "can this sonar hear that target, and at what range" from the
published environmental acoustics (fnc_updateUnderwaterAcoustics) and the
caller's sonar parameters.

The noise level comes from the published ambient noise, keyed to the local
wind speed (Coates 1990 four-component model; fnc_calculateAmbientNoise).  The
absorption comes from the published seawater absorption at the reference
frequency (Francois-Garrison 1982).  The range then follows from the sonar
equation (Urick):

    passive:  EL = SL - NL + DI - DT
    active:   EL = (SL + TS - NL + DI - DT) / 2
    TL(r)  = logFactor * log10(r) + alpha * r
    detection when SE = (SL .. ) >= DT, i.e. TL(r) <= EL

The kernels fnc_calculateSonarEquation and fnc_calculateDetectionRange do
the arithmetic; this function only binds them to the environment.

Argument defaults.  Source level and directivity are the caller's.  The
active target strength defaults to 15 dB, the submarine value between bow
aspect (+10) and beam aspect (+25) in Urick, Principles of Underwater Sound
(3rd ed., 1983), Table 9.1.  The detection threshold defaults to the energy
detector of Urick s.12.5, DT = 5 log10(d w / t), with the detection index
d = 13.8 for a 50 % detection at a 1e-4 false-alarm probability (the ROC
curves of s.12.4: d = (z_fa - z_d)^2 = 3.72^2) in a 1 Hz band integrated for
1 s: 5 log10 13.8 = 5.7 dB, so 6 dB.

Input:  [mode, sourceLevel, directivity, targetStrength, threshold, spreading]
          mode            "passive" (default) or "active"
          sourceLevel     SL, dB re 1 uPa at 1 m
          directivity     DI, dB (default 0)
          targetStrength  TS, dB (active only; default 15, Urick Table 9.1)
          threshold       DT, dB (default 6, Urick s.12.5)
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
