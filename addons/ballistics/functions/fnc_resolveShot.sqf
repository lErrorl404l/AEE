#include "..\script_component.hpp"
/*
Resolve everything for one fired round (issue #167).

The single entry point for a shot. Every value comes from the verified
database where a source holds it, and from a published physics formula
where no source does. Nothing needs external input: the projections of
data/ballistics are bundled with the mod, and a weapon or a round that
no table knows is still resolved from its own geometry.

  identity          getCartridgeData and getProjectileData
  standard          the drag standard is chosen to match the bullet
                    shape, so the coefficient used is the one the round
                    was measured against
  muzzle velocity   the measured barrel anchors first, the cartridge
                    curve second, the interior-ballistics model last
  stability         the Miller rule from the bullet geometry
  drag              the standard drag tables at the local speed of sound

Arguments:
  0: ammo (STRING, the CfgAmmo classname)
  1: weapon (STRING, the CfgWeapons classname, default "")
  2: barrelM (NUMBER, the measured barrel length, default 0)
  3: tempC (NUMBER, propellant temperature, default 21)
  4: rhoRel (NUMBER, air density relative to ISA sea level, default 1.0)

Returns [mv, bc, dragModel, twistM, stability, retardMs2, cartridgeId,
projectileId, bcGrade, spinRadPerSec]. A zero means the value is not
held. The twist is the weapon's own when the catalogue holds the weapon,
the arm-type standard when the cartridge registers a pistol and a rifle
rate separately, and the cartridge standard otherwise.
*/
params [
    ["_ammo", "", [""]],
    ["_weapon", "", [""]],
    ["_barrelM", 0, [0]],
    ["_tempC", 21, [0]],
    ["_rhoRel", 1.0, [0]]
];
if (_ammo == "") exitWith { [0, 0, "", 0, 0, 0, "", "", ""] };

private _cartridge = [_ammo] call FUNC(getCartridgeData);
private _projectile = [_ammo] call FUNC(getProjectileData);
private _shape = [_ammo] call FUNC(getBulletShape);

private _cartridgeId = if (_cartridge isEqualTo []) then { "" } else { _cartridge select 0 };
private _twist = if (_cartridge isEqualTo []) then { 0 } else { _cartridge select 2 };

// A cartridge that a standards body registers for both a pistol and a
// rifle test barrel carries both rates. The weapon type decides which
// applies, and an unidentified weapon keeps the cartridge default.
if (_weapon != "" && {(count _cartridge) > 6}) then {
    private _twistPistol = _cartridge select 5;
    private _twistRifle = _cartridge select 6;
    private _isHandgun =
        (getNumber (configFile >> "CfgWeapons" >> _weapon >> "type")) == 2;
    if (_isHandgun && _twistPistol > 0) then {
        _twist = _twistPistol;
    };
    if (!_isHandgun && _twistRifle > 0) then {
        _twist = _twistRifle;
    };
};

// The weapon's own barrel, when the catalogue holds it. A weapon that is
// not held keeps the cartridge standard twist, so nothing is unsupported.
// The twist does not add to the cartridge: it replaces it, because the
// rifling rate belongs to the barrel.
private _weaponData = [_weapon] call FUNC(getWeaponData);
if ((_weaponData isNotEqualTo []) && {(_weaponData select 1) > 0}) then {
    _twist = _weaponData select 1;
};
private _pressure = if (_cartridge isEqualTo []) then { 0 } else { _cartridge select 3 };

private _projectileId = if (_projectile isEqualTo []) then { "" } else { _projectile select 0 };
private _massG = if (_projectile isEqualTo []) then { 0 } else { _projectile select 1 };
private _calibreMm = if (_projectile isEqualTo []) then { 0 } else { _projectile select 2 };
private _lengthMm = if (_projectile isEqualTo []) then { 0 } else { _projectile select 4 };
private _coefficients = if (_projectile isEqualTo []) then { [] } else { _projectile select 3 };

