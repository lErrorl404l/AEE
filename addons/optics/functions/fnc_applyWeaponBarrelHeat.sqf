#include "..\script_component.hpp"
/*
 * Handheld weapon barrel heat (issue #124 migration).
 *
 * The wiki-documented TI mechanism: the ALPHA channel of a weapon's TI
 * texture is "barrel heat".  A real barrel WARMS as rounds are fired:
 * sustained fire heats a steel barrel to 100-300 C, cooling over ~1-2
 * min after the last shot.  A hot barrel is one of the most visible
 * handheld signatures in thermal.
 *
 * Mechanism: the Fired EH (XEH_postInit) calls ["fired"] here to
 * accumulate heat; the thermal PFH calls ["tick"] per frame to decay
 * it and drive the per-selection thermal substrate (issue #124), which
 * paints the weapon selection with the FLIR white-hot procedural
 * colour.  The weapon model is attached to the unit, so getObjectTextures
 * on the unit includes the weapon selections.
 *
 * This REPLACES the old ti_cloth_hot/cold.rvmat material swap (the
 * #123 bug class): the substrate solves the barrel temperature from
 * physics (q_internal = rounds-deposited heat, inertia from real mass)
 * and renders it as greyscale radiance, not a swapped material.
 *
 * Multiplayer: local per shooter, correct (thermal is per-client).
 *
 * The 0..1 heat state maps to an internal flux: at full heat the barrel
 * sits ~300 C above ambient in equilibrium (the documented sustained-fire
 * range), which the substrate's lumped-capacity solve turns into a
 * physically-grounded surface temperature with the correct time constant.
 */
params ["_weapon", ["_ammo", ""]];

if (!hasInterface) exitWith { 0 };

// Heat state: 0..1 barrel heat, persisted in missionNamespace.
private _heat = missionNamespace getVariable [QGVAR(barrelHeat), 0];
if !(_heat isEqualType 0) then { _heat = 0; };

// ─── Fired: add heat per round ────────────────────────────────────────────
// Each round adds ~0.05 heat (a 30-round mag takes the barrel from cold
// to ~0.5 warm); sustained fire saturates.  A 60-round belt pushes to 1.
// Suppressed fire adds less (gas vents through the can, barrel still
// warms but the signature is muffled).
if (_ammo != "") then {
    private _isSuppressed = getNumber (configFile >> "CfgWeapons" >> _weapon >> "suppression") > 0;
    private _perRound = [0.05, 0.03] select _isSuppressed;
    _heat = (_heat + _perRound) min 1;
    missionNamespace setVariable [QGVAR(barrelHeat), _heat];
    0
};

// ─── Tick: decay and drive the substrate ──────────────────────────────────
// Steel barrel cools with a ~90 s time constant: the barrel loses heat
// to air and the gun's own mass.  Exponential decay.
private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith { 0 };
if (diag_deltaTime > 0) then {
    _heat = _heat * exp (-diag_deltaTime / 90);
    missionNamespace setVariable [QGVAR(barrelHeat), _heat];
};

// Only drive when there is any heat (avoid wasted work when cold).
if (_heat < 0.001) exitWith { 0 };

// Find the weapon selection on the unit model.  The weapon is attached;
// getObjectTextures on the unit includes it.  Cache the selection NAME
// per weapon class.
private _weaponObj = currentWeapon _player;
if (_weaponObj == "") exitWith { 0 };
private _selName = missionNamespace getVariable [format [QGVAR(barrelSel_%1), _weaponObj], ""];
if (_selName == "") then {
    private _textures = getObjectTextures _player;
    private _mats = getObjectMaterials _player;
    private _found = "";
    {
        private _sel = _forEachIndex;
        if (_sel < count _mats) then {
            private _m = toLower (_mats select _sel);
            if (_m find "weapon" >= 0 || _m find _weaponObj >= 0) exitWith {
                private _names = selectionNames _player;
                if (_sel < count _names) then { _found = _names select _sel; };
            };
        };
    } forEach _textures;
    _selName = _found;
    missionNamespace setVariable [format [QGVAR(barrelSel_%1), _weaponObj], _selName];
};
if (_selName == "") exitWith { 0 };

// Internal flux: full heat -> ~300 C above ambient in equilibrium.
// Converted per unit area; the substrate's lumped-capacity solve uses
// the weapon's real mass (getMass) for the correct thermal time constant.
private _qInternal = _heat * 7000;   // W/m2: heat=1 -> ~300 C barrel (sustained fire)

[_player, _selName, "", _qInternal, 0.3] call EFUNC(thermal,applySelectionThermal);
0
