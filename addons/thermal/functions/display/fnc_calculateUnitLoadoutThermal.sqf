#include "..\..\script_component.hpp"
/*
 * Unit loadout thermal (issue #204).
 *
 * A soldier's thermal image is not a uniform body: every carried item -
 * uniform, vest, helmet, goggles, weapon, backpack and its contents
 * (magazines, grenades, radios) - has its OWN material, mass, and
 * thermal time constant.  The body warms the gear it touches; the gear
 * warms or cools at a rate set by its mass and material conductivity.
 * A FULL backpack (more mass) warms and cools SLOWER than an empty one -
 * the classic thermal-inertia behaviour.
 *
 * The per-selection substrate already paints each selection; this layer
 * computes the per-item temperature DELTA from the body and scales the
 * per-selection flux so each item reads its own temperature:
 *
 *   itemDelta = bodyHeat * (itemMassInertia) * (materialFactor)
 *
 *   - itemMassInertia: heavier items respond slower (tau ~ mass).
 *     A full backpack has more mass, so a smaller temperature delta
 *     from the body - it warms gradually.
 *   - materialFactor: metal (k 50) conducts body heat fast (mags,
 *     grenades, radios warm quickly); fabric/plastic (k low) insulate.
 *
 * The result is written to QGVAR(loadoutThermal) as a hashmap of
 * selection-name -> flux multiplier, read by fnc_applyClothingThermal
 * to scale each selection's q_internal.
 *
 * Params:
 *   0: _unit (OBJECT) - the unit.
 *
 * Returns: HASHMAP - selection-name -> flux multiplier (0..1).
 */
params [["_unit", objNull]];

if (isNull _unit || !alive _unit) exitWith { createHashMap };

private _result = createHashMap;

// ─── Enumerate the carried gear with real masses ──────────────────────────
// Arma gives the real mass via config (getMass on the container class
// plus its contents).  Each item is a thermal node.
private _gear = [];

// Headgear / goggles (worn).
private _headgear = headgear _unit;
if (_headgear != "") then {
    private _m = getNumber (configFile >> "CfgWeapons" >> _headgear >> "ItemInfo" >> "mass");
    _gear pushBack [_headgear, _m, "plastic"];
};
private _goggles = goggles _unit;
if (_goggles != "") then {
    private _m = getNumber (configFile >> "CfgGlasses" >> _goggles >> "mass");
    _gear pushBack [_goggles, _m, "glass"];
};

// Uniform, vest, backpack - the CONTAINERS plus their contents.
// getMass on the unit already includes the whole loadout, but the
// per-container content mass is what drives each item's inertia.
{
    _x params ["_container", "_items", "_mat"];
    if (isNil "_container" || _container == "") then { continue; };
    private _containerMass = getNumber (configFile >> "CfgWeapons" >> _container >> "ItemInfo" >> "mass");
    if (_containerMass <= 0) then { _containerMass = getNumber (configFile >> "CfgVehicles" >> _container >> "mass"); };
    // Real content mass: sum of each item's config mass.  A full
    // backpack has many times the mass of an empty one - this is the
    // thermal-inertia driver.
    private _contentMass = 0;
    {
        private _magMass = getNumber (configFile >> "CfgMagazines" >> _x >> "mass");
        if (_magMass <= 0) then {
            _magMass = getNumber (configFile >> "CfgWeapons" >> _x >> "ItemInfo" >> "mass");
        };
        if (_magMass <= 0) then {
            _magMass = getNumber (configFile >> "CfgVehicles" >> _x >> "mass");
        };
        _contentMass = _contentMass + _magMass;
    } forEach _items;
    _gear pushBack [_container, (_containerMass + _contentMass), _mat];
} forEach [
    [uniform _unit, uniformItems _unit, "fabric"],
    [vest _unit, vestItems _unit, "fabric"],
    [backpack _unit, backpackItems _unit, "fabric"]
];

// Weapon (hand contact already modelled by the grip flux; here its mass
// adds inertia to the whole-hand system).
private _weapon = primaryWeapon _unit;
if (_weapon != "") then {
    private _m = getNumber (configFile >> "CfgWeapons" >> _weapon >> "WeaponSlotsInfo" >> "mass");
    _gear pushBack [_weapon, _m, "metal"];
};

// ─── Per-item flux multiplier ─────────────────────────────────────────────
// Reference mass: an empty combat load (~15 kg of gear).  Items lighter
// than the reference respond fast (close to the body temp); heavier
// (a full pack) respond slowly - the temperature delta from the body
// shrinks with mass.
private _refMass = 15;
// Body heat estimate: the unit's current skin temperature drives how
    // much heat reaches the carried gear.  Read from the solved
    // selections (the two-node skin output); fall back to a warm-body
    // constant before the first solve.
    private _selMap = missionNamespace getVariable [QGVAR(selTemperature), createHashMap];
    private _bodyHeat = missionNamespace getVariable [QGVAR(bodyHeatEstimate), 0.5];
    private _bodySels = [_unit] call FUNC(getThermalSelections);
    if (count _bodySels > 0) then {
        private _names = selectionNames _unit;
        private _first = _bodySels select 0;
        if (_first < count _names) then {
            private _skin = _selMap getOrDefault [format ["%1|%2", _unit, (_names select _first)], -999];
            if (_skin > -900) then {
                private _air = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
                if !(_air isEqualType 0) then { _air = 15; };
                _bodyHeat = ((_skin - _air) / 20) max 0 min 1;
                missionNamespace setVariable [QGVAR(bodyHeatEstimate), _bodyHeat];
            };
        };
    };
{
    _x params ["_class", "_mass", "_mat"];
    if (_mass <= 0) then { _mass = 1; };
    // Thermal inertia: heavier responds slower.  tau ~ mass, so the
    // equilibrium delta from the body is 1/(1 + mass/ref).
    private _inertia = 1 / (1 + (_mass / _refMass));
    // Material factor: metal conducts body heat fast, fabric insulates.
    private _matFactor = switch (_mat) do {
        case "metal": { 1.0 };
        case "glass": { 0.6 };
        case "plastic": { 0.4 };
        default { 0.3 };   // fabric/leather
    };
    private _flux = _bodyHeat * _inertia * _matFactor;
    // Map the item to its model selection: the item class appears in
    // the selection material path (the weapon detection pattern).
    private _selMap = [_unit] call FUNC(getThermalSelections);
    private _names = selectionNames _unit;
    {
        private _idx = _x;
        if (_idx < count _names) then {
            private _matPath = toLower ((getObjectMaterials _unit) param [_idx, ""]);
            if (_matPath find (toLower _class) >= 0) then {
                _result set [format ["%1|%2", _unit, (_names select _idx)], _flux];
            };
        };
    } forEach _selMap;
} forEach _gear;

_result
