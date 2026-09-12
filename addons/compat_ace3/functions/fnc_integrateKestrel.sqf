#include "..\script_component.hpp"
/*
    AEE — ACE3 Weather State Population

    Populates ACE3 weather mission variables from AEE state so the Kestrel
    4500 and other ACE3 consumers display AEE's temperature, humidity, and
    overcast.

    Verified against the ACE3 source (addons/weather, addons/kestrel4500):
      - ace_weather_currentTemperature  read via ace_weather_fnc_calculateTemperatureAtHeight
      - ace_weather_currentHumidity     read directly
      - ace_weather_currentOvercast     read via ace_weather_fnc_calculateBarometricPressure

    Runs on every machine (server and clients).  AEE state is deterministic,
    so each machine computes identical values.  ace_weather_enabled = false
    stops ACE3's own server tick, so these writes persist.

    ace_weather_currentHeatIndex and ace_weather_currentWBGT are AEE
    EXTENSIONS: stock ACE3 defines neither variable and reads neither.  They
    are published for third-party mods that want AEE's authoritative NWS heat
    index (Rothfusz 1990) and Stull 2011 WBGT.

    The wind-barb (SHIFT+K wind info) reads the engine wind command directly,
    which AEE drives with setWind, so it follows AEE automatically.

    Guarded by isClass on ace_weather. No return value.
*/

if (!isClass (configFile >> "CfgPatches" >> "ace_weather")) exitWith {};
if (!(missionNamespace getVariable ["aee_core_enabled", false])) exitWith {};

missionNamespace setVariable ["ace_weather_currentTemperature", missionNamespace getVariable ["aee_core_currentTemperature", 15]];
missionNamespace setVariable ["ace_weather_currentHumidity", missionNamespace getVariable ["aee_core_currentHumidity", 0]];
missionNamespace setVariable ["ace_weather_currentOvercast", missionNamespace getVariable ["aee_core_overcast", overcast]];

// AEE extensions — third-party consumers only.  Stock ACE3 reads neither.
missionNamespace setVariable ["ace_weather_currentHeatIndex", missionNamespace getVariable ["aee_core_currentHeatIndex", 15]];
missionNamespace setVariable ["ace_weather_currentWBGT", missionNamespace getVariable ["aee_core_currentWBGT", 15]];
