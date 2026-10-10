#include "..\script_component.hpp"

private _rho = EGVAR(core,currentAirDensity);
private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _P = missionNamespace getVariable [QEGVAR(core,currentPressure), ISA_SEA_LEVEL_PRESSURE_HPA];
private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _biome = EGVAR(core,biome);
private _biomeName = EGVAR(core,biomeName);

private _logMsg = format [
    "Biome: %1 (%2) | Temp: %3 C | Pressure: %4 hPa | RH: %5%% | Density: %6 kg/m3",
    _biomeName, _biome,
    [_T, 1] call CBA_fnc_formatNumber,
    [_P, 1] call CBA_fnc_formatNumber,
    [_RH, 0] call CBA_fnc_formatNumber,
    // CBA_fnc_formatNumber is [number, integerWidth, decimalPlaces].
    // Passing 4 as the 2nd arg padded the integer to 4 digits ("0001");
    // the density needs 4 DECIMAL places (issue #177).
    [_rho, 0, 4] call CBA_fnc_formatNumber
];
AEE_LOG_INFO(_logMsg);
