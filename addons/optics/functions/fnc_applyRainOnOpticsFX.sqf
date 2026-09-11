#include "..\script_component.hpp"

/*
Rain-on-optics visual post-process: DynamicBlur + FilmGrain.

Reads QGVAR(rainOnOptics) (0–1) produced by fn_calculateRainOnOptics.
Gates on EGVAR(core,opticsEnabled).

When accumulation > 0.05 and cameraOn == player, applies screen-wide blur
and film grain proportional to accumulation.  Fades both out over 0.5 s
and disables them via CBA_fnc_waitAndExecute when conditions clear, using
a flag (QGVAR(rainFXActive)) to avoid spawning redundant callbacks.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _accum  = missionNamespace getVariable [QGVAR(rainOnOptics), 0];
private _player = call CBA_fnc_currentUnit;
private _active = missionNamespace getVariable [QGVAR(rainFXActive), false];

if (_accum > 0.05 && cameraOn == _player) then {
    if (!_active) then {
        "DynamicBlur" ppEffectEnable true;
        "FilmGrain"  ppEffectEnable true;
        missionNamespace setVariable [QGVAR(rainFXActive), true];
    };

    "DynamicBlur" ppEffectAdjust [_accum * 0.3];
    "DynamicBlur" ppEffectCommit 1;

    "FilmGrain" ppEffectAdjust [_accum * 0.1, _accum * 2, 0.1, 0, 0, false];
    "FilmGrain" ppEffectCommit 1;
} else {
    if (_active) then {
        "DynamicBlur" ppEffectAdjust [0];
        "DynamicBlur" ppEffectCommit 0.5;

        "FilmGrain" ppEffectAdjust [0, 0, 0, 0, 0, false];
        "FilmGrain" ppEffectCommit 0.5;

        [{
            "DynamicBlur" ppEffectEnable false;
            "FilmGrain"   ppEffectEnable false;
        }, [], 1] call CBA_fnc_waitAndExecute;

        missionNamespace setVariable [QGVAR(rainFXActive), false];
    };
};
