#include "..\script_component.hpp"

/*
Per-vehicle mud accretion on wheels/tracks (0–1).

Tracks mud build-up on ground vehicle wheel/track components when
driving on muddy terrain.  Mud accretes while the vehicle moves on
muddy surfaces (surfaceType contains "Mud", "Dirt" or "Soft"), and
decays exponentially on hard / paved surfaces.

Per-vehicle state stored in QGVAR(mudAccretion) hashmap keyed by
vehicle object:
  key:   vehicle object
  value: accretion 0–1

Stale entries (deleted vehicles) are cleaned up each tick.

Consumed by visual texture overlay / vehicle appearance systems.
*/
// ponytail: single hashmap; per-vehicle LRU if scale requires

params [];

if (!EGVAR(core,mudAccretionEnabled)) exitWith {
    missionNamespace setVariable [QGVAR(mudAccretion), createHashMap];
    0
};

private _accretion = missionNamespace getVariable [QGVAR(mudAccretion), createHashMap];
private _accretionRate = missionNamespace getVariable [QGVAR(mudAccretionRate), 0.002];
private _decayRate = missionNamespace getVariable [QGVAR(mudDecayRate), 0.99];
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
private _player = call CBA_fnc_currentUnit;

if (isNil "_player" || !alive _player) exitWith { 0 };

// Ground vehicles within 200 m of the player
private _vehicles = _player nearEntities [["Car", "Tank", "Motorcycle"], 200];

// ─── Per-vehicle pass ─────────────────────────────────────────────────────
{
    if (isNull _x) then { continue; };

    private _current = _accretion getOrDefault [_x, 0];
    private _vSpeed = abs speed _x;

    // Per-vehicle surface under the vehicle
    private _surface = surfaceType (getPos _x);
    private _mudFactor = parseNumber ((_surface find "Mud" >= 0) || (_surface find "Dirt" >= 0) || (_surface find "Soft" >= 0));

    if (_mudFactor > 0) then {
        // Accretion: setting per 5 s tick while moving on mud
        if (_vSpeed > 1) then {
            _current = (_current + _accretionRate * (_interval / 5) * _mudFactor) min 1;
        };
    } else {
        // Exponential decay off mud: setting per 5 s tick
        _current = _current * (_decayRate ^ (_interval / 5));
    };

    _accretion set [_x, _current];
} forEach _vehicles;

// ─── Stale entry cleanup ──────────────────────────────────────────────────
{
    if (isNull _x) then {
        _accretion deleteAt _x;
    };
} forEach (keys _accretion);

missionNamespace setVariable [QGVAR(mudAccretion), _accretion];

count _accretion
