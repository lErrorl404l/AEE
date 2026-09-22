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

    // Resolve everything for this round in one call (issue #167): the
    // cartridge and bullet identity, the drag standard that matches the
    // bullet shape, the muzzle velocity from the measured anchors (the
    // cartridge curve and the interior-ballistics model behind them),
    // the Miller stability and the drag at the muzzle. Every value comes
    // from the verified database, or from a published formula where no
    // source holds one.
    private _holder = (attachedObjects (vehicle _unit)) select 0;
    private _barrelM = [_weapon, _holder] call FUNC(measureBarrel);
    private _environment = call FUNC(getEnvironmentState);
    _environment params ["_tempC", "_pressureHPa", "_rhoRel"];

    private _shot = [_ammo, _weapon, _barrelM, _tempC, _rhoRel] call FUNC(resolveShot);
    _shot params ["_initSpeed", "_bc", "_dragModel", "_twist", "_stability", "_retard", "_cartridgeId", "_projectileId", "_bcGrade", "_spinRate"];
    missionNamespace setVariable [QGVAR(lastShot), _shot];
    if (_cartridgeId != "") then {
        missionNamespace setVariable [QGVAR(lastCartridge), [_cartridgeId, 0, _twist, 0, 0]];
    };

    // Round kinetic energy (J): E = 0.5*m*v^2. Mass from CfgAmmo, or the
    // resolved bullet where the config carries none.
    private _mass = getNumber (configFile >> "CfgAmmo" >> _ammo >> "hit") * 0.5;
    if (_mass <= 0) then { _mass = 4.0 / 1000; };          // ~4 g baseline
    if (_initSpeed <= 0) then { _initSpeed = 905; };
    private _energyJ = 0.5 * _mass * (_initSpeed ^ 2);

    // Apply the real muzzle velocity to the projectile. Vanilla fires the
    // round with the magazine initSpeed, which is a game value; the
    // solved velocity is the real one. ACE3 advanced ballistics applies
    // its own table on Fired, so it keeps ownership when it is active.
    if (_bc > 0 && _initSpeed > 0) then {
        private _advanced = isClass (configFile >> "CfgPatches" >> "ace_advanced_ballistics");
        if (_advanced) then {
            _advanced = missionNamespace getVariable ["ace_advanced_ballistics_enabled", false];
        };
        if (!_advanced) then {
            private _direction = vectorNormalized (velocity _projectile);
            if ((vectorMagnitude _direction) > 0) then {
                _projectile setVelocity (_direction vectorMultiply _initSpeed);
            };
        };
    };

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
