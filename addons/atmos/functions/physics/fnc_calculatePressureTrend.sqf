#include "..\..\script_component.hpp"

/*
Barometric pressure tendency via a time-stamped 3-hour ring buffer.

The tendency follows the WMO code 020xx pressure-tendency convention:
the change in station pressure over the preceding three hours, reported
as a signed value with a descriptive forecast.

Holds a time-stamped history of readings. Each tick appends
[diag_tickTime, current]; entries older than 3 hours are dropped, so the
buffer is bounded.  The trend is current minus the reading closest to
3 hours ago — the true WMO window, not the per-tick delta.

Directional forecast:
  drop > 2 hPa/3h  → "Storm approaching"
  drop 0.5–2       → "Rain expected"
  ±0.5             → "Stable"
  rise 0.5–2       → "Clearing"
  rise > 2         → "Fair weather"

Stored in GVAR(currentPressureTrend)   — float (hPa change over 3 h)
Stored in GVAR(currentWeatherForecast) — string short phrase
*/

private _currentP = EGVAR(core,currentPressure);
if (isNil "_currentP") then {
    _currentP = missionNamespace getVariable [QEGVAR(core,currentPressure), 1018];
};

// ─── Time-stamped 3-hour ring buffer ──────────────────────────────────────
// Each entry is [time, pressure].  Entries older than 3 hours (10800 s)
// are dropped so the buffer never grows without bound.
private _history = missionNamespace getVariable [QEGVAR(core,pressureHistory), []];
private _now = diag_tickTime;
_history pushBack [_now, _currentP];

// Drop entries older than the 3 h window (keep the buffer bounded)
private _cutoff = _now - 10800;
while {(count _history) > 0 && {(_history#0)#0 < _cutoff}} do {
    _history deleteAt 0;
};

// Clamp to a sane maximum (a 3 h window at a 5 s tick = ~2160 entries)
while {(count _history) > 2160} do {
    _history deleteAt 0;
};

missionNamespace setVariable [QEGVAR(core,pressureHistory), _history];

// ─── Trend over the preceding 3 hours ─────────────────────────────────────
// Find the reading closest to 3 hours ago; fall back to the oldest held.
private _p2 = _currentP;
if ((count _history) > 1) then {
    private _oldest = _history select 0;
    _p2 = _oldest select 1;
};
private _change = _currentP - _p2;

private _forecast = switch (true) do {
    case (_change < -2):  { "Storm approaching" };
    case (_change < -0.5): { "Rain expected" };
    case (_change > 2):   { "Fair weather" };
    case (_change > 0.5): { "Clearing" };
    default               { "Stable" };
};

missionNamespace setVariable [QEGVAR(core,currentPressureTrend), _change];
missionNamespace setVariable [QEGVAR(core,currentWeatherForecast), _forecast];
