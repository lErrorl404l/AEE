#include "..\script_component.hpp"
// Stamps residual heat into a surface at the point a round lands.
//
// A raw BIS "HitPart" fires on the PROJECTILE, not on a man, so no
// CfgVehicles class can carry it. It is therefore attached per projectile
// from the shooter's own "Fired" event, which is the same shape the material
// addon already uses, rather than from a class event handler.
//
// THE AMMO IS FOUND BY SCANNING, NOT BY POSITION. A first version named five
// parameters, so _ammo bound _this select 4, an ARRAY, and the consumer ran
// configFile >> "CfgAmmo" >> _ammo, which the engine rejected with
// "Type Array, expected String" 47 times in the 2026-09-29 in-game RPT. The
// obvious repair, naming the documented nine arguments, still depends on the
// argument order being exactly as documented, and a dedicated server cannot
// fire a round to prove the order. So the ammo is identified by what it IS:
// the first argument that is a string naming a CfgAmmo class. That is order
// independent, and a miss leaves _ammo empty so the consumer skips rather than
// throws.
// _this is already the event array, so there is nothing to destructure.
// Naming it in a params line would reassign a reserved variable.
if (!(_this isEqualType "ARRAY")) exitWith {};
if ((count _this) < 3) exitWith {};

private _projectile = objNull;
private _ammo = "";
{
    if ((_ammo isEqualTo "") && (_x isEqualType "")) then {
        if (getText (configFile >> "CfgAmmo" >> _x >> "weapon") != "") then { _ammo = _x };
    };
    if ((_projectile isEqualTo objNull) && (_x isEqualType "OBJECT")) then {
        _projectile = _x;
    };
} forEach _this;

if (isNull _projectile) exitWith {};
// The thermal field is local, so a distant impact costs nothing to skip.
if ((getPosASL _projectile) distance (getPosASL (call CBA_fnc_currentUnit)) > 150) exitWith {};

[_projectile, _ammo] call FUNC(applyImpactHeat);
