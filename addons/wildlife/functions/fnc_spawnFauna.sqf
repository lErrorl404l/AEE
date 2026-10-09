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

private _ecologyCorpus = missionNamespace getVariable [QGVAR(ecologyCorpus), []];
if !(_ecologyCorpus isEqualType []) then { _ecologyCorpus = []; };
if (_ecologyCorpus isEqualTo []) exitWith { [] };

private _density = missionNamespace getVariable [QGVAR(density), 1.0];
if !(_density isEqualType 0) then { _density = 1.0; };
if (_density <= 0) exitWith { [] };

private _biome = [QEGVAR(weather,localBiome), "", 2] call EFUNC(lib,readState);

private _waterFrac = 0;
private _coast = [_position, 200] call EFUNC(weather,getCoastDistance);
if (_coast isEqualType 0) then {
    _waterFrac = 1 - ((_coast / 200) min 1);
};

private _signals = missionNamespace getVariable [QEGVAR(weather,terrainSignals), []];
if !(_signals isEqualType []) then { _signals = []; };
private _vegScore = ([_signals] call FUNC(vegScore)) * _density;

// The matcher reads the true conditions, not a night boolean.  The sun
// elevation, the air temperature and the month come from the core state.
private _sunElevation = [QEGVAR(core,currentSunElevation), 30, 1] call EFUNC(lib,readState);
private _temperature = [QEGVAR(core,currentTemperature), 15, 1] call EFUNC(lib,readState);
private _month = date select 1;

private _structureFrac = 0;
if ((count _signals) >= 3) then {
    private _structVotes = _signals select 2;
    if (_structVotes isEqualType 0) then { _structureFrac = ((_structVotes max 0) min 1); };
};

private _assetMap = missionNamespace getVariable [QGVAR(assetMap), []];
if !(_assetMap isEqualType []) then { _assetMap = []; };

private _seed = (floor (_position select 0)) + ((floor (_position select 1)) * 31) + (floor CBA_missionTime);
private _matches = [
    _biome, _sunElevation, _temperature, _month, _waterFrac, _vegScore,
    "ground", _structureFrac, [0, 0], _seed, _ecologyCorpus
] call FUNC(getSpeciesMatch);

// The local environment sample gates the spawn: a group below the suitability
// floor is not spawned here.  The environment layer is a sub-switch, and the
// cell size and the millisecond budget come from the operator settings.
private _envEnabled = missionNamespace getVariable [QGVAR(environmentEnabled), true];
if !(_envEnabled isEqualType true) then { _envEnabled = true; };
private _environment = [];
if (_envEnabled) then {
    private _cellSize = missionNamespace getVariable [QGVAR(environmentCellSize), 25];
    if !(_cellSize isEqualType 0) then { _cellSize = 25; };
    private _budgetMs = missionNamespace getVariable [QGVAR(environmentBudgetMs), 2.0];
    if !(_budgetMs isEqualType 0) then { _budgetMs = 2.0; };
    _environment = [_position, _cellSize, 5, 12, _budgetMs] call FUNC(sampleNeighbourhood);
};

// Map each matched group to the vanilla fauna classes of its family.  The
// group id carries the family as its first token ("temperate_bird_dawn").
private _species = [];
for "_m" from 0 to ((count _matches) - 1) do {
    private _match = _matches select _m;
    private _groupId = _match select 0;

    // The group habitat weights and the sound group from the corpus row.
    // The sound group is stored on the agent so the emitter layer can resolve
    // a looping source class for it without a per-species branch here.
    private _habitat = [];
    private _soundGroup = "";
    for "_r" from 0 to ((count _ecologyCorpus) - 1) do {
        if (((_ecologyCorpus select _r) select 1) == _groupId) then {
            _habitat = (_ecologyCorpus select _r) select 9;
            _soundGroup = (_ecologyCorpus select _r) select 12;
        };
    };

    if (!_envEnabled || (([_environment, _habitat] call FUNC(environmentSuitability)) >= WILDLIFE_SUITABILITY_MIN)) then {
        private _family = (_groupId splitString "_") select 0;
        private _count = 1 + (floor ((_match select 1) * 4));
        for "_a" from 0 to ((count _assetMap) - 1) do {
            private _assetRow = _assetMap select _a;
            if (((_assetRow select 0) == "fauna") && ((_assetRow select 1) == _family)) then {
                private _classes = _assetRow select 4;
                for "_c" from 0 to ((count _classes) - 1) do {
                    private _class = _classes select _c;
                    private _seen = false;
                    for "_s" from 0 to ((count _species) - 1) do {
                        if (((_species select _s) select 0) == _class) then { _seen = true; };
                    };
                    if (!_seen) then { _species pushBack [_class, _count, _soundGroup]; };
                };
            };
        };
    };
};

private _forceSpecies = missionNamespace getVariable ["aee_wildlife_forceSpecies", ""];
if !(_forceSpecies isEqualType "") then { _forceSpecies = ""; };
if (_forceSpecies != "") then {
    _species = [[_forceSpecies, 1, ""]];
};

private _created = [];
private _spawned = 0;

for "_s" from 0 to ((count _species) - 1) do {
    private _row = _species select _s;
    private _cls = _row select 0;
    private _count = _row select 1;
    private _group = "";
    if ((count _row) >= 3) then { _group = _row select 2; };
    if !(_group isEqualType "") then { _group = ""; };
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
                // The sound group lets the emitter layer resolve a looping
                // source class for this animal, generically.
                _agent setVariable [QGVAR(soundGroup), _group];
                private _id = format ["wild_%1_%2", (round CBA_missionTime), (count _created)];
                _created pushBack [_id, _agent, _cls, _spawnPos];
                [_id, _agent, _cls] call FUNC(applyAnimalBehaviour);
                _spawned = _spawned + 1;
            };
        };
    };
};

_created
