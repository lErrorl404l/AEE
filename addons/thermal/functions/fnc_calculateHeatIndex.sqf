#include "..\script_component.hpp"

/*
Heat index (apparent temperature) per NWS Rothfusz 1990 (NOAA SR-90-23).
  HI = -42.379 + 2.04901523*T + 10.14333127*RH - 0.22475541*T*RH
       - 6.83783e-3*T^2 - 5.481717e-2*RH^2 + 1.22874e-3*T^2*RH
       + 8.5282e-4*T*RH^2 - 1.99e-6*T^2*RH^2

  T  — dry-bulb temperature in Fahrenheit
  RH — relative humidity in percent

Simple form below 80 °F or below 40 %RH:
  HI = 0.5 * (T + 61.0 + ((T - 68.0) * 1.2) + (RH * 0.094))

Adjustments:
  RH < 13 % and 80 <= T <= 112:  HI -= ((13 - RH) / 4) * sqrt((17 - |T - 95|) / 17)
  RH > 85 % and 80 <= T <= 87:   HI += ((RH - 85) / 10) * ((87 - T) / 5)

Stored in EGVAR(core,currentHeatIndex) for heat-stress modelling.
*/

if !(EGVAR(core,enabled)) exitWith {};

private _T_C = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _RH  = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];

if (isNil "_T_C") exitWith {};
if (isNil "_RH")  exitWith {};

// ─── Convert to Fahrenheit ────────────────────────────────────────────────
private _T_F = _T_C * 9 / 5 + 32;

// ─── Simple form — below 80 °F or below 40 %RH ───────────────────────────
private _HI_F = if (_T_F < 80 || _RH < 40) then {
    0.5 * (_T_F + 61.0 + ((_T_F - 68.0) * 1.2) + (_RH * 0.094))
} else {
    // ─── Full regression (Rothfusz 1990) ────────────────────────────────
    -42.379 + 2.04901523 * _T_F + 10.14333127 * _RH
        - 0.22475541 * _T_F * _RH
        - 6.83783e-3 * (_T_F ^ 2)
        - 5.481717e-2 * (_RH ^ 2)
        + 1.22874e-3 * (_T_F ^ 2) * _RH
        + 8.5282e-4 * _T_F * (_RH ^ 2)
        - 1.99e-6 * (_T_F ^ 2) * (_RH ^ 2)
};

// ─── Adjustments ──────────────────────────────────────────────────────────
if (_RH < 13 && _T_F >= 80 && _T_F <= 112) then {
    _HI_F = _HI_F - ((13 - _RH) / 4) * sqrt ((17 - abs (_T_F - 95)) / 17);
};
if (_RH > 85 && _T_F >= 80 && _T_F <= 87) then {
    _HI_F = _HI_F + ((_RH - 85) / 10) * ((87 - _T_F) / 5);
};

// ─── Convert back to Celsius ──────────────────────────────────────────────
private _HI_C = (_HI_F - 32) * 5 / 9;

missionNamespace setVariable [QEGVAR(core,currentHeatIndex), _HI_C];

_HI_C
