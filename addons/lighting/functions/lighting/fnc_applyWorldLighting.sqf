#include "..\..\script_component.hpp"

/*
Bind the world lighting matcher to this machine's current state.

Reads the facts AEE already publishes: latitude (core getWorldLocation),
biome (aee_core_biome), terrain signals (aee_weather_terrainSignals)
and engine overcast.  Classifies the world and publishes the run-time
profile.  Never keyed by map name.  Safe with missing facts and on a
headless server.

Called once per environment tick from fnc_updateEnvironment.

Return: the profile [nightFactor, starScale, grainScale, hazeScale].
*/

private _loc = [] call EFUNC(lib,getWorldLocation);
private _latitude = _loc select 0;
if !(_latitude isEqualType 0) then { _latitude = 40; };

private _biome = missionNamespace getVariable [QEGVAR(core,biome), "Cfb"];
if !(_biome isEqualType "") then { _biome = "Cfb"; };

private _signals = missionNamespace getVariable [QEGVAR(weather,terrainSignals), []];
private _waterFrac = 0;
private _meanElev = 0;
if ((_signals isEqualType []) && {(count _signals) > 4}) then {
    _waterFrac = _signals select 3;
    _meanElev = _signals select 4;
};
if !(_waterFrac isEqualType 0) then { _waterFrac = 0; };
if !(_meanElev isEqualType 0) then { _meanElev = 0; };

private _overcast = overcast;
if !(_overcast isEqualType 0) then { _overcast = 0; };

// Biome group from the Koppen first letter.  5 means unknown.
private _first = toUpper (_biome select [0, 1]);
private _biomeGroup = 5;
if (_first == "A") then { _biomeGroup = 0; };
if (_first == "B") then { _biomeGroup = 1; };
if (_first == "C") then { _biomeGroup = 2; };
if (_first == "D") then { _biomeGroup = 3; };
if (_first == "E") then { _biomeGroup = 4; };

// Dry climates: Mediterranean (Cs*) and desert or steppe (BW*, BS*).
private _dry = 0;
private _prefix2 = toUpper (_biome select [0, 2]);
if ((_prefix2 == "CS") || (_prefix2 == "BW") || (_prefix2 == "BS")) then { _dry = 1; };

private _worldClass = [_latitude, _biomeGroup, _waterFrac, _meanElev, _dry] call FUNC(worldLightingClass);
private _profile = [_worldClass, _overcast] call FUNC(worldLightingProfile);

missionNamespace setVariable [QGVAR(worldLighting), _profile];
missionNamespace setVariable [QGVAR(worldLightingClass), _worldClass];

// Per-lever ownership (docs/wiki/research/engine-hdr-and-night-ceiling.md).
// AEE owns gusts and humidity only when the operator turns weatherOwnership
// on.  It keeps reading overcast, rain, fog and wind to avoid a feedback loop
// and to preserve compat_realweather.  Server-side only.
if (isServer && {missionNamespace getVariable [QGVAR(weatherOwnership), false]}) then {
    private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
    if (_humidity isEqualType 0) then {
        private _rh = (_humidity / 100) max 0 min 1;
        setHumidity _rh;
    };
    private _gusts = missionNamespace getVariable [QEGVAR(core,currentGusts), 0];
    if (_gusts isEqualType 0) then {
        private _g = _gusts max 0 min 1;
        // setGusts is binary: time (s) on the left, value on the right.
        0 setGusts _g;
    };
};

_profile
