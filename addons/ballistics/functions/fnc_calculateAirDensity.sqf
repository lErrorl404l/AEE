#include "..\script_component.hpp"

// Read current weather state
private _T_C = EGVAR(core,currentTemperature);
private _P_hPa = EGVAR(core,currentPressure);
private _RH = EGVAR(core,currentHumidity);

if (isNil "_T_C") exitWith {};
if (isNil "_P_hPa") exitWith {};
if (isNil "_RH") then { _RH = 50; };

// Step 1 — Saturation vapor pressure (Buck 1996)
private _e_s = 6.1121 * exp((18.678 - _T_C / 234.5) * _T_C / (257.14 + _T_C));

// Step 2 — Actual vapor pressure
private _e = _e_s * _RH / 100;

// Step 3 — Virtual temperature
private _T_K = _T_C + 273.15;
private _T_v = _T_K / (1 - 0.37802 * _e / _P_hPa);

// Step 4 — Density
private _P_Pa = _P_hPa * 100;
private _R_d = 287.05287;  // J/(kg·K)
private _rho = _P_Pa / (_R_d * _T_v);  // kg/m³

// Store.  Core namespace is the single source: mobility (engine power,
// helicopter lift, turbulence) and ACE3 ballistics read it from there.
missionNamespace setVariable [QEGVAR(core,currentAirDensity), _rho];
