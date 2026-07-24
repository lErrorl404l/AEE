#include "script_component.hpp"

params [["_biome", "Cfa", [""]], ["_month", 1, [0]]];

if (!isServer) exitWith {};

// Get biome sea-level pressure
private _normals = [_biome] call FUNC(getClimateNormals);
private _P_sea = _normals select 0;

// Get elevation
private _elevation = GVAR(referenceAltitude);
if (_elevation <= 0) then {
    private _player = [] call CBA_fnc_currentUnit;
    if (!isNil "_player") then {
        _elevation = getTerrainHeightASL (getPos _player);
    } else {
        _elevation = getTerrainHeightASL [0, 0, 0];
    };
};

// Barometric formula — hypsometric equation
// P_station = P_sea * (T_std / (T_std - 0.0065 * elevation))^5.2559
private _T_std = 288.15;  // K
private _lapseRate = 0.0065;
private _exponent = 5.2559;

private _ratio = _T_std / (_T_std - _lapseRate * _elevation);
private _P_station = _P_sea * (_ratio ^ _exponent);

// Round to one decimal
private _P_final = round (_P_station * 10) / 10;

missionNamespace setVariable ["ace_weather_currentPressure", _P_final, true];
