#include "..\..\script_component.hpp"
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
private _heat = [QGVAR(barrelHeat), 0, 1] call EFUNC(core,readState);

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
// per weapon class.  The match is DYNAMIC (issue #204): the weapon's own
// class string in its material (works for any weapon), falling back to
// the shared thermal-selection discovery when the class match fails (a
// modded weapon whose material does not embed the class).
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
            // Dynamic: the weapon's class appears in its own material
            // path.  "weapon" is a structural fallback for vanilla.
            if (_m find _weaponObj >= 0 || _m find "weapon" >= 0) exitWith {
                private _names = selectionNames _player;
                if (_sel < count _names) then { _found = _names select _sel; };
            };
        };
    } forEach _textures;
    if (_found == "") then {
        // Modded weapon with no class/material marker: fall back to the
        // dynamic discovery and take the first selection (the weapon is
        // the only part this path heats).
        private _selList = [_player] call FUNC(getThermalSelections);
        if (count _selList > 0) then {
            private _names = selectionNames _player;
            private _i = _selList select 0;
            if (_i < count _names) then { _found = _names select _i; };
        };
    };
    _selName = _found;
    missionNamespace setVariable [format [QGVAR(barrelSel_%1), _weaponObj], _selName];
};
if (_selName == "") exitWith { 0 };

// Internal flux: full heat -> ~300 C above ambient in equilibrium.
// Converted per unit area; the substrate's lumped-capacity solve uses
// the weapon's real mass (getMass) for the correct thermal time constant.
private _qInternal = _heat * 7000;   // W/m2: heat=1 -> ~300 C barrel (sustained fire)

// ─── Hand-placement gradient (issue #204) ─────────────────────────────────
// A held weapon warms from BOTH the firing chamber AND the hands - the
// grip (rear) and foregrip (front) conduct body heat (~32 C skin) into
// the metal, and the heat spreads gradually along the weapon.  The
// barrel/critical parts get the firing flux; the grip parts get a body
// heat term that decays with distance from the hand.  The gradient is a
// wave (MKK pattern) across the weapon's selections: the hand-contact
// point warms first, the heat spreads down the weapon as it persists.
private _weaponSels = [_player] call FUNC(getThermalSelections);
private _wNames = selectionNames _player;
private _wCount = count _weaponSels;
private _applied = 0;
{
    private _wIdx = _x;
    private _wName = if (_wIdx < count _wNames) then { _wNames select _wIdx } else { "" };
    if (_wName == "") then { continue; };
    // Body-heat term: the grip (hand contact) warms the weapon from the
    // operator's skin.  Hand placement = the weapon's critical selection
    // (the one the material scan found).  Heat falls off along the
    // selection order from the grip point.
    private _phase = if (_wCount > 1) then { _forEachIndex / (_wCount - 1) } else { 0.5 };
    private _gripHeat = 600 * (1 - (_phase * 0.7));   // W/m2, hand at rear
    // Combine: firing flux on the weapon's critical selection (matched
    // by NAME - the dynamic discovery's index may differ from the
    // material-scan index), body heat on the grip.
    private _partFlux = [_qInternal, 0] select (_wName != _selName);
    private _flux = _partFlux + _gripHeat;
    [_player, _wName, "", _flux, 0.3] call FUNC(applySelectionThermal);
    _applied = _applied + 1;
} forEach _weaponSels;

_applied
