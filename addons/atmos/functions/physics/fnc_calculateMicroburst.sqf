#include "..\..\script_component.hpp"

/*
Microburst detection - sudden violent downdraft in convective conditions.

Requires: overcast > 0.8, temp above the configured threshold, RH > 70%,
ambient wind < 3 m/s. The configured activation chance applies per tick
when all conditions hold. Once triggered, a moderate gust (15-30 m/s) or
a damaging gust (26 m/s to the configured ceiling) persists for the
configured duration (~60 s at 5 s PFH). The NWS damaging microburst
criterion is a gust of 26 m/s (50 kt) or more.

Sets:
  QGVAR(currentMicroburst)    - bool
  QGVAR(microburstWindSpeed)  - float m/s (0 if inactive)
  QGVAR(microburstTimer)      - int ticks remaining
  QGVAR(microburstSeverity)   - string "MODERATE" or "DAMAGING"
*/

// ─── Inputs ──────────────────────────────────────────────────────────────
private _overcast  = overcast;
private _temp      = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _RH        = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];

if (isNil "_temp") then { _temp = 20; };
if (isNil "_RH")   then { _RH   = 50; };

// ─── Settings ─────────────────────────────────────────────────────────────
private _tempThreshold = missionNamespace getVariable [QGVAR(microburstTempThreshold), 28];
private _duration      = missionNamespace getVariable [QGVAR(microburstDuration), 12];
private _gustMax       = missionNamespace getVariable [QGVAR(microburstGustMax), 36];
private _interval      = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
private _chance        = missionNamespace getVariable [QGVAR(microburstChance), 0.01];
_chance = _chance * (_interval / 5);

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
        && (_temp > _tempThreshold)
        && (_RH > 70)
        && (_ambientWind < 3)
        && ([round (time * 10), 102] call EFUNC(core,deterministicRandom)) < _chance
    ) then {
        _timer = _duration;
        // Severity tier: a second roll below 0.5 gives a damaging gust.
        if (([round (time * 10), 104] call EFUNC(core,deterministicRandom)) < 0.5) then {
            _windSpeed = 26 + ((_gustMax - 26) * ([round (time * 10), 103] call EFUNC(core,deterministicRandom)));   // 26 m/s to configured ceiling
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
