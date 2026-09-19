#include "..\..\script_component.hpp"

/*
Dew / condensation on optics — subtle lens fogging overlay.

Reads QGVAR(dewOnOptics) (0–1) produced by fnc_calculateDewOnOptics.
Gates on EGVAR(core,opticsEnabled).

Computes and stores the dew blur intensity in QGVAR(dewBlur);
application is handled by fnc_managePostProcess.

Reference: real condensation on optics produces a foggy, milky
overlay that obscures detail.  We model this with FilmGrain noise
AND a slight blur to degrade image quality.

NOTE: FilmGrain is owned by applyNightGrain.  This function computes
only the blur contribution to avoid ppEffect conflicts.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _obscuration = missionNamespace getVariable [QGVAR(dewOnOptics), 0];
private _player      = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

// Blur increases with obscuration — milky lens effect; store 0 below gate so the arbiter can fade
private _blur = linearConversion [0, 1, _obscuration, 0, (missionNamespace getVariable [QGVAR(dewBlurMax), 0.4]), true];
missionNamespace setVariable [QGVAR(dewBlur), [0, _blur] select (_obscuration > 0.01)];
