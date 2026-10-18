#include "..\..\script_component.hpp"

/*
Rain-on-optics visual post-process: DynamicBlur only.

Reads QGVAR(rainOnOptics) (0–1) produced by fn_calculateRainOnOptics.
Gates on EGVAR(core,opticsEnabled).

FilmGrain is handled exclusively by fnc_applyNightGrain which already
accounts for rain contribution. This function computes and stores the
rain blur intensity in QGVAR(rainBlur); application is handled by
fnc_managePostProcess.
*/

if (!(missionNamespace getVariable [QEGVAR(core,opticsEnabled), true])) exitWith {};

private _accum  = missionNamespace getVariable [QGVAR(rainOnOptics), 0];
private _player = call CBA_fnc_currentUnit;

// Run in the player's own view: on foot (cameraOn == player) or in the
// player's vehicle (pilot/passenger/gunner - cameraOn is the vehicle).
// The sibling optics effects (solar glare, snow blindness, dew, seeing)
// use this same gate; the narrower cameraOn == _player test dropped the
// blur from every vehicle seat (issue #259).
private _veh = vehicle _player;
private _inView = (cameraOn == _player) || {cameraOn == _veh};

// Store 0 below gate so the arbiter can fade the effect out
private _blurScale = missionNamespace getVariable [QGVAR(rainBlurScale), 0.3];
missionNamespace setVariable [QGVAR(rainBlur), if (_accum > 0.05 && _inView) then { _accum * _blurScale } else { 0 }];
