#include "..\..\script_component.hpp"

/*
Lunar phase (0 new, 0.25 first quarter, 0.5 full, 0.75 last quarter) from
the mean synodic month (29.530588853 d) since the new moon of 2024-01-11
11:57 UT, including the time of day.  The mean phase is within about half a
day of the true one; the Moon's light uses the true illuminated fraction
(fnc_calculateSolarRadiation).

Sets  QGVAR(lunarPhase).
Returns the phase.
*/

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
// The UT instant (fnc_gameClockToUT, published by the solar model) puts
// the phase on Universal Time: day 8776 since 2000-01-01 is 2024-01-11.
private _daysSinceRef = (_dayNumber - 8777) + ((dayTime - 11.95) / 24);
private _ut = missionNamespace getVariable [QEGVAR(core,currentUTInstant), []];
if ((_ut isEqualType []) && {(count _ut) == 2}) then {
    _daysSinceRef = ((_ut select 0) - 8776) + (((_ut select 1) - 11.95) / 24);
};

// ─── Lunar phase (0 ≤ phase < 1) ─────────────────────────────────────────
// 0.0 = new moon, 0.25 = first quarter, 0.5 = full, 0.75 = last quarter
private _raw   = _daysSinceRef / 29.530588853;
private _phase = _raw - floor _raw;
if (_phase < 0) then { _phase = _phase + 1; };

// Store phase for downstream consumers (classifyNight, NVG, etc.)
missionNamespace setVariable [QGVAR(lunarPhase), _phase];

// The Moon's light is computed from the astronomy Moon (altitude and
// illuminated fraction) by aee_core_fnc_moonIlluminance; this function only
// publishes the waxing/waning phase for night classification.
_phase
