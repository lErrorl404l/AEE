#include "..\script_component.hpp"

/*
Harmonic tide model driven by in-game date and time.

Four standard tidal constituents (degrees/hour angular speeds from the
Admiralty/NOAA harmonic analysis):
  M2 (principal lunar semidiurnal): 28.9841°/h, period 12.42 h, amp 1.00 m
  S2 (principal solar semidiurnal): 30.0000°/h, period 12.00 h, amp 0.47 m
  K1 (lunisolar diurnal):           15.0411°/h, period 24.07 h, amp 0.58 m
  O1 (principal lunar diurnal):     13.9430°/h, period 25.82 h, amp 0.42 m

The tide height is the sum of the four constituents:

  h(t) = Σ Aᵢ · sin(ωᵢ · t − φᵢ)

where t is hours since a fixed epoch (2024-01-01 00:00, so the tide is a
deterministic function of the in-game date).  M2/S2 beat produces the
spring/neap cycle naturally (7-day period) — no phase hack needed.
Result clamped to the configured amplitude.

The tide description encodes the current state (Low / Rising / High /
Falling) and, where applicable, a spring- or neap-tide modifier.

Sets  QGVAR(currentTideOffset_m)   — float, −amp to +amp
Sets  QGVAR(currentTideDescription) — string
Returns QGVAR(currentTideOffset_m)
*/

params [];

private _amp = missionNamespace getVariable [QGVAR(tideAmplitude), 2.0];

private _dateArr = date;
_dateArr params [["_year", 2024], ["_month", 1], ["_day", 1], ["_hour", 12], ["_minute", 0]];

// ─── Hours since fixed epoch (2024-01-01 00:00) ───────────────────────────
// Standard 30.6001-day month formula for day-of-year, then ×24 + clock hours.
private _dayOfYear = floor (275 * _month / 9) - (2 * floor ((_month + 9) / 12)) + _day - 30;
private _hoursSinceEpoch = ((_year - 2024) * 8760) + ((_dayOfYear - 1) * 24) + _hour + (_minute / 60);

// ─── Constituent angular speeds (deg/h) and amplitudes (m) ───────────────
private _M2 = [28.9841, 1.00];
private _S2 = [30.0000, 0.47];
private _K1 = [15.0411, 0.58];
private _O1 = [13.9430, 0.42];

// Phase offsets (deg) at the epoch — approximate, so the tide is stable
private _phaseM2 = 0; private _phaseS2 = 45; private _phaseK1 = 90; private _phaseO1 = 0;

private _tideHeight = 0;
{
    _x params ["_speed", "_amp"];
    private _phase = switch (_forEachIndex) do {
        case 0: { _phaseM2 };
        case 1: { _phaseS2 };
        case 2: { _phaseK1 };
        default { _phaseO1 };
    };
    _tideHeight = _tideHeight + (_amp * sin ((_speed * _hoursSinceEpoch) + _phase));
} forEach [_M2, _S2, _K1, _O1];

_tideHeight = _tideHeight max -_amp min _amp;

// ─── Tide description ─────────────────────────────────────────────────────
// Approximate slope via forward difference for state detection (0.25 h)
private _eps     = 0.25;
private _tideE   = 0;
{
    _x params ["_speed", "_amp"];
    private _phase = switch (_forEachIndex) do {
        case 0: { _phaseM2 };
        case 1: { _phaseS2 };
        case 2: { _phaseK1 };
        default { _phaseO1 };
    };
    _tideE = _tideE + (_amp * sin ((_speed * (_hoursSinceEpoch + _eps)) + _phase));
} forEach [_M2, _S2, _K1, _O1];
_tideE = _tideE max -_amp min _amp;
private _slope = (_tideE - _tideHeight) / _eps;

private _tideDesc = if (_tideHeight > 1.0) then {
    "High"
} else {
    if (_tideHeight < -1.0) then {
        "Low"
    } else {
        ["Falling", "Rising"] select (_slope > 0)
    }
};

// Spring / neap from M2/S2 alignment: when the two semidiurnal constituents
// are in phase the tidal range is largest (spring), opposed it is smallest
// (neap).  The beat period is ~14.8 days.  Alignment is the cosine of the
// phase difference (peaks at 1 when in phase; SQF trig takes degrees, so
// no radian conversion).
private _alignment = abs (cos (((_M2 select 0) - (_S2 select 0)) * _hoursSinceEpoch + (_phaseM2 - _phaseS2)));
if (_alignment > 0.9) then {
    _tideDesc = _tideDesc + " (Spring Tide)";
};
if (_alignment < 0.2) then {
    _tideDesc = _tideDesc + " (Neap Tide)";
};

missionNamespace setVariable [QEGVAR(core,currentTideOffset_m),   _tideHeight];
missionNamespace setVariable [QEGVAR(core,currentTideDescription), _tideDesc];

_tideHeight
