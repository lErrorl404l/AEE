#include "..\script_component.hpp"

/*
WBGT (Wet-Bulb Globe Temperature) - the ISO 7243 heat-stress index.
  WBGT = 0.7 * Tw + 0.2 * Tg + 0.1 * T     (outdoor, sun load)

  Tw — wet-bulb temperature via Stull 2011 approximation
  Tg — globe temperature from the black-globe energy balance
       (fnc_calculateGlobeTemperature), NOT a T+15 guess
  T  — dry-bulb (air) temperature

Stored in EGVAR(core,currentWBGT) for thermal-stress modelling.
The old code guessed Tg = T + 15 in sun, T in shade.  That guess has
no physical basis; the globe now comes from the real energy balance
against MRT and solar load (issue #124, ISO 7726 + 7243).
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

// ─── Globe temperature — black-globe energy balance (ISO 7726) ────────────
// The globe solves absorbed solar + longwave vs emitted + convection
// against MRT, so it reads above air in sun (hot surroundings) and
// below air on clear nights (cold sky).  Replaces the old T+15 guess.
private _Tg = [] call FUNC(calculateGlobeTemperature);

// ─── WBGT (outdoor, solar-load weighting per ISO 7243)
private _WBGT = 0.7 * _Tw + 0.2 * _Tg + 0.1 * _T_C;

// Store for thermal-stress modelling
missionNamespace setVariable [QEGVAR(core,currentWBGT), _WBGT];

_WBGT
