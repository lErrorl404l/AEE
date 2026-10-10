#include "..\script_component.hpp"
/*
Shot response (issue #161): the reaction to a ballistic hit.

When a direct hit penetrates the soldier's protection and strikes a vital
region, the soldier is incapacitated at once and the fall is biased along
the round's momentum.

  - Penetration: the #126 model, reused through FUNC(calculatePenetration) -
    a round that does not defeat the protection (a graze, or a
    plate-carrier stop) does not drop the soldier.
  - Incapacitation: setUnconscious - the scripted "dropped" state
    (verified: it puts the unit in the engine ragdoll).  The same state
    the physiology sleep tracker already reads as sleep.
  - Momentum: p = m * v, and the velocity change on the body is
    dv = p / m_body.  The round's mass comes from the held ballistics
    database (EFUNC(ballistics,getProjectileData)); a 7.62x51 M80 is
    9.66 g, so dv on an 80 kg body is ~0.1 m/s.  The bias is small on
    purpose: it is the real momentum transfer, not a game knock-down.

CEILING.  The entity HitPart event runs on the SHOOTER's PC (Arma 3
wiki), so this runs there; setUnconscious has a global effect.  MP
locality is a documented ceiling.

Input:  the entity HitPart argument array
        [target, shooter, projectile, position, velocity, selection,
         ammo, vector, radius, surface, direct, instigator]
Output: BOOL - true when the soldier was incapacitated
*/
params [
    ["_target", objNull, [objNull]],
    ["_shooter", objNull, [objNull]],
    ["_projectile", objNull, [objNull, ""]],
    ["_position", [0, 0, 0], [[]]],
    ["_velocity", [0, 0, 0], [[]]],
    ["_selection", [], [[]]],
    ["_ammo", [], [[]]],
    ["_vector", [0, 0, 0], [[]]],
    ["_radius", 0, [0]],
    ["_surface", "", [""]],
    ["_direct", false, [false]],
    ["_instigator", objNull, [objNull]]
];

if (!_direct) exitWith { false };
if (isNull _target || {!alive _target}) exitWith { false };

private _ammoClass = _ammo param [4, ""];
if !(_ammoClass isEqualType "") exitWith { false };

// A vital region only: a limb or a graze does not incapacitate.
private _vital = ["head", "face", "neck", "torso", "chest", "spine",
    "spine1", "spine2", "spine3", "pelvis", "body"];
private _hitVital = false;
{
    if ((toLower _x) in _vital) exitWith { _hitVital = true; };
} forEach _selection;
if (!_hitVital) exitWith { false };

// The #126 penetration model, reused.
private _speed = vectorMagnitude _velocity;
private _sel = _selection param [0, ""];
private _pen = [_target, _sel, _ammoClass, _speed] call FUNC(calculatePenetration);
_pen params ["_penMM", "_protectionMM", "_overmatch", "_penetrated"];
if (!_penetrated) exitWith { false };

// Incapacitate at once.
_target setUnconscious true;

// Bias the fall along the round's momentum (p = m * v).
private _pdata = [_ammoClass] call EFUNC(ballistics,getProjectileData);
private _massKg = if (_pdata isEqualType [] && {(count _pdata) > 1}) then {
    (_pdata select 1) / 1000
} else {
    0
};
if (_massKg > 0 && (_speed > 0)) then {
    private _bodyMass = [_target] call EFUNC(clothing,getCorpseMass);
    private _dv = (_massKg * _speed) / _bodyMass;
    _target setVelocity ((velocity _target) vectorAdd ((vectorNormalized _velocity) vectorMultiply _dv));
};

true
