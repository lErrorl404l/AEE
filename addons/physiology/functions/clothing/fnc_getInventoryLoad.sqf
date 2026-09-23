#include "..\..\script_component.hpp"
/*
Carried inventory mass (the load-carriage library).

The equipment library weighs the worn slots (uniform, vest, headgear,
goggles, backpack). This function weighs what the soldier CARRIES: the
container contents, the assigned slot items (map, compass, watch, GPS,
radio, NVG, binocular) and the weapon attachments (optic, laser,
suppressor, bipod).

The worn slots, the carried weapons and the magazines are already counted
by fnc_getUniformProperties and its siblings, fnc_getWeaponLoad and
fnc_getMagazineLoad. This walk skips all three, so no item is counted
twice.

The engine commands give each classname once per instance:
- items - the contents of every container (uniform, vest, backpack). By
  the engine rule it holds no magazines, no assigned items and no carried
  weapons.
- assignedItems - the slot items, one per slot, no headgear or goggles.
- hmd and binocular - the head-mounted device and the binocular, added
  only when the engine does not report them as assigned.
- weaponCargo - the weapons stowed in the backpack.

An unknown item resolves to 0 (fnc_getItemMass): it is unknown, not
guessed, and the coverage test reports it.

Argument:
  0: unit (OBJECT, default player)

Returns the carried inventory mass in kg.
*/

params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { 0 };

private _worn = [
    uniform _unit, vest _unit, headgear _unit, goggles _unit, backpack _unit
];
private _held = [
    primaryWeapon _unit, secondaryWeapon _unit, handgunWeapon _unit
];

private _total = 0;

// An item the core table does not hold may be held by an optional layer:
// ACE's own kit carries published masses for items the core cannot know.
// Core asks whether a fallback resolver is registered and never names the
// layer, so the dependency stays one-way.
private _resolvers = missionNamespace getVariable [QGVAR(massResolvers), []];
private _resolve = {
    params ["_item", ["_category", "", [""]]];
    private _mass = [_item, _category] call FUNC(getItemMass);
    if (_mass <= 0) then {
        {
            _mass = [_item] call _x;
            if (_mass > 0) exitWith {};
        } forEach _resolvers;
    };
    _mass
};

// The container contents: one entry per instance, so each is counted.
// The category is the kind the walk knows: the items loop carries the
// general carried kit, so an optional classifier may identify a medical
// item and a family of another kind may not claim it.
{
    if (_x != ""
        && {!(_x in _worn)}
        && {!(_x in _held)}
        && {!isClass (configFile >> "CfgMagazines" >> _x)}) then {
        _total = _total + ([_x, "medical"] call _resolve);
    };
} forEach (items _unit);

// The assigned slot items, one per slot. `hmd` returns one classname (an
// empty string when the slot is empty) and `binocular` one classname. Both
// join when the engine does not report them as assigned; the membership
// check holds a duplicate back.
private _assigned = +assignedItems _unit;
private _hmd = hmd _unit;
if (_hmd != "" && {!(_hmd in _assigned)}) then { _assigned pushBack _hmd; };
private _binocular = binocular _unit;
if (_binocular != "" && {!(_binocular in _assigned)}) then {
    _assigned pushBack _binocular;
};
{
    if (_x != ""
        && {!(_x in _worn)}
        && {!(_x in _held)}) then {
        _total = _total + ([_x] call _resolve);
    };
} forEach _assigned;

// The weapon attachments: one entry per weapon and slot.
{
    {
        if (_x != "") then {
            _total = _total + ([_x] call _resolve);
        };
    } forEach _x;
} forEach [
    primaryWeaponItems _unit, secondaryWeaponItems _unit, handgunItems _unit
];

// The weapons stowed in the backpack take the weapon resolver.
{
    if (_x != "") then {
        _total = _total + ([_x] call FUNC(getWeaponMass));
    };
} forEach (weaponCargo (unitBackpack _unit));

_total
