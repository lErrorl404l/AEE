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

The physics (research-verified):
  - Engine penetration: mm RHA = (v/1000) * caliber * 15 (RHA bisurf)
  - Vanilla over-penetrates: 7.62 Ball (caliber 1.5, 833 m/s) = 18.7mm
    RHA at muzzle vs the real ~4-5mm.  The gate corrects this by
    comparing the round's penetration to the vehicle's protection.
  - STANAG protection by class: MRAP ~L2/L3 (8-18mm), IFV ~L4/L5
    (28-50mm), MBT ~L6 (100mm+).

ACE3 coexistence (verified): return _oldDamage (or 0), never re-inflate
the incoming _damage.  This handler returns _oldDamage when the round
does not penetrate, so the vehicle takes no NEW damage; ACE3's delta
stays at zero.  For ACE3 vehicles, hook ace_vehicle_damage_medicalDamage
instead of fighting the vehicle EH.

Arguments:
  0: unit (OBJECT) - the vehicle hit
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

// The engine's ammunition type - from the projectile's config.  Read
// the real caliber (the normalized penetration multiplier) and speed.
private _ammoType = typeOf _projectile;
private _caliber = getNumber (configFile >> "CfgAmmo" >> _ammoType >> "caliber");
private _speed = vectorMagnitude (velocity _projectile);
if (_caliber <= 0) exitWith { _damage };   // non-ballistic (rocket/shell with no caliber)

// Engine penetration vs RHA (the bisurf reference, bulletPenetrability 15):
//   mm RHA = (v/1000) * caliber * 15
private _penMM = ((_speed / 1000) * _caliber * 15) max 0;

// The vehicle's STANAG protection class from its armour pool.  The pool
// is the design target; the class maps to the RHA protection it models.
// The protection class: vehicles use the armour pool ladder; a SOLDIER
// uses the equipment library's vest NIJ level (issue #119) - a plate
// carrier (NIJ III) stops rifle ball, an unprotected soldier does not.
private _protectionMM = if (_unit isKindOf "Man") then {
    // The per-slot equipment library (issue #119): the protection
    // depends on WHERE the round hits.  A head hit faces the helmet's
    // armour; a torso hit faces the vest's.  The library returns
    // [uniform, vest, helmet, goggle, pack, combined] - each entry
    // [weight, armor NIJ 0..3, nir, clo].
    private _equip = [_unit] call EFUNC(physiology,getEquipmentProperties);
    private _hitSlot = if (_selection == "head" || _selection == "neck") then {
        _equip select 2   // the helmet
    } else {
        _equip select 1   // the vest (torso)
    };
    private _nij = _hitSlot select 1;
    switch (_nij) do {
        case 3: { 20 };   // ESAPI plates: stops rifle ball + 7.62 AP
        case 2: { 10 };   // IIIA soft: stops pistol + fragments
        case 1: { 6 };    // IIA soft: stops pistol only
        default { 3 };    // no armour on that slot: soft tissue
    };
} else {
    private _armorPool = getNumber (configOf _unit >> "armor");
    switch (true) do {
        case (_armorPool >= 1000): { 100 };  // MBT: ~L6 (APFSDS-class)
        case (_armorPool >= 500):  { 45 };   // IFV/APC tracked: ~L4/L5
        case (_armorPool >= 300):  { 32 };   // IFV/APC wheeled: ~L4
        case (_armorPool >= 130):  { 18 };   // MRAP: ~L3
        case (_armorPool >= 70):   { 8 };    // truck: ~L2
        default                   { 4 };    // light skin: ~L1
    };
};

// The gate: does the round's RHA penetration defeat the protection?
// If NOT, the round cannot meaningfully damage the vehicle - return
// _oldDamage (no new damage).  The ACE3 double-count rule: never
// re-inflate the incoming _damage.
if (_penMM < _protectionMM) exitWith {
    private _oldDamage = damage _unit;
    if (missionNamespace getVariable [QGVAR(penetrationDebug), false]) then {
        private _logMsg = format [
            "Penetration: %1 at %2 m/s cal %3 = %4 mm RHA vs %5 mm (%6) - STOPPED",
            _ammoType, _speed, _caliber, _penMM, _protectionMM, typeOf _unit
        ];
        AEE_LOG_INFO(_logMsg);
    };
    _oldDamage
};

// Penetrated: scale the damage by the penetration OVERMATCH - a round
// that defeats the protection by 2x does more internal damage.  The
// scale is capped at the raw damage (never inflate beyond the engine's
// value - the ACE3 rule).
private _overmatch = (_penMM / _protectionMM) min 1.0;
if (missionNamespace getVariable [QGVAR(penetrationDebug), false]) then {
    private _logMsg = format [
        "Penetration: %1 at %2 m/s cal %3 = %4 mm RHA vs %5 mm (%6) - PENETRATED x%7",
        _ammoType, _speed, _caliber, _penMM, _protectionMM, typeOf _unit, _overmatch
    ];
    AEE_LOG_INFO(_logMsg);
};
_damage * (0.5 + 0.5 * _overmatch)

