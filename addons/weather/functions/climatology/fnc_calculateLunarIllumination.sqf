#include "..\..\script_component.hpp"

/*
Compute ambient light level from moon phase, cloud cover, and solar
elevation.

Moon phase uses a simplified astronomical approximation referenced to the
new moon of 2024-01-11.  The result is in lux (0–300).

Sets  QGVAR(ambientLux).
Returns QGVAR(ambientLux).
*/

// ─── Daytime guard ───────────────────────────────────────────────────────
if (sunOrMoon > 0) exitWith {
    0
};

// ─── Parse date ──────────────────────────────────────────────────────────
private _dateArr = date;
private _year  = _dateArr#0;
private _month = _dateArr#1;
private _day   = _dateArr#2;

// ─── Continuous day number (integer) ─────────────────────────────────────
// Algorithm adapted from the task specification:
//   dayNumber = 367*y - 7*(y+(m+9)/12)/4 + 275*m/9 + d - 730530
// where integer division is enforced via floor() for SQF's float arithmetic.
private _adj = floor ((_month + 9) / 12);
private _c   = floor (7 * (_year + _adj) / 4);
private _d   = floor (275 * _month / 9);
private _dayNumber = 367 * _year - _c + _d + _day - 730530;

// ─── Days elapsed since reference new moon (2024-01-11) ──────────────────
// _refDayNumber computed from the same formula = 8777
private _daysSinceRef = _dayNumber - 8777;

// ─── Lunar phase (0 ≤ phase < 1) ─────────────────────────────────────────
// 0.0 = new moon, 0.25 = first quarter, 0.5 = full, 0.75 = last quarter
private _raw   = _daysSinceRef / 29.530588853;
private _phase = _raw - floor _raw;
if (_phase < 0) then { _phase = _phase + 1; };

// Store phase for downstream consumers (classifyNight, NVG, etc.)
missionNamespace setVariable [QGVAR(lunarPhase), _phase];

// ─── Illumination (lux) from phase angle ──────────────────────────────────
// Krisciunas & Schaefer (1991), PASP 103, 1033: the Moon's V magnitude
// as a function of phase angle, then illuminance from magnitude:
//   m = -12.73 + 0.026|alpha| + 4e-9 * alpha^4   (alpha in degrees)
//   E = 10^(-0.4 * (m + 14.18))  lux
// This reproduces the published moonlight curve: full ~0.26 lux,
// quarter ~0.025 lux, new ~0.0001 lux.  The opposition surge near
// full moon is built into the magnitude law, so no separate term.
private _phaseAngle = abs (180 * (1 - 2 * _phase));
private _moonMag = -12.73 + 0.026 * _phaseAngle + 4e-9 * (_phaseAngle ^ 4);
private _lux = 10 ^ (-0.4 * (_moonMag + 14.18));

// ─── Overcast attenuation ────────────────────────────────────────────────
private _overcast = overcast;
if (isNil "_overcast") then { _overcast = 0; };
_lux = _lux * (1 - _overcast * 0.8);

// ─── Starlight floor (0.001 lux) ─────────────────────────────────────────
_lux = 0.001 + _lux;
_lux = _lux max 0 min 300;

// ─── Store & return ──────────────────────────────────────────────────────
// The optics illuminance model owns ambientLux (aee_core_ambientLux);
// this module only feeds moonPhase into night classification.
_lux
