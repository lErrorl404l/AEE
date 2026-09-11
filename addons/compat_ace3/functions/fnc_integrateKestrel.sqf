#include "..\script_component.hpp"
/*
    AEE — ACE3 Kestrel 4500 Data Population

    Populates ACE3 weather mission variables from AEE state so the Kestrel
    4500 displays AEE's temperature, humidity, and overcast.

    Verified against the ACE3 source (addons/weather, addons/kestrel4500):
      - ace_weather_currentTemperature  read via ace_weather_fnc_calculateTemperatureAtHeight
      - ace_weather_currentHumidity     read directly
      - ace_weather_currentOvercast     read via ace_weather_fnc_calculateBarometricPressure

    The wind-barb (SHIFT+K wind info) reads the engine wind command directly,
    which AEE drives with setWind, so it follows AEE automatically.

    Guarded by isClass on ace_weather. No return value.
*/

if (!isClass (configFile >> "CfgPatches" >> "ace_weather")) exitWith {};
if (!(missionNamespace getVariable ["aee_core_enabled", false])) exitWith {};

missionNamespace setVariable ["ace_weather_currentTemperature", missionNamespace getVariable ["aee_core_currentTemperature", 15]];
missionNamespace setVariable ["ace_weather_currentHumidity", missionNamespace getVariable ["aee_core_currentHumidity", 0]];
missionNamespace setVariable ["ace_weather_currentOvercast", missionNamespace getVariable ["aee_core_overcast", overcast]];
