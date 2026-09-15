#include "..\script_component.hpp"
/*
 * Handheld weapon barrel heat.
 *
 * The wiki-documented TI mechanism: the ALPHA channel of a weapon's TI
 * texture is "barrel heat".  The baked texture shows a static barrel, but
 * a real barrel WARMS as rounds are fired: sustained fire heats a steel
 * barrel to 100-300 C, cooling over ~1-2 min after the last shot.  A hot
 * barrel is one of the most visible handheld signatures in thermal.
 *
 * Mechanism: the Fired EH (XEH_postInit) calls ["fired"] here to
 * accumulate heat; the thermal PFH calls ["tick"] per frame to decay it
 * and swap the weapon's material to a hot-TI variant while hot.  The
 * weapon model is attached to the unit, so getObjectTextures on the unit
 * includes the weapon selections.
 *
 * Multiplayer: local per shooter, correct (thermal is per-client).
 *
 * Materials: reuse ti_cloth_hot/cold.rvmat (real TI textures).  The swap
 * is throttled by a heat-state change guard like the other material
 * systems.
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

// ─── Tick: decay and swap the weapon material ─────────────────────────────
// Steel barrel cools with a ~90 s time constant: the barrel loses heat to
// air and the gun's own mass.  Exponential decay.
private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith { 0 };
if (diag_deltaTime > 0) then {
    _heat = _heat * exp (-diag_deltaTime / 90);
    missionNamespace setVariable [QGVAR(barrelHeat), _heat];
};

// Only swap when the heat crosses a threshold (avoid thrash).
private _weaponObj = currentWeapon _player;
if (_weaponObj == "") exitWith { 0 };

    // Material: hot above 0.4, cold below 0.15, keep own between.
    private _material = if (_heat > 0.4) then {
        "\z\aee\addons\optics\data\ti_cloth_hot.rvmat"
    } else {
        ["", "\z\aee\addons\optics\data\ti_cloth_cold.rvmat"] select (_heat < 0.15)
    };
    if (_material == "") exitWith { 0 };

    // Find the weapon selection on the unit model.  The weapon is
    // attached; getObjectTextures on the unit includes it.  Cache the
    // selection index per weapon class.
    private _selIdx = missionNamespace getVariable [format [QGVAR(barrelSel_%1), _weaponObj], -1];
    if (_selIdx < 0) then {
        private _textures = getObjectTextures _player;
        // Weapon selections are the later ones (hands/weapon render last);
        // find the one whose material mentions the weapon's class name.
        // getObjectTextures returns STRINGS (texture paths) — the index is
        // _forEachIndex, not _x (comparing a string to count was the bug).
        private _mats = getObjectMaterials _player;
        private _found = -1;
        {
            private _sel = _forEachIndex;
            if (_sel < count _mats) then {
                private _m = toLower (_mats select _sel);
                if (_m find "weapon" >= 0 || _m find _weaponObj >= 0) exitWith { _found = _sel; };
            };
        } forEach _textures;
        _selIdx = _found;
        missionNamespace setVariable [format [QGVAR(barrelSel_%1), _weaponObj], _selIdx];
    };
    if (_selIdx < 0) exitWith { 0 };

    // Change guard: skip if already at this material.
    private _cur = (getObjectMaterials _player) select _selIdx;
    if (_cur == _material) exitWith { 0 };
    _player setObjectMaterial [_selIdx, _material];
    1
