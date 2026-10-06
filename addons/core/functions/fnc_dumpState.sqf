#include "..\script_component.hpp"

/*
Consolidated core state line.

One grep of "core state" answers the base environment the other modules build
on: the smoothed weather EMA, the physics scalars, the solar and illuminance
terms and the module flags.  Emitted once at AEE_LOG_INFO on the first call,
then at AEE_LOG_DEBUG every tick, so the state is readable without the trace
switch and cheap with it off.

The line reads only.  The only write is the stateLogStarted flag.  It reads
the published aee_core_* state that the local update tick and the atmos,
ballistics and environmental kernels write.

Arguments: none.

Return Value: Nothing.
Public: No
Example: [] call aee_core_fnc_dumpState
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _tempC = missionNamespace getVariable [QEGVAR(core,currentTemperature), 0];
if !(_tempC isEqualType 0) then { _tempC = 0; };
private _pressHPa = missionNamespace getVariable [QEGVAR(core,currentPressure), 0];
if !(_pressHPa isEqualType 0) then { _pressHPa = 0; };
private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 0];
if !(_humidity isEqualType 0) then { _humidity = 0; };
private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 0];
if !(_rho isEqualType 0) then { _rho = 0; };
private _overcast = missionNamespace getVariable [QEGVAR(core,overcast), 0];
if !(_overcast isEqualType 0) then { _overcast = 0; };
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), 0];
if !(_sunElev isEqualType 0) then { _sunElev = 0; };
private _lux = missionNamespace getVariable [QEGVAR(core,illuminanceLux), 0];
if !(_lux isEqualType 0) then { _lux = 0; };
private _ambientLux = missionNamespace getVariable [QEGVAR(core,ambientLux), 0];
if !(_ambientLux isEqualType 0) then { _ambientLux = 0; };
private _night = missionNamespace getVariable [QEGVAR(core,lightIsNight), false];
if !(_night isEqualType false) then { _night = false; };
private _seed = missionNamespace getVariable [QEGVAR(core,weatherProgressionSeed), 0];
if !(_seed isEqualType 0) then { _seed = 0; };
private _realWeather = missionNamespace getVariable [QEGVAR(core,realWeatherActive), false];
if !(_realWeather isEqualType false) then { _realWeather = false; };
private _isReady = missionNamespace getVariable [QGVAR(isReady), false];
if !(_isReady isEqualType false) then { _isReady = false; };

private _logMsg = format [
    "core state | weather=temp:%1C press:%2hPa rh:%3%% rho:%4 overcast:%5 sunElev:%6 | light=lux:%7 ambient:%8 night:%9 | progression=seed:%10 realWeather:%11 | ready:%12",
    round (_tempC * 100) / 100, round (_pressHPa * 100) / 100, round _humidity,
    round (_rho * 10000) / 10000, round (_overcast * 1000) / 1000, round (_sunElev * 100) / 100,
    round _lux, round _ambientLux, _night,
    _seed, _realWeather, _isReady
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
