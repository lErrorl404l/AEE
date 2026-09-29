#include "..\script_component.hpp"
// Stamps residual heat into a surface at the point a round lands.
//
// A raw BIS "HitPart" fires on the PROJECTILE, not on a man, so no
// CfgVehicles class can carry it. It is therefore attached per projectile
// from the shooter's own "Fired" event, which is the same shape the material
// addon already uses, rather than from a class event handler.
params ["_projectile", "_shooter", "_instigator", "_selection", "_ammo"];

if (isNil "_projectile" || {isNull _projectile}) exitWith {};
if (isNil "_ammo") then { _ammo = ""; };
// The thermal field is local, so a distant impact costs nothing to skip.
if ((getPosASL _projectile) distance (getPosASL (call CBA_fnc_currentUnit)) > 150) exitWith {};

[_projectile, _ammo] call FUNC(applyImpactHeat);
