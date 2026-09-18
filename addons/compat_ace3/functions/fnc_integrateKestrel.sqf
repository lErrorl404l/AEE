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

    A MISSION can re-enable ace_weather via its own settings module.  ACE3's
    server tick then recomputes currentTemperature from ITS model (a static
    per-map table + random shift) every updateInterval and races this write.
    AEE is the authoritative weather simulation, so this function re-asserts
    ace_weather_enabled = false every tick and wins the race (issue #181).
    A mission author who genuinely wants ACE3's weather model should not
    load the compat at all.

    ace_weather_currentTemperature is written as the UN-LAPSED base
    temperature (aee_core_currentTemperatureBase): ACE3's
    calculateTemperatureAtHeight applies its own 6.5 C/km lapse on read, so
    writing the lapse-adjusted currentTemperature double-counted altitude
    (AEE's -13 C at 26 m became ACE's -37 C at 3 km).  With the base, ACE3's
    lapse reproduces AEE's exact value at any height.

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

// Re-assert weather ownership.  A mission settings module can re-enable
// ace_weather after preInit; ACE3's server tick would then recompute the
// weather variables from its own model and race this write.  Setting it
// false every tick stops ACE3's tick and keeps AEE authoritative.
missionNamespace setVariable ["ace_weather_enabled", false];
missionNamespace setVariable ["ace_weather_windSimulation", false];

missionNamespace setVariable ["ace_weather_currentTemperature", missionNamespace getVariable ["aee_core_currentTemperatureBase", 15]];
missionNamespace setVariable ["ace_weather_currentHumidity", missionNamespace getVariable ["aee_core_currentHumidity", 0]];
missionNamespace setVariable ["ace_weather_currentOvercast", missionNamespace getVariable ["aee_core_overcast", overcast]];

// AEE extensions — third-party consumers only.  Stock ACE3 reads neither.
missionNamespace setVariable ["ace_weather_currentHeatIndex", missionNamespace getVariable ["aee_core_currentHeatIndex", 15]];
missionNamespace setVariable ["ace_weather_currentWBGT", missionNamespace getVariable ["aee_core_currentWBGT", 15]];
