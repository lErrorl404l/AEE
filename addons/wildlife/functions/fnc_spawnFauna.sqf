#include "..\script_component.hpp"

/*
Spawn client-local fauna around the listener.

Client-only cosmetic ecology.  A machine with no player spawns nothing.  The
species mix comes from fnc_speciesForBiome against the biome, the water, the
vegetation score and the mission density.  Every animal is created with
createAgent, never a vehicle, and the engine animal FSM is disabled on the
object so the substrate can steer it.

The caller owns the cap check.  This function spawns at most _allowed animals
and never more.

Arguments:
  0: Array  - the listener position
  1: Number - the maximum number to spawn this tick

Returns:
  Array - the created entries [id, agent, class, spawnPosition]
*/

params [
    ["_position", [0, 0, 0], [[]]],
    ["_allowed", 0, [0]]
];

if (!hasInterface) exitWith { [] };
private _unit = call CBA_fnc_currentUnit;
if (isNull _unit) exitWith { [] };
if ((count _position) < 2) exitWith { [] };
if (_allowed <= 0) exitWith { [] };

private _enabled = missionNamespace getVariable [QGVAR(enabled), true];
if !(_enabled isEqualType true) then { _enabled = true; };
if (!_enabled) exitWith { [] };

private _animals = missionNamespace getVariable [QGVAR(animalsEnabled), false];
if !(_animals isEqualType true) then { _animals = false; };
if (!_animals) exitWith { [] };

private _table = missionNamespace getVariable [GVAR(speciesTable), []];
if !(_table isEqualType []) then { _table = []; };
if (_table isEqualTo []) exitWith { [] };

private _density = missionNamespace getVariable [QGVAR(density), 1.0];
if !(_density isEqualType 0) then { _density = 1.0; };
if (_density <= 0) exitWith { [] };

private _biome = [QEGVAR(environmental,localBiome), "", 2] call EFUNC(core,readState);
private _isNight = sunOrMoon < 0.5;

private _waterFrac = 0;
private _coast = [_position, 200] call EFUNC(environmental,getCoastDistance);
if (_coast isEqualType 0) then {
    _waterFrac = 1 - ((_coast / 200) min 1);
};

private _veg = 0;
private _signals = missionNamespace getVariable [QEGVAR(environmental,terrainSignals), []];
if (_signals isEqualType []) then {
    if ((count _signals) >= 2) then {
        private _votes = _signals select 1;
        if (_votes isEqualType 0) then { _veg = ((_votes max 0) min 1); };
    };
};
private _vegScore = _veg * _density;

private _seed = (floor (_position select 0)) + ((floor (_position select 1)) * 31) + (floor CBA_missionTime);
private _species = [_biome, _isNight, _waterFrac, _vegScore, _seed, _table] call FUNC(speciesForBiome);

private _forceSpecies = missionNamespace getVariable ["aee_wildlife_forceSpecies", ""];
if !(_forceSpecies isEqualType "") then { _forceSpecies = ""; };
if (_forceSpecies != "") then {
    _species = [[_forceSpecies, 1]];
};

private _created = [];
private _spawned = 0;

for "_s" from 0 to ((count _species) - 1) do {
    private _row = _species select _s;
    private _cls = _row select 0;
    private _count = _row select 1;
    if !(_count isEqualType 0) then { _count = 1; };

    for "_j" from 1 to (round _count) do {
        if (_spawned < _allowed) then {
            private _angle = ((count _created) * 37) mod 360;
            private _dist = 25 + (((_spawned * 13) + (floor (_position select 0))) mod 120);
            private _spawnPos = [
                (_position select 0) + (_dist * (sin _angle)),
                (_position select 1) + (_dist * (cos _angle)),
                0
            ];

            private _agent = createAgent [_cls, _spawnPos, [], 0, "NONE"];
            if (!isNull _agent) then {
                _agent setVariable ["BIS_fnc_animalBehaviour_disable", true];
                private _id = format ["wild_%1_%2", (round CBA_missionTime), (count _created)];
                _created pushBack [_id, _agent, _cls, _spawnPos];
                [_id, _agent, _cls] call FUNC(applyAnimalBehaviour);
                _spawned = _spawned + 1;
            };
        };
    };
};

_created
