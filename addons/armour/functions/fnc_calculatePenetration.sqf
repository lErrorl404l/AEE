#include "..\script_component.hpp"
/*
Penetration vs protection (issue #126, extracted for reuse by the shot
response of issue #161).

The single penetration model.  FUNC(penetrationGate) wires this into the
HandleDamage event; FUNC(applyShotResponse) in aee_blast reads the same
result for the incapacitation threshold.  One model, two consumers.

The physics (research-verified, the engine bisurf reference):
  - Engine penetration: mm RHA = (v/1000) * caliber * 15
  - The round's RHA penetration is compared to the target's protection:
      * a soldier faces the vest (torso) or helmet (head/neck) NIJ level
        from the equipment library (issue #119): ESAPI plates (NIJ III)
        20 mm, IIIA soft 10 mm, IIA soft 6 mm, no armour 3 mm (soft tissue)
      * a vehicle faces its derived STANAG protection (issue #170)
  - A round with no caliber (rocket, shell) is non-ballistic: penMM < 0.

Input:  [_unit, _selection, _ammoType, _speed_mps]
Output: [penMM, protectionMM, overmatch, penetrated]
        penMM < 0 signals a non-ballistic round (caller passes it through).
*/
params [
    ["_unit", objNull, [objNull]],
    ["_selection", "", [""]],
    ["_ammoType", "", [""]],
    ["_speed", 0, [0]]
];

if (isNull _unit || (_ammoType == "")) exitWith { [-1, 0, 0, false] };

private _caliber = getNumber (configFile >> "CfgAmmo" >> _ammoType >> "caliber");
if (_caliber <= 0) exitWith { [-1, 0, 0, false] };

// Engine penetration vs RHA (the bisurf reference, bulletPenetrability 15).
private _penMM = ((_speed / 1000) * _caliber * 15) max 0;

// The protection the round must defeat.
private _protectionMM = if (_unit isKindOf "Man") then {
    // The per-slot equipment library (issue #119): the protection
    // depends on WHERE the round hits.  The library returns
    // [uniform, vest, helmet, goggle, pack, combined] - each entry
    // [weight, armor NIJ 0..3, nir, clo].
    private _equip = [_unit] call EFUNC(clothing,getEquipmentProperties);
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
    // The dynamic protection derivation (issue #170).
    ([_unit] call FUNC(deriveProtection)) select 1
};

private _penetrated = _penMM >= _protectionMM;
private _overmatch = if (_protectionMM > 0) then {
    (_penMM / _protectionMM) min 1.0
} else {
    1.0
};

[_penMM, _protectionMM, _overmatch, _penetrated]
