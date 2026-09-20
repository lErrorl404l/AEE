#include "..\..\script_component.hpp"
/*
 * Hit-point verified part classification (issue #204).
 *
 * Every vehicle model carries GUARANTEED damage metadata: the hit
 * points (getAllHitPointsDamage) name the parts that can be damaged -
 * HitLFWheel, HitEngine, HitFuel, HitGlass, HitTurret.  The engine
 * requires these to exist for the damage model to work, so a hit point
 * is a VERIFIED part label, stronger than any texture-path keyword or
 * selection-name heuristic.
 *
 * The damage data returns three parallel arrays:
 *   [names[], selections[], damages[]]
 * The NAMES are the hit-point identifiers (e.g. "HitLFWheel"), the
 * SELECTIONS are the model selections they damage (e.g. "wheel_1_1").
 * We map the selection -> guaranteed material from the hit-point name.
 *
 * This runs once per vehicle class and caches the map, so the per-
 * selection material detector can consult it at zero extra config cost.
 *
 * Params:
 *   0: _object (OBJECT) - the vehicle.
 *
 * Returns: HASHMAP - model-selection-name -> material class, built from
 *   the object's hit points (empty for objects with no damage model).
 */
params [["_object", objNull]];

private _result = createHashMap;
if (isNull _object) exitWith { _result };
if !(_object isKindOf "AllVehicles") exitWith { _result };

// Cache per class - the hit-point set is static per model.
private _cacheKey = format ["%1_%2", QGVAR(hitPointMaterials), typeOf _object];
private _cached = missionNamespace getVariable [_cacheKey, _result];
if (count _cached > 0) exitWith { _cached };

// getAllHitPointsDamage: [names[], selections[], damages[]].
private _hpData = getAllHitPointsDamage _object;
if (count _hpData < 3) exitWith { _result };
private _hpNames = _hpData select 0;
private _hpSels = _hpData select 1;
if (count _hpNames != count _hpSels) exitWith { _result };

for "_i" from 0 to (count _hpNames - 1) do {
    private _hp = toLower (_hpNames select _i);
    private _sel = _hpSels select _i;
    if (_sel == "") then { continue; };

    // Map the hit-point name to a material.  The engine's hit-point
    // naming is standardised across all vehicles:
    //   HitLF/RF/LB/RBWheel, HitLFWheel... -> rubber
    //   HitEngine, HitMotor -> engine
    //   HitFuel -> engine (the fuel cell sits in the engine bay)
    //   HitGlass, HitWindshield -> glass
    //   HitTurret, HitGun, HitMissile -> metal (weapon systems)
    //   HitBody, HitHull, HitTrack -> metal
    //   HitFuel -> the burning/warm core
    private _mat = "";
    if (_hp find "wheel" >= 0 || {_hp find "tire" >= 0}) then {
        _mat = "rubber";
    } else {
        if (_hp find "engine" >= 0 || {_hp find "motor" >= 0} || {_hp find "fuel" >= 0}) then {
            _mat = "engine";
        } else {
            if (_hp find "glass" >= 0 || {_hp find "window" >= 0} || {_hp find "windshield" >= 0}) then {
                _mat = "glass";
            } else {
                if (_hp find "turret" >= 0 || {_hp find "gun" >= 0} || {_hp find "missile" >= 0}) then {
                    _mat = "metal";   // weapon systems (also covers
                                      // Hit_Turret_Glass - glass turret
                                      // optics read metal-ish, and the
                                      // turret itself is the target)
                } else {
                    if (_hp find "track" >= 0) then {
                        _mat = "metal";   // tank tracks: steel
                    };
                };
            };
        };
    };
    if (_mat != "") then {
        // Only set if not already known (the FIRST hit point naming a
        // selection wins; more specific hit points later in the list
        // could refine it, but the standard names are unambiguous).
        _result set [_sel, _mat];
    };
};

missionNamespace setVariable [_cacheKey, _result];
_result
