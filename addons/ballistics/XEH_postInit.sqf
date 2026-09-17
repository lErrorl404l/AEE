#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

// ─── Fired EH: propellant-temperature MV correction per shot ──────────────
// Tracks the weapon's ammo temperature (first-order relaxation toward
// ambient + solar soak + shot heat, issue #94) and computes the correction
// for the actual ammo just fired.  Local to the shooter; no remote side
// effects.  Skips thrown items and the ACE3-advanced-ballistics
// double-count guard inside the correction function.
["fired", {
    params ["_unit", "_weapon", "", "", "_ammo", "_magazine", "_projectile"];
    if (_unit != call CBA_fnc_currentUnit) exitWith {};
    if (_weapon == "throw" || _weapon == "put") exitWith {};
    if (_projectile isEqualTo objNull) exitWith {};

    // Round kinetic energy (J): E = 0.5*m*v^2.  Mass from CfgAmmo; the
    // velocity from the magazine's initSpeed (falls back to a 5.56 NATO
    // baseline when the class cannot be resolved).
    private _mass = getNumber (configFile >> "CfgAmmo" >> _ammo >> "hit") * 0.5;
    if (_mass <= 0) then { _mass = 4.0 / 1000; };          // ~4 g baseline
    private _initSpeed = 905;
    {
        if (getText (configFile >> "CfgMagazines" >> configName _x >> "ammo") == _ammo) exitWith {
            _initSpeed = getNumber (configFile >> "CfgMagazines" >> configName _x >> "initSpeed");
        };
    } forEach ((configFile >> "CfgMagazines") call BIS_fnc_returnChildren);
    if (_initSpeed <= 0) then { _initSpeed = 905; };
    private _energyJ = 0.5 * _mass * (_initSpeed ^ 2);

    // Track + read the ammo temperature, then feed it to the correction.
    private _ammoTemp = [_unit, _weapon, _energyJ] call FUNC(calculateAmmoTemperature);

    // Barrel thermal state: temperature + POI shift (issue #130).
    [_unit, _weapon, true] call FUNC(calculateBarrelState);

    // ACE3 advanced ballistics owns the correction; write our tracked
    // temperature into ACE3's per-weapon variable so its table uses AEE's
    // live value (Option C).  Otherwise feed our own correction.
    if (isClass (configFile >> "CfgPatches" >> "ace_advanced_ballistics")) then {
        if (missionNamespace getVariable ["ace_advanced_ballistics_ammoTemperatureEnabled", false]) then {
            _unit setVariable ["ace_overheating_weapon_ammoTemp", _ammoTemp];
        };
    };
    [_ammo, _ammoTemp] call FUNC(calculateMuzzleVelocityCorrection);
}] call CBA_fnc_addEventHandler;

AEE_LOG_INFO("ballistics module post-init complete");

ADDON = true;
