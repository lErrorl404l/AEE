#include "..\..\script_component.hpp"
/*
Carried magazine mass (the load-carriage library).

A magazine is the heaviest repeated item a soldier carries, so it drives
the load. The empty mass comes from the generated resolver
(fnc_getMagazineMass), which projects the maker-published masses for 76
magazines. The cartridges add their own mass: the round mass tier below
is the published loaded-round mass for the chambering, from the same
research set (TM 43-0001-27 and the maker manuals).

Argument:
  0: unit (OBJECT, default player)

Returns the carried magazine mass in kg.
*/

params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { 0 };

// [chambering token, loaded round mass g] — the published round mass.
private _roundTiers = [
    ["556x45", 12.3],
    ["762x51", 25.4],
    ["762x39", 16.4],
    ["545x39", 10.8],
    ["762x54", 21.8],
    ["9x19", 11.6],
    ["45acp", 21.4],
    ["40sw", 13.0],
    ["50bmg", 114.0],
    ["46x30", 6.0],
    ["57x28", 6.0],
    ["338", 26.0],
    ["300", 12.5]
];

private _total = 0;
{
    _x params ["_magazine", "_ammo", "_count", "_loaded"];
    if (_magazine != "") then {
        private _empty = [_magazine] call FUNC(getMagazineMass);
        private _lower = toLower _magazine;
        private _round = 12.0;
        {
            if (_lower find (_x select 0) >= 0) exitWith {
                _round = _x select 1;
            };
        } forEach _roundTiers;
        _total = _total + _empty + (_count max 0) * _round / 1000;
    };
} forEach (magazinesAmmoFull _unit);

_total
