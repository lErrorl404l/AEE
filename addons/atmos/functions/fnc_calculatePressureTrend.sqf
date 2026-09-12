#include "..\script_component.hpp"

/*
Barometric pressure tendency via a 3-point ring buffer.

The tendency follows the WMO code 020xx pressure-tendency convention:
the change in station pressure over the preceding three hours, reported
as a signed value with a descriptive forecast.

Holds two prior readings (pressureReading1, pressureReading2). Each tick:
  p2 ← p1, p1 ← current
Then computes change = current - p2.

Directional forecast:
  drop > 2 hPa/tick  → "Storm approaching"
  drop 0.5–2         → "Rain expected"
  ±0.5               → "Stable"
  rise 0.5–2         → "Clearing"
  rise > 2           → "Fair weather"

Stored in GVAR(currentPressureTrend)   — float (hPa change)
Stored in GVAR(currentWeatherForecast) — string short phrase
*/

private _currentP = EGVAR(core,currentPressure);
if (isNil "_currentP") then {
    _currentP = missionNamespace getVariable [QEGVAR(core,currentPressure), 1018];
};

// ─── Ring buffer: initialise on first run ─────────────────────────────────
private _p1 = missionNamespace getVariable [QEGVAR(core,pressureReading1), _currentP];
private _p2 = missionNamespace getVariable [QEGVAR(core,pressureReading2), _currentP];

// Shift buffer
missionNamespace setVariable [QEGVAR(core,pressureReading2), _p1];
missionNamespace setVariable [QEGVAR(core,pressureReading1), _currentP];

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
