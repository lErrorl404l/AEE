#include "script_component.hpp"

params [["_biome", "Cfa", [""]], ["_month", 1, [0]]];

if (!isServer) exitWith {};

// Get climate normals for the biome
private _normals = [_biome] call FUNC(getClimateNormals);
private _tDay = _normals select 2;
private _tNight = _normals select 3;

// Get time-of-day factor (0-1, 0 = midnight, 0.5 = noon)
private _dayTime = dayTime;
private _dayFraction = _dayTime / 24;

// Diurnal interpolation using a sine wave centered on solar noon (~12:30)
// dayFraction 0.52 ~ solar noon → weight toward tDay
private _diurnalWeight = 0.5 + 0.5 * sin ((_dayFraction - 0.25) * 360);
private _T_base = _tNight select (_month - 1) + (_tDay select (_month - 1) - _tNight select (_month - 1)) * _diurnalWeight;

// Elevation correction — lapse rate -6.5 °C/km
private _elevation = GVAR(referenceAltitude);
if (_elevation <= 0) then {
    private _player = [] call CBA_fnc_currentUnit;
    if (!isNil "_player") then {
        _elevation = getTerrainHeightASL (getPos _player);
    } else {
        _elevation = getTerrainHeightASL [0, 0, 0];
    };
};
private _T_elevation = _T_base - 0.0065 * _elevation;

// Overcast correction — up to -4 °C under full overcast
private _overcast = overcast;
private _T_overcast = _T_elevation - 4 * _overcast;

// Round to one decimal
private _T_final = round (_T_overcast * 10) / 10;

missionNamespace setVariable ["ace_weather_currentTemperature", _T_final, true];
