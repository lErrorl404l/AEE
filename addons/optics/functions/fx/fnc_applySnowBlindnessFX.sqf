#include "..\..\script_component.hpp"

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
// Run in the player's own view: on foot (cameraOn == player) or in
// the player's vehicle (pilot/passenger/gunner - cameraOn is the
// vehicle).  Skip spectator/UAV-terminal/external cameras.
private _veh = vehicle _player;
if (isNil "_player" || !alive _player) exitWith {};
if (cameraOn != _player && {cameraOn != _veh}) exitWith {};

// Lift brightness and desaturate slightly — simulates dazzle
private _scale        = missionNamespace getVariable [QGVAR(snowBlindnessIntensity), 1.0];
private _brightness = 1 + (linearConversion [0, 1, _blindness, 0, 0.3, true] * _scale);
private _contrast   = 1 - (linearConversion [0, 1, _blindness, 0, 0.15, true] * _scale);
private _ccParams   = [_brightness, _contrast, 0, [0, 0, 0, 0], [1, 1, 1, _blindness * 0.1 * _scale], [0.9, 0.9, 0.9, 0]];

missionNamespace setVariable [QGVAR(snowBlindnessCC), if (_blindness > 0.01) then { _ccParams } else { [] }];
