#include "..\script_component.hpp"
/*
    AEE — Real Weather Integration

    Reads weather.json from the mission folder and publishes the values into
    AEE's shared state (aee_core_* mission variables). The file is written
    by tools/weather_fetch.py; that file documents the format.

    weather.json format (all values required):
      temperatureC  — air temperature in Celsius
      humidityPct   — relative humidity in percent (0..100)
      pressureHpa   — station pressure in hectopascals
      overcast      — cloud cover fraction (0..1)

    The values overwrite AEE's simulated state. AEE's own simulation tick
    recomputes them on the next update, so the intended consumption is for
    the maintainer to gate the simulation on aee_core_realWeatherActive
    (set true here) when real data must win.

    The Real Weather host mod's public API could not be verified from its
    source (no public repository found). When the host mod is present, hook
    its weather-application function here to publish AEE's state into the
    host mod's world. The exact function name must be verified from the host
    mod's source before enabling the guarded block below.

    No return value.
*/

if (!isClass (configFile >> "CfgPatches" >> "aee_core")) exitWith {};

private _json = loadFile "weather.json";
if (_json == "") exitWith {};

private _data = [_json] call CBA_fnc_parseJSON;
if (isNil "_data") exitWith {};

private _temp = _data getVariable "temperatureC";
private _humidity = _data getVariable "humidityPct";
private _pressure = _data getVariable "pressureHpa";
private _overcast = _data getVariable "overcast";

if ((isNil "_temp")
    || (isNil "_humidity")
    || (isNil "_pressure")
    || (isNil "_overcast")
) exitWith {};

missionNamespace setVariable [QEGVAR(core,currentTemperature), _temp];
missionNamespace setVariable [QEGVAR(core,currentHumidity), _humidity];
missionNamespace setVariable [QEGVAR(core,currentPressure), _pressure];
missionNamespace setVariable [QEGVAR(core,overcast), _overcast];
missionNamespace setVariable [QEGVAR(core,realWeatherActive), true];

// ─── Real Weather host-mod hook ─────────────────────────────────────────
// The host mod's public API is not verifiable from public sources. When the
// host mod is present, call its weather-application function here to publish
// AEE's state into the host mod's world. Verify the exact function name from
// the host mod's source before enabling this block.
if (isClass (configFile >> "CfgPatches" >> "realweather")) then {
    // [QEGVAR(core,currentTemperature), QEGVAR(core,currentHumidity), QEGVAR(core,currentPressure)] call realweather_fnc_applyWeather;
};
