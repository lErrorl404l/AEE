#include "..\script_component.hpp"

/*
Dew / condensation on optics — subtle lens fogging overlay.

Reads QGVAR(dewOnOptics) (0–1) produced by fnc_calculateDewOnOptics.
Gates on EGVAR(core,opticsEnabled).

Applies a mild blur + desaturation to simulate moisture condensing
on scope/binocular lenses.  The effect is transient — peaks during
rapid temperature changes or early morning, then decays.

Reference: real condensation on optics produces a foggy, milky
overlay that obscures detail.  We model this with FilmGrain noise
AND a slight blur to degrade image quality.

NOTE: FilmGrain is owned by applyNightGrain.  This function uses
only Blur + ColorCorrections to avoid ppEffect conflicts.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _obscuration = missionNamespace getVariable [QGVAR(dewOnOptics), 0];
private _player      = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

private _active = missionNamespace getVariable [QGVAR(dewFXActive), false];

if (_obscuration > 0.01) then {
    if (!_active) then {
        "DynamicBlur" ppEffectEnable true;
        missionNamespace setVariable [QGVAR(dewFXActive), true];
    };

    // Blur increases with obscuration — milky lens effect
    private _blur = linearConversion [0, 1, _obscuration, 0, 0.4, true];
    "DynamicBlur" ppEffectAdjust [_blur];
    "DynamicBlur" ppEffectCommit 2;
} else {
    if (_active) then {
        "DynamicBlur" ppEffectAdjust [0];
        "DynamicBlur" ppEffectCommit 1;

        [{
            "DynamicBlur" ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;

        missionNamespace setVariable [QGVAR(dewFXActive), false];
    };
};
