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
Example: [] call aee_diagnostics_fnc_dumpState
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
private _isReady = missionNamespace getVariable [QEGVAR(core,isReady), false];
if !(_isReady isEqualType false) then { _isReady = false; };

// Ownership sentinels (ADR-027). Read each declared property from the live
// config tree and compare it to AEE's value. A mismatch is the silent loss:
// another mod loaded after AEE and won the config merge for a class AEE owns.
// Read only; the config tree is never written here.
private _sentinels = missionNamespace getVariable [QEGVAR(core,ownershipSentinels), []];
if !(_sentinels isEqualType []) then { _sentinels = []; };
private _mismatches = [];
{
    _x params [["_id", ""], ["_path", []], ["_prop", ""], ["_type", ""], ["_expected", 0]];
    private _cfg = configFile;
    { _cfg = _cfg >> _x; } forEach _path;
    private _entry = _cfg >> _prop;
    private _live = switch (_type) do {
        case "number": { getNumber _entry };
        case "array": { getArray _entry };
        case "text": { getText _entry };
        default { nil };
    };
    private _ok = if (isNull _entry) then { false } else {
        switch (_type) do {
            case "number": { abs (_live - _expected) <= (0.000001 + abs (_expected) * 0.000001) };
            case "array": { _live isEqualTo _expected };
            case "text": { _live isEqualTo _expected };
            default { false };
        };
    };
    if !(_ok) then {
        _mismatches pushBack format ["%1=%2(want %3)", _id, _live, _expected];
    };
} forEach _sentinels;

private _ownership = if (_mismatches isEqualTo []) then { "ok" } else { format ["MISMATCH(%1)", count _mismatches] };
if (_mismatches isNotEqualTo []) then {
    private _ownershipWarn = format [
        "ownership sentinels: %1 - a later-loading mod won the config merge for a class AEE owns",
        _mismatches joinString ", "
    ];
    AEE_LOG_WARN(_ownershipWarn);
};

private _logMsg = format [
    "core state | weather=temp:%1C press:%2hPa rh:%3%% rho:%4 overcast:%5 sunElev:%6 | light=lux:%7 ambient:%8 night:%9 | progression=seed:%10 realWeather:%11 | ready:%12 | ownership:%13",
    round (_tempC * 100) / 100, round (_pressHPa * 100) / 100, round _humidity,
    round (_rho * 10000) / 10000, round (_overcast * 1000) / 1000, round (_sunElev * 100) / 100,
    round _lux, round _ambientLux, _night,
    _seed, _realWeather, _isReady, _ownership
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
