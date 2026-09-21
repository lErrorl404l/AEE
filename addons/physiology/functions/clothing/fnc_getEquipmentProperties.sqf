#include "..\..\script_component.hpp"
/*
Comprehensive equipment library (issue #119).

The soldier's complete signature = uniform + vest + helmet, each with
its own physics properties.  Helmets and vests add weight, ballistic
armour (NIJ level), NIR reflectance, and thermal insulation (clo).
The library covers the vanilla equipment families (verified against
the installed game configs) with research-backed values:

  weight  - kg (real issue weights)
  armor   - NIJ protection level 0..3 (0 none, 1 IIA, 2 IIIA, 3 III+plates)
  nirReflectance - NIR reflectance 0..1 (the NVG signature)
  clo     - insulation (helmet ~0.06-0.15, vest ~0.06-0.18)

The resolver walks the CfgEquipment config (explicit entries + the
CfgWeapons inheritance chain for modded items), then falls back to the
classname-family classification (helmet/vest keywords).

Arguments:
  0: unit (OBJECT, default player)

Returns [weightKg, armorLevel, nirReflectance, cloTotal]:
  weightKg    - combined uniform + vest + helmet weight
  armorLevel  - the max NIJ level worn (the vest dominates)
  nirReflectance - the area-weighted NIR (uniform dominant, equipment adds)
  cloTotal    - the combined insulation
*/
params [["_unit", player, [objNull]]];
if (isNull _unit) exitWith { [8.0, 0, 0.40, 0.75] };

// Resolve one item's properties from CfgEquipment (walk the
// inheritance).  The section differs by slot: helmets/vests are
// CfgWeapons classes, backpacks are CfgVehicles classes - the slot
// disambiguates what the item is (headgear/vest/backpack), so the
// resolver walks the correct ancestry per slot.
private _fnResolve = {
    params ["_item", "_def", "_section"];
    if (_item == "") exitWith { _def };
    private _candidate = configFile >> _section >> _item;
    private _depth = 0;
    while {isClass _candidate && _depth < 16} do {
        private _eq = configFile >> "CfgEquipment" >> configName _candidate;
        if (isClass _eq) exitWith {
            [
                getNumber (_eq >> "weight"),
                getNumber (_eq >> "armor"),
                getNumber (_eq >> "nirReflectance"),
                getNumber (_eq >> "clo")
            ]
        };
        _candidate = inheritsFrom _candidate;
        _depth = _depth + 1;
    };
    _def
};

// The uniform properties (the existing resolver).
private _uniformProps = [_unit] call FUNC(getClothingInsulation);   // [clo, alpha, nir, perm, emiss]
private _uniformClo = _uniformProps select 0;
private _uniformNir = _uniformProps select 2;

// The vest + helmet + backpack from CfgEquipment (with classname-family
// fallback).
private _vestItem = vest _unit;
private _helmetItem = headgear _unit;
private _packItem = backpack _unit;

// Vest: NIJ-armour plate carriers dominate the vest armour/weight.
private _vestDef = [2.5, 2, 0.38, 0.10];
private _vest = [_vestItem, _vestDef, "CfgWeapons"] call _fnResolve;
if (_vestItem != "" && _vest isEqualTo _vestDef) then {
    // classname-family fallback (the dynamic pattern)
    private _v = toLower _vestItem;
    _vest = switch (true) do {
        case (_v find "platecarrier" >= 0 ||
              _v find "iotv" >= 0 ||
              _v find "ciras" >= 0 ||
              _v find "spcs" >= 0 ||
              _v find "cpc" >= 0):    { [5.5, 3, 0.35, 0.18] };
        case (_v find "tacvest" >= 0):      { [2.0, 2, 0.38, 0.10] };
        case (_v find "bandollier" >= 0):   { [1.0, 1, 0.40, 0.06] };
        case (_v find "chestrig" >= 0):     { [1.2, 1, 0.40, 0.07] };
        case (_v find "harness" >= 0):      { [1.5, 1, 0.40, 0.08] };
        case (_v find "rebreather" >= 0):   { [3.0, 0, 0.20, 0.15] };
        default                            { _vestDef };
    };
};

// Helmet: ballistic helmets are NIJ IIIA (ACH 1.36-1.72 kg, PASGT
// 1.41-1.91 kg, MICH 1.36-1.63 kg, 6B47 ~1 kg, 6B27 0.95-1.25 kg).
// Aircrew are IIA (HGU-55 1.0-1.1 kg, no ballistic core).
private _helmetDef = [1.4, 2, 0.40, 0.07];
private _helmet = [_helmetItem, _helmetDef, "CfgWeapons"] call _fnResolve;
if (_helmetItem != "" && _helmet isEqualTo _helmetDef) then {
    private _h = toLower _helmetItem;
_helmet = switch (true) do {
        case (_h find "crew" >= 0 ||
              _h find "racing" >= 0):   { [1.0, 1, 0.40, 0.05] };
        case (_h find "pilot" >= 0 ||
              _h find "heli" >= 0):     { [1.1, 1, 0.45, 0.15] };
        case (_h find "watchcap" >= 0 ||
              _h find "milcap" >= 0):   { [0.1, 0, 0.30, 0.12] };
        case (_h find "boonie" >= 0 ||
              _h find "hat" >= 0 ||
              _h find "strawhat" >= 0): { [0.2, 0, 0.40, 0.05] };
        case (_h find "bandanna" >= 0 ||
              _h find "shemag" >= 0 ||
              _h find "turban" >= 0 ||
              _h find "fakeheadgear" >= 0): { [0.1, 0, 0.35, 0.04] };
        case (_h find "cap" >= 0):         { [0.15, 0, 0.38, 0.05] };
        case (_h find "beret" >= 0):       { [0.15, 0, 0.35, 0.04] };
        default                           { _helmetDef };
    };
};

// Backpack: weight is the pack itself + its contents (the load
// command).  The NIR/clo of the pack fabric (camo 0.40, black 0.10).
private _packDef = [5.0, 0, 0.40, 0.10];
private _pack = [_packItem, _packDef, "CfgVehicles"] call _fnResolve;
if (_packItem != "" && _pack isEqualTo _packDef) then {
    private _b = toLower _packItem;
    _pack = switch (true) do {
        // large packs: the rucksack/backpack family (carry weight
        // includes the load via the engine load command)
        case (_b find "backpack" >= 0 ||
              _b find "rucksack" >= 0 ||
              _b find "bergen" >= 0 ||
              _b find "carryall" >= 0 ||
              _b find "assaultpack" >= 0 ||
              _b find "kitbag" >= 0):   { [6.0, 0, 0.40, 0.12] };
        default                        { _packDef };
    };
};
// The pack contents add their carried weight (the engine load
// command: 0..1 of the pack's max capacity).
private _packContents = load (unitBackpack _unit);

// Combine: weight sums (incl. the pack contents), armour = max (the
// vest dominates), NIR is the uniform-dominant average, clo sums.
private _weight = (_vest select 0) + (_helmet select 0) + (_pack select 0)
    + _packContents + 4.0;   // +base uniform weight
private _armor = (_vest select 1) max (_helmet select 1);
private _nir = (_uniformNir + (_vest select 2) * 0.3 + (_helmet select 2) * 0.2
    + (_pack select 2) * 0.1) / 1.6;
private _clo = _uniformClo + (_vest select 3) + (_helmet select 3) + (_pack select 3);

[_weight, _armor, _nir, _clo]

