#include "..\script_component.hpp"

/*
Snow blindness / photokeratitis visual overlay.

Reads QGVAR(snowBlindness) (0–1) produced by fnc_calculateSnowBlindness.
Gates on EGVAR(core,opticsEnabled).

Stores the ColorCorrections params in QGVAR(snowBlindnessCC). The arbiter
(fnc_managePostProcess) applies them. An empty array means no snow
blindness, so the arbiter fades the effect out.

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

// Lift brightness and desaturate slightly — simulates dazzle
private _brightness = linearConversion [0, 1, _blindness, 1, 1.3, true];
private _contrast   = linearConversion [0, 1, _blindness, 1, 0.85, true];
private _ccParams   = [_brightness, _contrast, 0, [0, 0, 0, 0], [1, 1, 1, _blindness * 0.1], [0.9, 0.9, 0.9, 0]];

missionNamespace setVariable [QGVAR(snowBlindnessCC), if (_blindness > 0.01) then { _ccParams } else { [] }];
