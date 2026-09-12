#include "..\script_component.hpp"

/*
Author: AEE
Description: Computes HF D-layer non-deviative absorption from the solar
zenith angle, sunspot number, operating frequency, and the solar flare state
published by fnc_calculateSpaceWeather.

Uses the ITU-R P.531 secant law for non-deviative absorption: absorption is
proportional to 1/f² and to the secant of the solar zenith angle χ.  The
D-layer ionisation follows the sun (χ > 90° at night, so absorption falls to
a residual) and scales with the 11-year sunspot cycle.  Solar flares add a
sudden ionospheric disturbance (Dellinger effect) term.

Arguments: None
Return Value: NUMBER: absorption 0..10 dB
Example: [] call aee_radio_fnc_calculateIonosphericAbsorption
Public: No
*/

private _freq_Hz = missionNamespace getVariable [QGVAR(frequency), 3e6];
private _ssn = missionNamespace getVariable [QGVAR(sunspotNumber), 100];
private _flareActive = missionNamespace getVariable [QEGVAR(environmental,solarFlareActive), false];
private _flareValue = missionNamespace getVariable [QEGVAR(environmental,spaceWeatherFlareValue), 0];

// ─── Frequency dependence — absorption ∝ 1/f² (reference 3 MHz) ────────────
private _freqFactor = (3e6 / _freq_Hz) ^ 2;

// ─── Solar zenith angle — D-layer ionisation follows the sun ───────────────
private _sunPos = getSunPosition;
if (isNil "_sunPos") then { _sunPos = [0, 0]; };  // no renderer on a dedicated server
private _sunElev = _sunPos param [1, 0];
private _cosChi = (sin _sunElev) max 0;
private _dayFactor = [0.05, 1] select (_cosChi > 0);

// ─── Sunspot number — D-layer ionisation scales with solar activity ────────
private _ssnFactor = 1 + _ssn / 100;

// ─── Dellinger effect — solar flare sudden ionospheric disturbance ─────────
private _baseAbs = 0.5;  // mid-latitude noon reference at 3 MHz
private _absorption_dB = _baseAbs * _freqFactor * _dayFactor * _ssnFactor;
if (_flareActive) then {
    _absorption_dB = _absorption_dB + _flareValue;
};
_absorption_dB = _absorption_dB max 0 min 10;

missionNamespace setVariable [QEGVAR(core,ionosphericAbsorption), _absorption_dB];

_absorption_dB
