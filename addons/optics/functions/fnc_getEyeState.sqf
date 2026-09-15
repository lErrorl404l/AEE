#include "..\script_component.hpp"
/*
 * Shared eye-state foundation.
 *
 * Every eye-space system (rain droplets, solar glare, illuminance, muzzle
 * flash glare, wet-eye streaking) needs the same three vectors:
 *
 *   eyePos  - the ACTUAL eye position in ASL (stance/head-pose aware)
 *   forward - the camera look vector (unit length)
 *   up      - the camera up vector (parallax/roll correct)
 *
 * Previously each system computed these independently - duplicated code
 * that drifted (the rain-droplet bug: attaching to the static HEAD memory
 * point instead of the eye was one such drift).  This function is the
 * single source of truth: ONE computation per tick, cached, consumed by
 * every eye-space system.
 *
 * eyePos is the canonical eye anchor: it accounts for stance and head
 * pose (prone = low, leaning = offset) and is what the game's own camera
 * uses in first person.  getCameraViewDirection gives the look vector.
 * eyeDirection gives [forward, up] - the full basis needed for correct
 * glare/parallax geometry.
 *
 * Cached per tick in missionNamespace so N consumers cost 1 eyePos call.
 * The cache is keyed by diag_frameNo: stale entries are recomputed, so
 * any caller in any frame gets fresh values without extra eyePos calls.
 */
params ["_unit"];

if (isNil "_unit") then { _unit = call CBA_fnc_currentUnit; };
if (isNull _unit) exitWith { [getPosASLVisual _unit, [0, 0, 1], [0, 1, 0]] };

private _frame = diag_frameNo;
private _cache = missionNamespace getVariable [QGVAR(eyeState), []];
if (count _cache >= 3 && {_cache select 0 == _frame}) exitWith {
    _cache select 1
};

private _eye = eyePos _unit;
private _eyeDir = eyeDirection _unit;
private _fwd = _eyeDir select 0;
private _up = _eyeDir select 1;

// Cheap safe-guard: if the vectors are degenerate (broken camera state),
// fall back to the unit's own orientation.
if (_fwd isEqualTo [0, 0, 0] || {_up isEqualTo [0, 0, 0]}) then {
    _fwd = vectorDir _unit;
    _up = vectorUp _unit;
};

missionNamespace setVariable [QGVAR(eyeState), [_frame, [_eye, _fwd, _up]]];
[_eye, _fwd, _up]
