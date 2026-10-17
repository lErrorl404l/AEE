#include "..\script_component.hpp"
/*
Environmental excess loss on a radio link, for the ACRE2 and TFAR layers.

ACRE2 already computes the physical path loss of every link (Longley-Rice
ITM: distance, frequency, terrain diffraction), and TFAR applies its own
distance and terrain model.  AEE therefore supplies ONLY the losses those
models do not hold, as decibels, so nothing is counted twice:

  L_iono    HF D-layer absorption, ITU-R P.533 (fnc_calculateIonosphericAbsorption),
            evaluated at the link frequency; zero at 30 MHz and above, where
            the D-layer is transparent.  The ACRE2 callback re-evaluates it
            per link at the link's own frequency.
  L_flare   a solar flare's sudden ionospheric disturbance, NOAA SWPC
            D-RAP: (HAF / f)^1.5 dB, at any frequency.
  L_batt    a cold battery delivers less power: -10 log10(capacity factor)
            (aee_thermal_batteryTemperatureDerating), when enabled.
  L_emp     EMP front-end upset (EMP Commission 2008): the published
            amplitude factor f gives -20 log10(f).

Gaseous absorption is not included: below 1 GHz it is under 0.01 dB/km
(ITU-R P.676, Fig. 1), so a tactical VHF/UHF link loses less than 0.1 dB.
Tropospheric ducting and vegetation loss are not included: both need path
geometry (duct height and launch angle, ITU-R P.453/P.530; foliage depth,
ITU-R P.833) that the link layers do not pass.

Published:
  aee_radio_excessLossDB          L_iono(reference freq) + L_batt + L_emp, dB
  aee_radio_radioPropagationIndex the free-space range factor of that loss,
                                  10^(-L/20) (1 = no excess loss)
*/

private _freqHz = missionNamespace getVariable [QGVAR(radioFrequencyHz), 1e8];
if !(_freqHz isEqualType 0) then { _freqHz = 1e8; };

// ─── HF D-layer absorption (only below 30 MHz) ────────────────────────────
private _ionoDB = 0;
if (_freqHz < 30e6) then {
    private _num = missionNamespace getVariable [QGVAR(dLayerNumerator), 0];
    private _fL = missionNamespace getVariable [QGVAR(gyroFreqMHz), 1];
    if !(_num isEqualType 0) then { _num = 0; };
    if !(_fL isEqualType 0) then { _fL = 1; };
    _ionoDB = _num / ((((_freqHz / 1e6) + _fL) ^ 1.98) + 10.2);
};

// ─── Battery temperature derating (issue #36) ─────────────────────────────
private _battDB = 0;
if (missionNamespace getVariable [QGVAR(batteryDeratingEnabled), true]) then {
    private _derate = missionNamespace getVariable [QEGVAR(thermal,batteryTemperatureDerating), 1.0];
    if !(_derate isEqualType 0) then { _derate = 1.0; };
    _derate = (_derate max 0.01) min 1;
    _battDB = -10 * log _derate;
};

// ─── EMP semiconductor upset (issue #9) ───────────────────────────────────
private _empFactor = missionNamespace getVariable [QEGVAR(core,empRadioFactor), 1.0];
if !(_empFactor isEqualType 0) then { _empFactor = 1.0; };
_empFactor = (_empFactor max 0.001) min 1;
private _empDB = -20 * log _empFactor;

// ─── Flare sudden ionospheric disturbance (NOAA SWPC D-RAP) ───────────────
// (HAF / f)^1.5 dB at any frequency: an X-class flare's HAF can exceed
// 30 MHz, so it reaches low VHF.
private _flareDB = 0;
private _haf = missionNamespace getVariable [QEGVAR(weather,flareHAF), 0];
if !(_haf isEqualType 0) then { _haf = 0; };
if (_haf > 0) then {
    _flareDB = (_haf / (_freqHz / 1e6)) ^ 1.5;
};

private _excessDB = _ionoDB + _flareDB + _battDB + _empDB;
private _index = 10 ^ (-_excessDB / 20);

missionNamespace setVariable [QGVAR(excessLossDB), _excessDB];
missionNamespace setVariable [QGVAR(radioPropagationIndex), _index];

if (missionNamespace getVariable [QEGVAR(diagnostics,diagnostic), false]) then {
    private _logMsg = format [
        "RadioPropagation: excess %1 dB (iono %2 | battery %3 | EMP %4) -> range factor %5",
        [_excessDB, 1] call CBA_fnc_formatNumber,
        [_ionoDB, 1] call CBA_fnc_formatNumber,
        [_battDB, 1] call CBA_fnc_formatNumber,
        [_empDB, 1] call CBA_fnc_formatNumber,
        [_index, 3] call CBA_fnc_formatNumber
    ];
    AEE_LOG_INFO(_logMsg);
};

_index
