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
 * Plus, for effects whose particles must stay glued to the eye (rain
 * droplets on the lens), the eye VELOCITY:
 *
 *   eyeVel  - eye displacement between frames / dt, m/s (world space)
 *
 * A droplet on a lens is stationary in EYE space: its world velocity must
 * cancel the eye's motion.  Computing eyeVel here keeps it consistent for
 * every consumer (one source of truth), instead of each effect deriving
 * its own velocity from stale positions.
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
if (isNull _unit) exitWith { [getPosASLVisual _unit, [0, 0, 1], [0, 1, 0], [0, 0, 0]] };

private _frame = diag_frameNo;
private _cache = missionNamespace getVariable [QGVAR(eyeState), []];
// Cache layout is [_frame, [_eye, _fwd, _up, _eyeVel]] = 2 elements.
// Guard on 2 and matching frame.
if (count _cache >= 2 && {_cache select 0 == _frame}) exitWith {
    _cache select 1
};

private _eye = eyePos _unit;
private _eyeDir = eyeDirection _unit;
// The eye POSITION must also track the camera for freelook-sensitive
// effects (focus fan, blowout cone, rain droplets).  eyePos follows the
// head model, which does NOT move with freelook.  The camera origin
// (positionCameraToWorld [0,0,0]) is where the actual view comes from
// and moves with freelook / vehicle camera.  Use it when it is valid.
private _camOrigin = positionCameraToWorld [0, 0, 0];
if (_camOrigin isNotEqualTo [0, 0, 0]) then {
    _eye = _camOrigin;
};

// Eye velocity: displacement from the PREVIOUS frame's eye position over
// the frame time, world-space m/s.  The first-ever call has no baseline
// (velocity 0).  Stored separately so a slow caller (PFH) still gets a
// stable velocity without racing the per-frame cache.
private _eyeVel = [0, 0, 0];
private _prevEye = missionNamespace getVariable [QGVAR(eyeStatePrev), nil];
private _prevTime = missionNamespace getVariable [QGVAR(eyeStatePrevTime), diag_tickTime];
if (!isNil "_prevEye") then {
    private _dt = diag_tickTime - _prevTime;
    if (_dt > 0.01) then {
        _eyeVel = (_eye vectorDiff _prevEye) vectorMultiply (1 / _dt);
    };
};
// eyeDirection's return shape is ambiguous across engine states: it is
// documented as the eye direction vector, and empirically can come back
// either as a flat 3-vector [x,y,z] (the eye forward) or as a 2-element
// [forward, up].  Handle BOTH; a scalar reaching vectorCrossProduct later
// raises "Type Number, expected Array" (the bug this guards).
private _fwd = vectorDir _unit;
private _up = vectorUp _unit;
if (_eyeDir isEqualType [] && {count _eyeDir == 3}) then {
    // Flat vector form: the whole thing is the eye forward.
    _fwd = _eyeDir;
} else {
    if (_eyeDir isEqualType [] && {count _eyeDir == 2}) then {
        // [forward, up] form.
        private _f = _eyeDir select 0;
        private _u = _eyeDir select 1;
        if (_f isEqualType [] && {count _f == 3}) then { _fwd = _f; };
        if (_u isEqualType [] && {count _u == 3}) then { _up = _u; };
    };
};

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
    // positionCameraToWorld is the canonical freelook-tracked camera:
    // [0,0,0] = the actual camera origin (moves with freelook head-pose
    // and vehicle camera), [0,0,100] = a point 100 m along the camera's
    // view.  The vector between them IS the live view direction.
    // screenToWorldDirection [0.5, 0.5] returns the direction to the
    // screen centre but from a projection that does NOT update during
    // freelook in every render state (Killzone_Kid BIKI note: "if you
    // need centre of screen direction, use positionCameraToWorld").
    private _camPos = positionCameraToWorld [0, 0, 0];
    private _camAim = positionCameraToWorld [0, 0, 100];
    if (_camPos isNotEqualTo [0, 0, 0] && {_camAim isNotEqualTo [0, 0, 0]}) then {
        _fwd = vectorNormalized (_camAim vectorDiff _camPos);
    };
};

// Cheap safe-guard: if the vectors are degenerate (broken camera state),
// fall back to the unit's own orientation.
if !(_fwd isEqualType [] && {count _fwd == 3}) then { _fwd = vectorDir _unit; };
if !(_up isEqualType [] && {count _up == 3}) then { _up = vectorUp _unit; };

// Store this frame's eye + time as the baseline for the NEXT frame's
// velocity, and the 4-element state in the per-frame cache.
missionNamespace setVariable [QGVAR(eyeStatePrev), _eye];
missionNamespace setVariable [QGVAR(eyeStatePrevTime), diag_tickTime];
missionNamespace setVariable [QGVAR(eyeState), [_frame, [_eye, _fwd, _up, _eyeVel]]];
[_eye, _fwd, _up, _eyeVel]
