#include "script_component.hpp"

// v1: passthrough — read engine wind, set ACE3 output
if (isNil "ace_weather_currentWind") then {
    private _wind = wind;
    private _gusts = gust;
    missionNamespace setVariable ["ace_weather_currentWind", _wind, true];
    missionNamespace setVariable ["ace_weather_currentGusts", _gusts, true];
};
