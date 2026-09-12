#include "..\script_component.hpp"

/*
Microburst detection - sudden violent downdraft in convective conditions.

Requires: overcast > 0.8, temp > 28°C, RH > 70%, ambient wind < 3 m/s.
1 %/tick activation chance when all conditions hold. Once triggered,
a moderate gust (15-30 m/s) or a damaging gust (26-36 m/s) persists for
~12 ticks (~60 s at 5 s PFH). The NWS damaging microburst criterion is
a gust of 26 m/s (50 kt) or more.

Sets:
  QGVAR(currentMicroburst)    - bool
  QGVAR(microburstWindSpeed)  - float m/s (0 if inactive)
  QGVAR(microburstTimer)      - int ticks remaining
  QGVAR(microburstSeverity)   - string "MODERATE" or "DAMAGING"
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
private _severity  = "MODERATE";

if (_timer > 0) then {
    // Active - decrement timer, keep wind speed
    _timer     = _timer - 1;
    _windSpeed = missionNamespace getVariable [QGVAR(microburstWindSpeed), 15 + (15 * ([round (time * 10), 101] call EFUNC(core,deterministicRandom)))];
    _severity  = missionNamespace getVariable [QGVAR(microburstSeverity), "MODERATE"];
} else {
    // Check trigger conditions
    private _ambientWind = vectorMagnitude wind;
    if (_overcast > 0.8
        && (_temp > 28)
        && (_RH > 70)
        && (_ambientWind < 3)
        && ([round (time * 10), 102] call EFUNC(core,deterministicRandom)) < 0.01
    ) then {
        _timer = 12;
        // Severity tier: a second roll below 0.5 gives a damaging gust.
        if (([round (time * 10), 104] call EFUNC(core,deterministicRandom)) < 0.5) then {
            _windSpeed = 26 + (10 * ([round (time * 10), 103] call EFUNC(core,deterministicRandom)));   // 26-36 m/s damaging
            _severity  = "DAMAGING";
        } else {
            _windSpeed = 15 + (15 * ([round (time * 10), 103] call EFUNC(core,deterministicRandom)));   // 15-30 m/s moderate
            _severity  = "MODERATE";
        };
    };
};

// ─── Output ──────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(currentMicroburst),   _timer > 0];
missionNamespace setVariable [QGVAR(microburstWindSpeed), _windSpeed];
missionNamespace setVariable [QGVAR(microburstTimer),     _timer];
missionNamespace setVariable [QGVAR(microburstSeverity),  _severity];
