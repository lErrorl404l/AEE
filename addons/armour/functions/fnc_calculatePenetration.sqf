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
        from the equipment library (issue #119): the incoming bullet's
        impact energy density against that level's NIJ 0101.06
        certification rounds (see the soldier branch below)
      * a vehicle faces its derived STANAG protection (issue #170)
  - A round with no caliber (rocket, shell) is non-ballistic: penMM < 0.

Input:  [_unit, _selection, _ammoType, _speed_mps]
Output: [penMM, protectionMM, overmatch, penetrated]
        A vehicle hit compares mm RHA; a soldier hit compares impact energy
        density, J/mm^2 (both fields in the same unit, so the overmatch
        ratio and the flag mean the same thing to every consumer).
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
// The vehicle branch compares in mm RHA against the STANAG protection.
private _penMM = ((_speed / 1000) * _caliber * 15) max 0;

// ─── Soldier: real projectile against the NIJ certification threats ───────
// A body-armour level is defined by the rounds it is certified to stop
// (NIJ Standard-0101.06, Table 2 and 4: bullet, mass, reference velocity).
// The soldier branch compares the incoming round's IMPACT ENERGY DENSITY,
// E / A = (m v^2 / 2) / (pi d^2 / 4) in J/mm^2, from the real bullet in the
// ballistics corpus (aee_ballistics_fnc_getProjectileData: mass, diameter),
// with the highest energy density among that level's certification rounds.
// Energy per presented area is the projectile term of the armour
// penetration scaling (Cunniff 1999, 18th Int. Symp. Ballistics: V50 is a
// function of A_d*A_p/m_p), so a vest stops what its certification rounds
// bracket and a denser or faster round defeats it.  It does not separate
// core hardness (a steel-core M855 against a polyethylene III plate), which
// needs a construction-specific V50 the corpus does not hold.
//
//   level   certification rounds (mass g, diameter mm, velocity m/s)
//   III     7.62x51 M80 FMJ (9.6, 7.82, 847)                    71.7 J/mm2
//   IIIA    .357 SIG FMJ FN (8.1, 9.02, 448); .44 Mag SJHP (15.6, 10.9, 436)
//   IIA     9 mm FMJ RN (8.0, 9.02, 373); .40 S&W FMJ (11.7, 10.16, 352)
//
// A round the corpus does not hold falls back to the engine formula on
// both sides (the certification round's CfgAmmo caliber), the same metric
// the vehicle branch uses.
private _protectionMM = 0;
if (_unit isKindOf "Man") then {
    // The per-slot equipment library (issue #119): [uniform, vest, helmet,
    // goggle, pack, combined], each [weight, armor NIJ 0..3, nir, clo].
    private _equip = [_unit] call EFUNC(clothing,getEquipmentProperties);
    private _hitSlot = if (_selection == "head" || _selection == "neck") then {
        _equip select 2   // the helmet
    } else {
        _equip select 1   // the vest (torso)
    };
    private _nij = _hitSlot select 1;
    // [mass g, diameter mm, velocity m/s, engine proxy ammo]
    private _threats = switch (_nij) do {
        case 3: { [[9.6, 7.82, 847, "B_762x51_Ball"]] };
        case 2: { [[8.1, 9.02, 448, "B_9x21_Ball"], [15.6, 10.9, 436, ""]] };
        case 1: { [[8.0, 9.02, 373, "B_9x21_Ball"], [11.7, 10.16, 352, ""]] };
        default { [] };
    };
    private _fnc_density = {
        params ["_massG", "_diaMM", "_v"];
        (0.5 * (_massG / 1000) * _v * _v) / (pi * _diaMM * _diaMM / 4)
    };
    private _proj = [_ammoType] call EFUNC(ballistics,getProjectileData);
    if (_threats isEqualTo []) then {
        // No armour on that slot: soft tissue, the engine-metric floor.
        _protectionMM = 3;
    } else {
        if ((_proj isNotEqualTo []) && {(_proj select 1) > 0} && {(_proj select 2) > 0}) then {
            _penMM = [_proj select 1, _proj select 2, _speed] call _fnc_density;
            {
                _protectionMM = _protectionMM max ([_x select 0, _x select 1, _x select 2] call _fnc_density);
            } forEach _threats;
        } else {
            {
                _x params ["", "", "_tv", "_tAmmo"];
                if (_tAmmo != "") then {
                    private _tCal = getNumber (configFile >> "CfgAmmo" >> _tAmmo >> "caliber");
                    if (_tCal > 0) then {
                        _protectionMM = _protectionMM max ((_tv / 1000) * _tCal * 15);
                    };
                };
            } forEach _threats;
        };
    };
} else {
    // The dynamic protection derivation (issue #170).
    _protectionMM = ([_unit] call FUNC(deriveProtection)) select 1;
};
private _penetrated = _penMM >= _protectionMM;
private _overmatch = if (_protectionMM > 0) then {
    (_penMM / _protectionMM) min 1.0
} else {
    1.0
};

[_penMM, _protectionMM, _overmatch, _penetrated]
