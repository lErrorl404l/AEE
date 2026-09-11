#include "..\script_component.hpp"

/*
Microburst detection — sudden violent downdraft in convective conditions.

Requires: overcast > 0.8, temp > 28°C, RH > 70%, ambient wind < 3 m/s.
1 %/tick activation chance when all conditions hold.  Once triggered,
extreme gust wind (15-30 m/s) persists for ~12 ticks (~60 s at 5 s PFH).

Sets:
  QGVAR(currentMicroburst)    — bool
  QGVAR(microburstWindSpeed)  — float m/s (0 if inactive)
  QGVAR(microburstTimer)      — int ticks remaining
*/

// ─── Inputs ──────────────────────────────────────────────────────────────
private _overcast  = overcast;
private _temp      = EGVAR(core,currentTemperature);
private _RH        = EGVAR(core,currentHumidity);

if (isNil "_temp") then { _temp = 20; };
if (isNil "_RH")   then { _RH   = 50; };

// ─── Timer ───────────────────────────────────────────────────────────────
private _timer     = missionNamespace getVariable [QGVAR(microburstTimer), 0];
private _windSpeed = 0;

if (_timer > 0) then {
    // Active — decrement timer, keep wind speed
    _timer     = _timer - 1;
    _windSpeed = missionNamespace getVariable [QGVAR(microburstWindSpeed), 15 + random 15];
} else {
    // Check trigger conditions
    private _ambientWind = vectorMagnitude wind;
    if (_overcast > 0.8
        && _temp > 28
        && _RH > 70
        && _ambientWind < 3
        && random 1 < 0.01
    ) then {
        _timer     = 12;
        _windSpeed = 15 + random 15;   // 15-30 m/s
    };
};

// ─── Output ──────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(currentMicroburst),   _timer > 0];
missionNamespace setVariable [QGVAR(microburstWindSpeed), _windSpeed];
missionNamespace setVariable [QGVAR(microburstTimer),     _timer];
