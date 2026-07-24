/*
    AEE - ACE3 Compatibility Layer
    Detects ACE3 at mission start and disables ACE3's weather simulation
    so AEE can own the ace_weather_current* variables.
*/

if (is3DEN) exitWith {};

// Check if ACE3 weather system is loaded
if (isNil "ace_weather_currentTemperature") exitWith {
    diag_log "[AEE][ACE3 Compat] ACE3 weather not detected — skipping compat layer";
};

// ACE3 weather is present — disable its simulation so AEE takes over
ace_weather_windSimulation = false;
ace_weather_enableWind = false;
ace_weather_enableRain = false;
ace_weather_enableFog = false;
ace_weather_enableOvercast = false;

diag_log "[AEE][ACE3 Compat] ACE3 weather detected and disabled — AEE now controls ace_weather_current* variables";
