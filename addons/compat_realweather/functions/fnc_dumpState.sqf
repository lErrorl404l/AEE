#include "..\script_component.hpp"

/*
compat_realweather state line.

One grep of "compat_realweather state" answers the module's state.  Read only:
the only write is the stateLogStarted flag.  AEE_LOG_INFO on the first call,
then AEE_LOG_DEBUG each tick, so it is readable without the trace switch and
cheap with it off.

The line carries the values this module publishes into AEE's shared core state
from weather.json: air temperature, humidity, pressure, overcast and the
active flag.  Each value carries a safe default so the first line is valid
before the JSON file has been read.

Nothing here changes state and nothing broadcasts.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _temp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_temp isEqualType 0) then { _temp = 15; };
private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if !(_humidity isEqualType 0) then { _humidity = 50; };
private _pressure = missionNamespace getVariable [QEGVAR(core,currentPressure), ISA_SEA_LEVEL_PRESSURE_HPA];
if !(_pressure isEqualType 0) then { _pressure = ISA_SEA_LEVEL_PRESSURE_HPA; };
private _overcast = missionNamespace getVariable [QEGVAR(core,overcast), 0];
if !(_overcast isEqualType 0) then { _overcast = 0; };
private _active = missionNamespace getVariable [QEGVAR(core,realWeatherActive), false];
if !(_active isEqualType false) then { _active = false; };

private _logMsg = format [
    "compat_realweather state | temp=%1 humidity=%2 pressure=%3 overcast=%4 active=%5",
    round (_temp * 100) / 100, round (_humidity * 100) / 100,
    round (_pressure * 100) / 100, round (_overcast * 100) / 100, _active
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
