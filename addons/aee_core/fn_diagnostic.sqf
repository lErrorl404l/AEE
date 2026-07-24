#include "script_component.hpp"

private _rho = GVAR(currentAirDensity);
private _T = ace_weather_currentTemperature;
private _P = ace_weather_currentPressure;
private _RH = ace_weather_currentHumidity;
private _biome = GVAR(biome);
private _biomeName = GVAR(biomeName);

diag_log text format [
    "[AEE] Biome: %1 (%2) | Temp: %3 C | Pressure: %4 hPa | RH: %5%% | Density: %6 kg/m3",
    _biomeName, _biome,
    [_T, 1] call CBA_fnc_formatNumber,
    [_P, 1] call CBA_fnc_formatNumber,
    [_RH, 0] call CBA_fnc_formatNumber,
    [_rho, 4] call CBA_fnc_formatNumber
];
