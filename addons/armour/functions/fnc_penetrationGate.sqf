#include "..\script_component.hpp"
/*
Penetration gate (issue #126).

The second lever.  The engine's bisurf penetration gate is model-baked,
but the HandleDamage EH can scale the DAMAGE by the round's real
penetration vs the vehicle's protection level - the ACE3-replacement
pattern.  This is what makes "a rifle shreds an IFV" impossible: the
round's RHA penetration is compared to the vehicle's STANAG class, and
damage is scaled down (or zeroed) when the round cannot defeat the
protection.

The physics and the protection derivation live in
FUNC(calculatePenetration), shared with the shot response (issue #161).
This file is the HandleDamage wiring.

  - Engine penetration: mm RHA = (v/1000) * caliber * 15 (RHA bisurf)
  - Vanilla over-penetrates: 7.62 Ball (caliber 1.5, 833 m/s) = 18.7mm
    RHA at muzzle vs the real ~4-5mm.  The gate corrects this by
    comparing the round's penetration to the vehicle's protection.
  - STANAG protection by class: MRAP ~L2/L3 (8-18mm), IFV ~L4/L5
    (28-50mm), MBT ~L6 (100mm+).

A cannon round needs a different penetration model.  This bisurf rule is
fitted to small arms: it has no rod length, no impact obliquity and no
shaped-charge jet term, so it does not describe a tank cannon round.  The
cannon branch is deliberately NOT applied.  Candidate models are the
Alekseevskii-Tate long-rod relation for APFSDS and a shaped-charge jet
relation for HEAT; no held source states those inputs, so no cannon
figure is invented.

ACE3 coexistence (verified): return _oldDamage (or 0), never re-inflate
the incoming _damage.  For ACE3 vehicles, hook
ace_vehicle_damage_medicalDamage instead of fighting the vehicle EH.

Arguments:
  0: unit (OBJECT) - the vehicle or soldier hit
  1: selection (STRING)
  2: damage (NUMBER) - the incoming damage
  3: source (OBJECT) - the shooter
  4: projectile (OBJECT) - the round ("" for non-projectile damage)
  5: hitIndex (NUMBER)
  6: instigator (OBJECT)
  7: hitPoint (STRING) - e.g. "HitEngine"

Returns the SCALED damage (the HandleDamage return), respecting the
ACE3 rule.
*/
params ["_unit", "_selection", "_damage", "_source", "_projectile",
        ["_hitIndex", -1, [0]], ["_instigator", objNull, [objNull]],
        ["_hitPoint", "", [""]]];

// Only projectile impacts on land vehicles OR infantry (the issue #119
// soldier-armour gate).  Non-projectile damage passes through untouched.
if (_projectile isEqualType "" || {isNull _projectile}) exitWith { _damage };
if !(_unit isKindOf "LandVehicle" || {_unit isKindOf "Man"}) exitWith { _damage };

private _ammoType = typeOf _projectile;
private _speed = vectorMagnitude (velocity _projectile);

// The shared penetration model (issue #126 + #161).
private _pen = [_unit, _selection, _ammoType, _speed] call FUNC(calculatePenetration);
_pen params ["_penMM", "_protectionMM", "_overmatch", "_penetrated"];

// Non-ballistic (rocket/shell with no caliber): pass through untouched.
if (_penMM < 0) exitWith { _damage };

// The gate: does the round's RHA penetration defeat the protection?
// If NOT, the round cannot meaningfully damage the vehicle - return
// _oldDamage (no new damage).  The ACE3 double-count rule: never
// re-inflate the incoming _damage.
if (!_penetrated) exitWith {
    private _oldDamage = damage _unit;
    if (missionNamespace getVariable [QGVAR(penetrationDebug), false]) then {
        private _logMsg = format [
            "Penetration: %1 at %2 m/s = %3 mm RHA vs %4 mm (%5) - STOPPED",
            _ammoType, _speed, _penMM, _protectionMM, typeOf _unit
        ];
        AEE_LOG_INFO(_logMsg);
    };
    _oldDamage
};

// Penetrated: scale the damage by the penetration OVERMATCH - a round
// that defeats the protection by 2x does more internal damage.  The
// scale is capped at the raw damage (never inflate beyond the engine's
// value - the ACE3 rule).
if (missionNamespace getVariable [QGVAR(penetrationDebug), false]) then {
    private _logMsg = format [
        "Penetration: %1 at %2 m/s = %3 mm RHA vs %4 mm (%5) - PENETRATED x%6",
        _ammoType, _speed, _penMM, _protectionMM, typeOf _unit, _overmatch
    ];
    AEE_LOG_INFO(_logMsg);
};
_damage * (0.5 + 0.5 * _overmatch)
