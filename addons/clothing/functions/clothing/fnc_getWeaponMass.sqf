#include "..\..\script_component.hpp"
/*
Weapon mass (the load-carriage library).

The equipment library covers the uniform, the vest, the helmet, the
goggles and the pack. Weapons were absent, so the heaviest single item a
soldier carries was left out of the stamina load.

The researched mass comes from the weapon catalogue in the ballistics
addon, which holds the maker's published figure (mass_kg) for every
weapon it identifies. That call is guarded, so physiology works without
ballistics, and the fallback classifies the classname by family keyword
in the manner of the clothing library.

Argument:
  0: weapon (STRING, a CfgWeapons classname, default "")

Returns the mass in kg. A zero means the classname carries no signal.
*/

params [["_weapon", "", [""]]];
if (_weapon == "") exitWith { 0 };

// The researched value, when the ballistics catalogue holds the weapon.
// The result is collected first: an exitWith inside a then block leaves
// only that block, not the function.
private _researched = 0;
if (!isNil "aee_ballistics_fnc_getWeaponData") then {
    private _data = [_weapon] call aee_ballistics_fnc_getWeaponData;
    if ((_data isNotEqualTo []) && {(_data select 4) > 0}) then {
        _researched = _data select 4;
    };
};
if (_researched > 0) exitWith { _researched };

// The family fallback, when the catalogue does not hold the weapon.  The
// table is GENERATED from the corpus (fnc_weaponMassFallback.sqf): every
// figure in it is the median of the published masses the weapon catalogue
// holds for that family, so nothing here is invented.  The order matters:
// the most specific family first, so a classname holding "lmg" is not read
// as a rifle.
private _class = toLower _weapon;
([] call FUNC(weaponMassFallback)) params ["_tiers", "_default"];

private _mass = _default;
{
    if (_class find (_x select 0) >= 0) exitWith { _mass = _x select 1; };
} forEach _tiers;

_mass
