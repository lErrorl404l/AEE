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
 * uses in first person.  The LOOK vector is state-aware, matching
 * KtweaK's NVG (fn_sampleLighting): in a turret the optics align to the
 * weapon (weaponDirection), on foot to the view centre
 * (screenToWorldDirection [0.5, 0.5]).  getCameraViewDirection tracks the
 * head, which is wrong for a weapon-aligned optic.
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

// ─── State-aware forward vector ───────────────────────────────────────────
// The eye POSITION is always eyePos, but the correct LOOK vector depends
// on the player state.  Verified against KtweaK's NVG (fn_sampleLighting),
// the closest shipping analogue to our eye-space systems:
//   - In a turret: the optics align to the WEAPON, not the head.  Use the
//     turret's weaponDirection (the gunner's aim).
//   - On foot / passenger: use the camera view centre, which is the true
//     look vector (screenToWorldDirection [0.5, 0.5] = the crosshair).
// getCameraViewDirection is close on foot but tracks the head in a
// turret, which is wrong for a weapon-aligned optic.
private _veh = vehicle _unit;
private _inTurret = (_veh isNotEqualTo _unit)
    && {count (allTurrets [_veh, false]) > 0}
    && {(_veh turretUnit [0]) isEqualTo _unit};

if (_inTurret) then {
    private _weaponDir = _veh weaponDirection (currentWeapon _veh);
    if (_weaponDir isNotEqualTo [0, 0, 0]) then { _fwd = vectorNormalized _weaponDir; };
} else {
    // screenToWorldDirection [0.5, 0.5] = the exact centre of the view.
    private _screenDir = screenToWorldDirection [0.5, 0.5];
    if (_screenDir isNotEqualTo [0, 0, 0]) then { _fwd = _screenDir; };
};

// Cheap safe-guard: if the vectors are degenerate (broken camera state),
// fall back to the unit's own orientation.
if (_fwd isEqualTo [0, 0, 0] || {_up isEqualTo [0, 0, 0]}) then {
    _fwd = vectorDir _unit;
    _up = vectorUp _unit;
};

missionNamespace setVariable [QGVAR(eyeState), [_frame, [_eye, _fwd, _up]]];
[_eye, _fwd, _up]
