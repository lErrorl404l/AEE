#include "..\..\script_component.hpp"
/*
Carried weapon mass (the load-carriage library).

Sums the mass of the weapons the soldier carries: the primary weapon, the
launcher and the handgun. The equipment library then adds this to the
combined load, which the stamina model consumes.

Magazines are not counted yet, and they are the heaviest part of a
combat load. Their capture is a separate dataset.

Argument:
  0: unit (OBJECT, default player)

Returns the carried weapon mass in kg.
*/

params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { 0 };

private _total = 0;
{
    if (_x != "") then {
        _total = _total + ([_x] call FUNC(getWeaponMass));
    };
} forEach [primaryWeapon _unit, secondaryWeapon _unit, handgunWeapon _unit];

_total
