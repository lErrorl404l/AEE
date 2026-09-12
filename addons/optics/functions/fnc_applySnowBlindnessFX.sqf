#include "..\script_component.hpp"

/*
Snow blindness / photokeratitis visual overlay.

Reads QGVAR(snowBlindness) (0–1) produced by fnc_calculateSnowBlindness.
Gates on EGVAR(core,opticsEnabled).

Applies a subtle white RadialBlur overlay that brightens the periphery,
simulating the dazzle and tearing from high-albedo snow reflection.

Reference values:
  • Real snow blindness is painful and debilitating
  • In-game we model the early stage: mild dazzle, squinting
  • White overlay alpha 0–0.1 (subtle, not obstructive)
  • Combined with slight radial blur for periphery wash
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _blindness = missionNamespace getVariable [QGVAR(snowBlindness), 0];
private _player    = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

private _active = missionNamespace getVariable [QGVAR(snowBlindFXActive), false];

if (_blindness > 0.01) then {
    if (!_active) then {
        "ColorCorrections" ppEffectEnable true;
        missionNamespace setVariable [QGVAR(snowBlindFXActive), true];
    };

    // Lift brightness and desaturate slightly — simulates dazzle
    private _brightness = linearConversion [0, 1, _blindness, 1, 1.3, true];
    private _contrast   = linearConversion [0, 1, _blindness, 1, 0.85, true];
    "ColorCorrections" ppEffectAdjust [_brightness, _contrast, 0, [0, 0, 0, 0], [1, 1, 1, _blindness * 0.1], [0.9, 0.9, 0.9, 0]];
    "ColorCorrections" ppEffectCommit 2;
} else {
    if (_active) then {
        "ColorCorrections" ppEffectAdjust [1, 1, 0, [0, 0, 0, 0], [1, 1, 1, 0], [0.9, 0.9, 0.9, 0]];
        "ColorCorrections" ppEffectCommit 1;

        [{
            "ColorCorrections" ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;

        missionNamespace setVariable [QGVAR(snowBlindFXActive), false];
    };
};