// ─── The drag standard and the coefficient ───────────────────────────────
// The standard follows the bullet shape: a flat base bullet is
// described by G1, a boat tail by G7, which is the standard each was
// measured against. Where a source holds no coefficient at all, one is
// calculated from the shape.
// getBulletShape returns [shapeClass, formFactor, modelCode]. The class
// is the standard NAME, which is what the coefficient keys use; the
// modelCode is the numeric form of the same standard.
private _preferred = if ((count _shape) >= 3) then { _shape select 0 } else { "" };
private _formFactor = if ((count _shape) >= 3) then { _shape select 1 } else { 1.0 };
private _bc = 0;
private _model = _preferred;
private _bcGrade = "";
{
    _x params ["_candidate", "_value", "_grade"];
    if (_candidate == _preferred) exitWith {
        _bc = _value;
        _model = _candidate;
        _bcGrade = _grade;
    };
} forEach _coefficients;
if (_bc <= 0 && {_coefficients isNotEqualTo []}) then {
    (_coefficients select 0) params ["_candidate", "_value", "_grade"];
    _bc = _value;
    _model = _candidate;
    _bcGrade = _grade;
};
if (_bc <= 0 && _massG > 0 && _calibreMm > 0) then {
    _bc = [_massG, _calibreMm, _formFactor, (_model == "G7")]
        call FUNC(calculateBallisticCoefficient);
    _bcGrade = "derived";
};

// ─── The muzzle velocity ─────────────────────────────────────────────────
private _mv = ([_ammo, _barrelM, _tempC] call FUNC(deriveCartridge)) select 0;
if (_mv <= 0 && _calibreMm > 0 && _massG > 0) then {
    _mv = [_calibreMm, _massG, _barrelM, _pressure] call FUNC(calculateInteriorBallistics);
};

// A cannon or autocannon has no interior-ballistics curve here: the
// small-arms model above is fitted to cartridge barrels and gives 0 at
// and above 20 mm. The sourced service velocity in the load record is
// then the value, because a found value beats a formula (ADR-003). The
// lookup is a class-name table with a cache, so the shot path stays flat.
private _cartridgeCalibre = if (_cartridge isEqualTo []) then { 0 } else { _cartridge select 1 };
if (_mv <= 0 && _cartridgeCalibre >= 20) then {
    private _load = [_ammo] call FUNC(getLoadData);
    if (_load isNotEqualTo []) then {
        _mv = _load select 2;
    };
};

// ─── Stability and the drag at the muzzle ────────────────────────────────
// The stability path follows the projectile. A rifled round uses the Miller
// spin rule. A fin-stabilised round (a smoothbore sets the twist to 0) uses
// the FIN_STABILISED sentinel from the same function, so neither path breaks
// when the twist is 0.
private _stability = 0;
if (_lengthMm > 0 && _massG > 0 && _calibreMm > 0) then {
    _stability = [_lengthMm / 1000, _massG, _calibreMm / 1000, _twist, _mv, 0]
        call FUNC(calculateStability);
};

private _retard = 0;
if (_bc > 0 && _mv > 0) then {
    _retard = [_bc, _mv, _model, _rhoRel, _tempC] call FUNC(calculateBallisticDrag);
};

// The spin rate follows from the twist and the velocity:
// omega = 2 pi v / T (rad/s). It is what the stability depends on.
private _spinRate = if (_twist > 0 && _mv > 0) then { 2 * pi * _mv / _twist } else { 0 };

// The resolved shot, in one line: the identity it matched and the values
// the model derived from it. A miss shows as an empty cartridge, which is
// the case a wrong trajectory is hardest to explain without this.
private _logMsg = format [
    "shot %1/%2: mv %3 m/s, bc %4 (%5), twist %6 m/turn, stability %7, retard %8 m/s2, barrel %9 m",
    _cartridgeId, _projectileId, round _mv, _bc, _model, _twist, _stability, round _retard, round (_barrelM * 1000) / 1000
];
AEE_LOG_DEBUG(_logMsg);

[
    _mv,
    _bc,
    _model,
    _twist,
    _stability,
    _retard,
    _cartridgeId,
    _projectileId,
    _bcGrade,
    _spinRate
]
