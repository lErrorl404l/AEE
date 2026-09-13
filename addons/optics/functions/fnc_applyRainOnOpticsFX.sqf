#include "..\script_component.hpp"

/*
Rain-on-optics visual post-process: DynamicBlur only.

Reads QGVAR(rainOnOptics) (0–1) produced by fn_calculateRainOnOptics.
Gates on EGVAR(core,opticsEnabled).

FilmGrain is handled exclusively by fnc_applyNightGrain which already
accounts for rain contribution. This function computes and stores the
rain blur intensity in QGVAR(rainBlur); application is handled by
fnc_managePostProcess.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _accum  = missionNamespace getVariable [QGVAR(rainOnOptics), 0];
private _player = call CBA_fnc_currentUnit;

// Store 0 below gate so the arbiter can fade the effect out
private _blurScale = missionNamespace getVariable [QGVAR(rainBlurScale), 0.3];
missionNamespace setVariable [QGVAR(rainBlur), if (_accum > 0.05 && cameraOn == _player) then { _accum * _blurScale } else { 0 }];
