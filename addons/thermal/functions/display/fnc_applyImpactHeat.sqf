#include "..\..\script_component.hpp"
/*
 * Projectile impact residual heat (issue #204).
 *
 * A bullet hole carries residual heat from the projectile: the round
 * arrives hot (friction + the muzzle-heated barrel it passed through)
 * and transfers that heat into the surface it strikes.  On metal or
 * masonry a hole is a warm spot for a while; on dry wood it can smoulder.
 *
 * The HitPart event fires on the IMPACTED object with the projectile;
 * its position at impact IS the bullet hole.  A short-lived warm ground
 * stamp is laid there, scaled by the round's energy (the ammo's
 * hit/indirectHit - heavier rounds carry more energy) and the surface.
 *
 * This is a SCRIPTED hit EH (the engine's HitPart is per-object; we
 * install one on the player's environment objects via the tick, or
 * react to the global "hitPart" via a server-side listener).  The
 * engine broadcasts hitPart; we listen with addEventHandler on the
 * relevant objects and stamp at the impact.
 *
 * Params:
 *   0: _projectile (OBJECT)
 *   1: _ammo (STRING) - the round's config class
 *
 * Returns: SCALAR - 1 if a stamp was laid.
 */
params ["_projectile", ["_ammo", ""]];

if (isNull _projectile) exitWith { 0 };

// The impact point: the projectile's position (it stops there or
// passes through - the hole is at the intersection).
private _pos = getPosASL _projectile;
if (count _pos < 3) exitWith { 0 };

// Round energy: CfgAmmo hit (kinetic) - a proxy for how much heat the
// impact deposits.  Heavy AP/explosive rounds deposit more.
private _hit = getNumber (configFile >> "CfgAmmo" >> _ammo >> "hit");
if (_hit <= 0) then { _hit = 5; };   // small-arms default
private _energy = _hit min 100;

// Residual heat: the round's own temperature (it was in a hot barrel)
// + the kinetic conversion at impact.  Scale modestly - a bullet hole
// is a small warm patch, not a fire.
private _offset = (2.0 + (_energy / 20)) min 8;   // +2..8 C
[_pos, _offset, 45] call FUNC(addGroundStamp);

// The impacted OBJECT (if the projectile stopped on it) gets a short
// radiative kick on the surface nearest the impact.
private _near = _pos nearObjects 2;
if (_near isNotEqualTo []) then {
    private _obj = _near select 0;
    if !(_obj isKindOf "Man") then {
        private _sels = [_obj] call FUNC(getThermalSelections);
        if (count _sels > 0) then {
            private _names = selectionNames _obj;
            private _sel = _sels select 0;
            if (_sel < count _names) then {
                private _flux = _offset * 120;
                [_obj, (_names select _sel), "", _flux, 0.5] call FUNC(applySelectionThermal);
            };
        };
    };
};

1
