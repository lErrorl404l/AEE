#include "script_component.hpp"

params [["_biome", "Cfa", [""]], ["_month", 1, [0]]];

if (!isServer) exitWith {};

// Get biome humidity normals
private _normals = [_biome] call FUNC(getClimateNormals);
private _humidityArray = _normals select 4;
private _RH = _humidityArray select (_month - 1);

// Saturation under overcast or rain
if (overcast > 0.7 || rain > 0) then {
    _RH = 100;
};

// Round to integer
private _RH_final = round _RH;

missionNamespace setVariable ["ace_weather_currentHumidity", _RH_final, true];
