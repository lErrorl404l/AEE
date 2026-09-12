#include "..\script_component.hpp"

/*
Rain-on-optics visual post-process: DynamicBlur only.

Reads QGVAR(rainOnOptics) (0–1) produced by fn_calculateRainOnOptics.
Gates on EGVAR(core,opticsEnabled).

FilmGrain is handled exclusively by fnc_applyNightGrain which already
accounts for rain contribution. This function only drives DynamicBlur
to simulate water droplets blurring the view.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _accum  = missionNamespace getVariable [QGVAR(rainOnOptics), 0];
private _player = call CBA_fnc_currentUnit;
private _active = missionNamespace getVariable [QGVAR(rainFXActive), false];

if (_accum > 0.05 && cameraOn == _player) then {
    if (!_active) then {
        "DynamicBlur" ppEffectEnable true;
        missionNamespace setVariable [QGVAR(rainFXActive), true];
    };

    "DynamicBlur" ppEffectAdjust [_accum * 0.3];
    "DynamicBlur" ppEffectCommit 1;
} else {
    if (_active) then {
        "DynamicBlur" ppEffectAdjust [0];
        "DynamicBlur" ppEffectCommit 0.5;

        [{
            "DynamicBlur" ppEffectEnable false;
        }, [], 1] call CBA_fnc_waitAndExecute;

        missionNamespace setVariable [QGVAR(rainFXActive), false];
    };
};
