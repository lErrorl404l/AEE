#include "..\script_component.hpp"

/*
Author: AEE
Description: HF D-layer non-deviative absorption, ITU-R P.533 (George &
Bradley 1974, the "absorption index" form P.533 adopts for paths to 2000 km):

  L_a = 677.2 * sec(i) * I(chi) / ((f + f_L)^1.98 + 10.2)        dB
  I(chi) = (1 + 0.0037 * R12) * (cos 0.881 chi)^1.3               chi <= 102 deg

  f      operating frequency, MHz
  f_L    electron gyrofrequency about the longitudinal field at 100 km, MHz
  R12    12-month smoothed sunspot number
  chi    solar zenith angle at the absorbing layer; past 102 deg the index
         holds its 102 deg value (night)
  sec i  the obliquity of the ray at 110 km.  This state has no path
         geometry, so it is evaluated at vertical incidence (sec i = 1),
         the minimum; a consumer with a hop geometry scales it by sec(i).

The zenith angle is the astronomical sun (aee_core_currentSunElevation from
fnc_calculateSolarRadiation: date, latitude, longitude).  f_L comes from a
centred dipole, B0 = 29.8 uT at the equatorial surface (IGRF-13, epoch
2020: sqrt(g10^2 + g11^2 + h11^2) with g10 -29404.8, g11 -1450.9,
h11 4652.5 nT), taking the geographic latitude as the magnetic latitude:
  B = B0 * (Re / (Re + h))^3 * sqrt(1 + 3 sin^2 lat),  tan(dip) = 2 tan(lat)
  f_L = 0.028 MHz/uT * B * sin(dip)

Anchor: lat 40, f_L 1.02 MHz, R12 100, sun overhead: 3 MHz -> 36 dB per
vertical pass, the reason the 80 m band is dead at midday; 10 MHz -> 7.4 dB.

A solar flare adds the NOAA SWPC D-RAP absorption (HAF / f)^1.5 dB, the HAF
published by aee_weather_fnc_calculateSpaceWeather from the X-ray flux.

Arguments: None
Return Value: NUMBER: absorption, dB (vertical incidence)
Example: [] call aee_radio_fnc_calculateIonosphericAbsorption
Public: No
*/

private _freq_Hz = missionNamespace getVariable [QGVAR(frequency), 3e6];
if !(_freq_Hz isEqualType 0) then { _freq_Hz = 3e6; };
private _fMHz = (_freq_Hz max 1e5) / 1e6;
// The sunspot number of the mission date (aee_weather_fnc_calculateSpaceWeather:
// SILSO record, NOAA prediction, mean cycles); R12 in P.533 is the
// 12-month smoothed number, which that series is.
private _ssn = missionNamespace getVariable [QEGVAR(weather,sunspotNumber), 100];
if !(_ssn isEqualType 0) then { _ssn = 100; };
// D-RAP highest affected frequency of an X-ray flare at the observer, MHz.
private _haf = missionNamespace getVariable [QEGVAR(weather,flareHAF), 0];
if !(_haf isEqualType 0) then { _haf = 0; };

// ─── Solar zenith angle (astronomical sun) ─────────────────────────────────
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
if !(_sunElev isEqualType 0) then { _sunElev = -90; };
private _chi = (90 - _sunElev) min 102;

// ─── Longitudinal gyrofrequency at 100 km (centred dipole) ─────────────────
private _lat = ([] call EFUNC(lib,getWorldLocation)) select 0;
private _B = 29.8 * ((6371 / 6471) ^ 3) * sqrt (1 + 3 * ((sin _lat) ^ 2));   // uT
private _dip = atan (2 * tan _lat);
private _fL = 0.028 * _B * abs (sin _dip);                                    // MHz

// ─── George & Bradley absorption (ITU-R P.533) ─────────────────────────────
private _index = (1 + 0.0037 * _ssn) * ((cos (0.881 * _chi)) max 0) ^ 1.3;
private _absorption_dB = 677.2 * _index / (((_fMHz + _fL) ^ 1.98) + 10.2);
// Published so a consumer evaluates the absorption at its OWN frequency:
//   L_a(f) = dLayerNumerator / ((f_MHz + gyroFreqMHz)^1.98 + 10.2)
missionNamespace setVariable [QGVAR(dLayerNumerator), 677.2 * _index];
missionNamespace setVariable [QGVAR(gyroFreqMHz), _fL];

// ─── Sudden ionospheric disturbance (NOAA SWPC D-RAP) ─────────────────────
// A flare's X-rays add A(f) = (HAF / f)^1.5 dB (1 dB at the HAF).
if (_haf > 0) then {
    _absorption_dB = _absorption_dB + ((_haf / _fMHz) ^ 1.5);
};
_absorption_dB = _absorption_dB max 0;

missionNamespace setVariable [QEGVAR(core,ionosphericAbsorption), _absorption_dB];

_absorption_dB
