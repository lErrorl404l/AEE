#include "..\script_component.hpp"

/*
Simplified harmonic tide model driven by in-game date and time.

Combines lunar and solar tidal constituents:
  • Moon tide:  1.0 × sin(2π × dayFraction + moonPhase × π)
  • Sun tide:   0.4 × sin(2π × (dayFraction − 0.5))

Spring and neap cycles emerge naturally from the alignment of the
two constituents.  Result is clamped to ±2 m.

The tide description encodes the current state (Low / Rising / High / Falling)
and, where applicable, a spring- or neap-tide modifier.

Sets  QGVAR(currentTideOffset_m)   — float, −2 to +2
Sets  QGVAR(currentTideDescription) — string
Returns QGVAR(currentTideOffset_m)
*/

params [];

private _dateArr = date;
_dateArr params [["_year", 2024], ["_month", 1], ["_day", 1], ["_hour", 12], ["_minute", 0]];

// ─── Day fraction (0–1) ───────────────────────────────────────────────────
private _dayFraction = (_hour + (_minute / 60)) / 24;

// ─── Days since epoch (approximate) ───────────────────────────────────────
private _daysSinceEpoch = (_year * 365) + (_month * 30) + _day;

// ─── Moon phase (−1 to 1) ────────────────────────────────────────────────
// 29.53-day synodic period; sin() returns 0 at new moon, ±1 at full/alignment
private _moonPhase = sin (360 * (_daysSinceEpoch / 29.53));

// ─── Harmonic constituents (sin expects degrees) ─────────────────────────
private _moonTide = sin ((360 * _dayFraction) + (_moonPhase * 180));
private _sunTide  = 0.4 * sin (360 * (_dayFraction - 0.5));

private _tideHeight = (_moonTide + _sunTide) max -2 min 2;

// ─── Tide description ─────────────────────────────────────────────────────
// Approximate slope via forward difference for state detection
private _eps       = 0.01;
private _moonTideE = sin ((360 * (_dayFraction + _eps)) + (_moonPhase * 180));
private _sunTideE  = 0.4 * sin (360 * ((_dayFraction + _eps) - 0.5));
private _tideE     = (_moonTideE + _sunTideE) max -2 min 2;
private _slope     = (_tideE - _tideHeight) / _eps;

private _tideDesc = if (_tideHeight > 1.0) then {
    "High"
} else {
    if (_tideHeight < -1.0) then {
        "Low"
    } else {
        ["Falling", "Rising"] select (_slope > 0)
    }
};

// Spring / neap modifier appended when moon-sun alignment is pronounced
if (abs _moonPhase > 0.9) then {
    _tideDesc = _tideDesc + " (Spring Tide)";
};
if (abs _moonPhase < 0.2) then {
    _tideDesc = _tideDesc + " (Neap Tide)";
};

missionNamespace setVariable [QEGVAR(core,currentTideOffset_m),   _tideHeight];
missionNamespace setVariable [QEGVAR(core,currentTideDescription), _tideDesc];

_tideHeight
