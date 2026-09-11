#include "..\script_component.hpp"

/*
Per-vehicle mud accretion on wheels/tracks (0–1).

Tracks mud build-up on ground vehicle wheel/track components when
driving on muddy terrain.  Mud accretes while the vehicle moves on
"GroundMud" surfaces, and decays on hard / paved surfaces.

Per-vehicle state stored in QGVAR(mudAccretion) hashmap keyed by
vehicle netId:
  key:   vehicle netId (string)
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
private _player = call CBA_fnc_currentUnit;

if (isNil "_player" || !alive _player) exitWith { 0 };

// Ground vehicles within 200 m of the player
private _vehicles = _player nearEntities [["Car", "Tank", "Motorcycle"], 200];
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];

// ─── Per-vehicle pass ─────────────────────────────────────────────────────
{
    if (isNull _x) then { continue; };

    private _netId = netId _x;
    private _current = _accretion getOrDefault [_netId, 0];
    private _vSpeed = abs speed _x;

    if (_groundState == "Mud" && _vSpeed > 1) then {
        // Accretion: 0.002 per tick while moving on mud
        _current = (_current + 0.002) min 1;
    } else {
        if (_groundState != "Mud") then {
            _current = (_current - 0.005) max 0;
        };
    };

    _accretion set [_netId, _current];
} forEach _vehicles;

// ─── Stale entry cleanup ──────────────────────────────────────────────────
{
    if (isNull (objectFromNetId _x)) then {
        _accretion deleteAt _x;
    };
} forEach (keys _accretion);

missionNamespace setVariable [QGVAR(mudAccretion), _accretion];

count _accretion
