#include "..\script_component.hpp"

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
    missionNamespace setVariable [QGVAR(ambientLux), 0];
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

// ─── Illumination fraction (0 = new, 1 = full) ──────────────────────────
// SQF's cos() takes degrees, so 2π rad → 360°
private _illumination = (1 - cos (360 * _phase)) / 2;

// ─── Overcast attenuation ────────────────────────────────────────────────
private _overcast = overcast;
if (isNil "_overcast") then { _overcast = 0; };
_illumination = _illumination * (1 - _overcast * 0.8);

// ─── Lunar lux contribution (0.001–0.3 typical range) ───────────────────
private _lux = 0.001 + _illumination * 0.299;
_lux = 0 max _lux min 300;

// ─── Store & return ──────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(ambientLux), _lux];
_lux
