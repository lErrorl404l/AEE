#include "..\script_component.hpp"

/*
ISO 9613-1:1993 atmospheric absorption coefficient (acoustic propagation).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It returns the frequency-dependent attenuation of sound by the atmosphere in
dB per metre, so a caller multiplies by the path length in metres.

SOURCED.  The formula is ISO 9613-1:1993 "Acoustics - Attenuation of sound
during propagation outdoors - Part 1: Calculation of the absorption of sound
by the atmosphere", equations (3) to (5) (the Sutherland-Bass relaxation
model).  The two relaxation frequencies are the oxygen term frO (eq 4) and the
nitrogen term frN (eq 5).  The molar water-vapour concentration h is the exact
ISO form h = (RH/100) * p_sat / p, with the saturation vapour pressure p_sat
from Buck (1981) in Pa, the same Buck equation the radio kernel uses.

Verified against the issue #80 reference values, computed from the standard
equations at 15 C, 50 % RH, 101.325 kPa:
    1 kHz -> 2.6015e-3 dB/m   (2.60 dB/km)
    8 kHz -> 12.5894e-3 dB/m  (12.59 dB/km)
Accuracy: within +-10 % for RH 0.05-5 %, T 253.15-323.15 K, p < 200 kPa
(ISO 9613-1 clause 7.1).  h is the molar FRACTION (0 to about 0.05): the
relaxation constants are calibrated for the fraction, not a percentage.

Units: T in degrees Celsius, RH in percent, P in hPa, the units the core
weather state publishes.  The kernel converts to Kelvin and Pa internally and
uses the reference pressure p0 = 101325 Pa.

Arguments:
  0: Number - the frequency, Hz
  1: Number - the air temperature, degrees Celsius
  2: Number - the relative humidity, percent 0 to 100
  3: Number - the atmospheric pressure, hPa (default 1013.25)

Returns:
  Number - the absorption coefficient, dB per metre

Example:
  [1000, 15, 50, 1013.25] call aee_ambience_fnc_atmosphericAbsorption
Public: Yes
*/

params [
    ["_frequencyHz", 1000, [0]],
    ["_temperatureC", 15, [0]],
    ["_humidity", 50, [0]],
    ["_pressureHPa", 1013.25, [0]]
];

private _tK = _temperatureC + 273.15;
private _t0 = 293.15;
private _pPa = _pressureHPa * 100;
private _p0 = 101325;

// Molar water-vapour concentration h (ISO 9613-1), a fraction.  Saturation
// vapour pressure from Buck (1981), hPa: 6.1121 exp((18.678 - t/234.5) t/(257.14 + t)).
private _psatPa = 6.1121 * (exp ((18.678 - (_temperatureC / 234.5)) * (_temperatureC / (257.14 + _temperatureC)))) * 100;
private _h = (_humidity / 100) * _psatPa / _pPa;

// Oxygen relaxation frequency (ISO 9613-1 eq 4), Hz.
private _frO = (_pPa / _p0) * (24 + (4.04e4 * _h * (0.02 + _h) / (0.391 + _h)));

// Nitrogen relaxation frequency (ISO 9613-1 eq 5), Hz.
private _frN = ((_tK / _t0) ^ (-0.5)) * (9 + (280 * _h * (exp (-4.170 * (((_tK / _t0) ^ (-1 / 3)) - 1)))));

// Absorption coefficient (ISO 9613-1 eq 3), dB/m.  The 8.686 factor converts
// Np/m to dB/m.
private _alpha = 8.686 * (_frequencyHz ^ 2) * (
    (1.84e-11 * ((_pPa / _p0) ^ (-1)) * ((_tK / _t0) ^ 0.5))
    + ((_tK / _t0) ^ (-2.5)) * (
        (0.01275 * (exp (-2239.1 / _tK)) / (_frO + ((_frequencyHz ^ 2) / _frO)))
        + (0.1068 * (exp (-3352 / _tK)) / (_frN + ((_frequencyHz ^ 2) / _frN)))
    )
);

_alpha
