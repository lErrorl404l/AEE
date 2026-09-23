#include "..\script_component.hpp"

/*
ACE item mass (the ACE-bodied items).

The core equipment library holds only real published masses, and it stays
free of ACE conventions.  ACE's own medical and support items are a case
the core cannot know: their classnames carry no engine item category, so
the core resolver returns 0 for them and the item contributes nothing to
the carried load.  This compat function supplies them.

The values are ACE's published config masses.  They are a real mass, not
the engine's slot-space value: ACE states them in units of 100 g, and that
scale was checked against documented item masses.  Saline IV at 10 units
is a 1.0 kg bag, a body bag at 7 is 0.7 kg, a surgical kit at 15 is
1.5 kg, a suture at 0.1 is 10 g.  Five items land on 0.100 kg per unit
and the two that do not are values ACE rounded to one decimal, so the
scale is verified and a conversion is defensible.

Argument:
  0: item (STRING, an ACE classname, default "")

Returns the ACE-published mass in kg, or 0 when the item is not held.
*/

params [["_item", "", [""]]];
if (_item == "") exitWith { 0 };

// [ACE classname, config mass unit] - the unit is 100 g, so the mass is
// unit / 10 kg.
private _TABLE = [
    ["ACE_fieldDressing", 0.6],
    ["ACE_packingBandage", 0.6],
    ["ACE_elasticBandage", 0.6],
    ["ACE_quikclot", 0.6],
    ["ACE_tourniquet", 1.0],
    ["ACE_morphine", 1.0],
    ["ACE_adenosine", 1.0],
    ["ACE_atropine", 1.0],
    ["ACE_epinephrine", 1.0],
    ["ACE_painkillers_Item", 1.0],
    ["ACE_splint", 2.0],
    ["ACE_plasmaIV_250", 2.5],
    ["ACE_bloodIV_250", 2.5],
    ["ACE_salineIV_250", 2.5],
    ["ACE_plasmaIV_500", 5.0],
    ["ACE_bloodIV_500", 5.0],
    ["ACE_salineIV_500", 5.0],
    ["ACE_bodyBag", 7.0],
    ["ACE_plasmaIV", 10.0],
    ["ACE_bloodIV", 10.0],
    ["ACE_salineIV", 10.0],
    ["ACE_personalAidKit", 10.0],
    ["ACE_surgicalKit", 15.0],
    ["ACE_suture", 0.1],
    ["FirstAidKit", 4.0],
    ["Medikit", 60.0]
];

private _match = 0;
{
    _x params ["_name", "_unit"];
    // An exact classname match, so an ACE item cannot be confused with
    // another by a substring.
    if (_item == _name) exitWith { _match = _unit; };
} forEach _TABLE;

if (_match == 0) exitWith { 0 };
_match / 10
