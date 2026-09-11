#include "..\script_component.hpp"

/*
Heat index using simplified WBGT (Wet-Bulb Globe Temperature) model.
  WBGT = 0.7 * Tw + 0.2 * Tg + 0.1 * T

  Tw — wet-bulb temperature via Stull 2011 approximation
  Tg — globe temperature (T + 15 in sun, T in shade, interpolated by overcast)

Stored in GVAR(currentWBGT) for thermal-stress modelling.
Also sets EGVAR(core,currentHeatIndex) for ACE3 medical potential.
*/

if !(EGVAR(core,enabled)) exitWith {};

private _T_C = EGVAR(core,currentTemperature);
private _RH  = EGVAR(core,currentHumidity);

if (isNil "_T_C") exitWith {};
if (isNil "_RH")  exitWith {};

// ─── Wet-bulb temperature (Stull 2011, accurate ±1 °C for 0–100 %RH, –20–50 °C)
// SQF atan returns degrees; Stull 2011 needs radians, so each term is
// converted with the rad operator.
private _sqrtRHP1 = sqrt (_RH + 8.313659);
private _Tw = _T_C * (atan (0.151977 * _sqrtRHP1)) * 0.0174532925
    + (atan (_T_C + _RH)) * 0.0174532925
    - (atan (_RH - 1.676331)) * 0.0174532925
    + 0.00391838 * (_RH ^ 1.5) * (atan (0.023101 * _RH)) * 0.0174532925
    - 4.686035;

// ─── Globe temperature — interpolate sun/shade by overcast
//     Full sun (overcast = 0): Tg = T + 15
//     Full shade (overcast = 1): Tg = T
private _Tg = _T_C + 15 * (1 - overcast);

// ─── WBGT
private _WBGT = 0.7 * _Tw + 0.2 * _Tg + 0.1 * _T_C;

// Store (QGVAR only — ACE3 medical has no heat index system)
missionNamespace setVariable [QEGVAR(core,currentWBGT), _WBGT];

_WBGT
