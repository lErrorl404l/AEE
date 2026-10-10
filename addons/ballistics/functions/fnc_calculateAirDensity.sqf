#include "..\script_component.hpp"

// Read current weather state
private _T_C = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _P_hPa = missionNamespace getVariable [QEGVAR(core,currentPressure), 1013];
private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];

if !(_T_C isEqualType 0) then { _T_C = 15; };
if !(_P_hPa isEqualType 0) then { _P_hPa = 1013; };
if !(_RH isEqualType 0) then { _RH = 50; };

// The density formula is the pure kernel FUNC(calculateAirDensityKernel).
// The dispatcher selects the native kernel when the dev extension is ready
// and the SQF reference otherwise; both are the same formula.
private _rho = ["calculateAirDensityKernel", [_T_C, _P_hPa, _RH]] call EFUNC(core,dispatchKernel);
if (_rho isEqualType "") then { _rho = parseNumber _rho; };
if !(_rho isEqualType 0) then {
    _rho = [_T_C, _P_hPa, _RH] call FUNC(calculateAirDensityKernel);
};

// Store.  Core namespace is the single source: mobility (engine power,
// helicopter lift, turbulence) and ACE3 ballistics read it from there.
missionNamespace setVariable [QEGVAR(core,currentAirDensity), _rho];
