#include "..\script_component.hpp"

/*
The single wildlife client tick.

Builds the local disturbance field from the local unit's movement and the
nearby units, samples it at the listener, selects the ambient bed and the
silence, applies the force hooks and plays the bed.  The whole layer is
client-local cosmetic ecology.  A machine with no player computes the state
and then stops before any sound or object.

Arguments:
  0: Array - an optional anchor position, empty means the local unit
  1: Bool  - dry run, compute the state and skip every sound and object

Returns:
  Array - [bedKey, gain, disturbance, spook, spookRange]
*/

params [
    ["_anchor", [], [[]]],
    ["_dryRun", false, [false]]
];

private _unit = objNull;
if (hasInterface) then {
    _unit = call CBA_fnc_currentUnit;
};
private _hasUnit = !(isNull _unit);

private _position = _anchor;
if ((count _position) < 2) then {
    if (_hasUnit) then {
        _position = getPos _unit;
    } else {
        _position = [0, 0, 0];
    };
};

// Guarded reads: a nil read that falls through to a default is the #154 bug.
private _biome = [QEGVAR(environmental,localBiome), "", 2] call EFUNC(core,readState);

private _forceBiome = missionNamespace getVariable ["aee_wildlife_forceBiome", ""];
if !(_forceBiome isEqualType "") then { _forceBiome = ""; };
if (_forceBiome != "") then { _biome = _forceBiome; };

private _isNight = sunOrMoon < 0.5;
private _forceNight = missionNamespace getVariable ["aee_wildlife_forceNight", 0];  // non-nil default: nil leaves a private undefined (SQF) and the isEqualType guard throws every tick
if (_forceNight isEqualType false) then { _isNight = _forceNight; };

private _nearWater = 0;
if (_hasUnit) then {
    private _coast = [_position, 200] call EFUNC(environmental,getCoastDistance);
    if (_coast isEqualType 0) then {
        _nearWater = 1 - ((_coast / 200) min 1);
    };
};

private _windVector = wind;
private _wind = (((_windVector select 0) ^ 2) + ((_windVector select 1) ^ 2)) ^ 0.5;

private _rain = rain;
if !(_rain isEqualType 0) then { _rain = 0; };
private _rainAmount = ((_rain max 0) min 1);

// The published soil and surface facts.  Wet ground damps the bed, so a damp
// soundscape is muffled.  readState is the guarded read from the core.
private _soil = [QEGVAR(core,soilMoisture), 0.2, 1] call EFUNC(core,readState);
private _wetness = [QEGVAR(core,surfaceWetness), 0, 1] call EFUNC(core,readState);

private _field = missionNamespace getVariable [QEGVAR(ai,disturbance), []];
if !(_field isEqualType []) then { _field = []; };

private _now = CBA_missionTime;
private _key = [_position] call EFUNC(ai,disturbanceKey);
private _disturbance = [_field, _key, _now, 45] call EFUNC(ai,disturbanceSample);

// Raise the field from soldier traffic.  A quiet walk leaves no trace; a run
// leaves more.  The local unit's stance scales its own trace.  The nearby
// units the client can sense contribute at their own cells.  The scan is
// bounded to a small radius and a fixed unit count so the tick stays flat.
// This runs only with a live local unit and only outside dry run.
if (_hasUnit) then {
    if (!_dryRun) then {
        private _speed = speed _unit;
        if (_speed > 1.5) then {
            private _magnitude = ((_speed / 8) max 0) min 1;
            private _stance = stance _unit;
            if (_stance == "CROUCH") then { _magnitude = _magnitude * 0.75; };
            if (_stance == "PRONE") then { _magnitude = _magnitude * 0.5; };
            _field = [_field, _key, _magnitude, _now] call EFUNC(ai,disturbanceApply);
        };

        private _traffic = _position nearEntities [["CAManBase"], 60];
        private _sensed = 0;
        {
            if (_sensed < 8) then {
                private _other = _x;
                if ((!isNull _other) && (_other != _unit)) then {
                    private _otherSpeed = speed _other;
                    if (_otherSpeed > 1.5) then {
                        private _otherMagnitude = ((_otherSpeed / 8) max 0) min 1;
                        private _otherKey = [getPos _other] call EFUNC(ai,disturbanceKey);
                        _field = [_field, _otherKey, _otherMagnitude, _now] call EFUNC(ai,disturbanceApply);
                        _sensed = _sensed + 1;
                    };
                };
            };
        } forEach _traffic;

        // Bound the field before it is published: drop stale cells, then cap
        // by decayed magnitude.  The prune kernel owns the policy.
        _field = [_field, _now, AI_CELL_CAP, AI_CELL_HORIZON] call EFUNC(ai,disturbancePrune);
        missionNamespace setVariable [QEGVAR(ai,disturbance), _field];
    };
};

// The vegetation signal from aee_environmental_terrainSignals.  The shape is
// [surfaceVotes, vegVotes, structureVotes, waterFrac, meanElevM, maxElevM].
// vegVotes is a HashMap biome code -> indicator vote weight, published by the
// terrain scan.  The strongest single vote is the vegetation score, clamped
// to 0..1.  Max rather than sum: one tree votes for several Koppen codes, so
// a sum double-counts one species.  A map with no classified tree or bush
// yields an empty map and therefore an open-ground score of 0.
private _signals = [QEGVAR(environmental,terrainSignals), [], 3] call EFUNC(core,readState);
private _vegScore = 0;
if ((count _signals) >= 2) then {
    private _votes = _signals select 1;
    if (_votes isEqualType createHashMap) then {
        {
            if (_x > _vegScore) then { _vegScore = _x; };
        } forEach (values _votes);
    };
};
_vegScore = ((_vegScore max 0) min 1);

private _manifest = missionNamespace getVariable [QGVAR(manifest), []];
if !(_manifest isEqualType []) then { _manifest = []; };

private _bed = [_biome, _isNight, _nearWater, _wind, _disturbance, _manifest, _rainAmount, _vegScore] call FUNC(soundBedForContext);
private _bedKey = _bed select 0;
private _bedGain = _bed select 1;

private _decay = missionNamespace getVariable [QGVAR(silenceDecay), 0.05];
if !(_decay isEqualType 0) then { _decay = 0.05; };

private _silence = [_disturbance, _decay] call FUNC(disturbanceSilence);
private _forceSilence = missionNamespace getVariable ["aee_wildlife_forceSilence", -1];
if !(_forceSilence isEqualType 0) then { _forceSilence = -1; };
if (_forceSilence >= 0) then { _silence = ((_forceSilence max 0) min 1); };

private _gain = ((_bedGain * _silence) max 0) min 1;

// Wet ground damps the bed: saturated soil and standing surface water muffle
// the soundscape, so a damp cell is quieter than a dry one.
private _damp = 1 - ((((_soil max _wetness) max 0) min 1) * 0.3);
_gain = ((_gain * _damp) max 0) min 1;

private _spook = false;
private _spookPosition = _position;
private _forceSpook = missionNamespace getVariable ["aee_wildlife_forceSpook", []];
if (_forceSpook isEqualType []) then {
    if ((count _forceSpook) >= 2) then {
        _spook = true;
        _spookPosition = _forceSpook;
    };
} else {
    if (_disturbance > 0.6) then { _spook = true; };
};

private _spookRange = 0;
if (_spook) then {
    private _sensitivity = missionNamespace getVariable [QGVAR(spookSensitivity), 1];
    if !(_sensitivity isEqualType 0) then { _sensitivity = 1; };
    _spookRange = [_disturbance, _sensitivity, 20] call FUNC(spookRange);
};

private _state = [_bedKey, _gain, _disturbance, _spook, _spookRange];

if (_dryRun) exitWith { _state };
if (!_hasUnit) exitWith { _state };

private _enabled = missionNamespace getVariable [QGVAR(enabled), true];
if !(_enabled isEqualType true) then { _enabled = true; };
if (!_enabled) exitWith { _state };

private _ambient = missionNamespace getVariable [QGVAR(ambientEnabled), true];
if !(_ambient isEqualType true) then { _ambient = true; };

// The fauna switches are read here so the slice-two runtime and the debug line
// share one guarded read.
private _animals = missionNamespace getVariable [QGVAR(animalsEnabled), false];
if !(_animals isEqualType true) then { _animals = false; };
private _density = missionNamespace getVariable [QGVAR(density), 1.0];
if !(_density isEqualType 0) then { _density = 1.0; };

if (_spook) then {
    [_spookPosition, 0.9] call FUNC(spookWave);
};

if (_ambient) then {
    if (_gain > 0.01) then {
        private _source = "";
        for "_i" from 0 to ((count _manifest) - 1) do {
            private _row = _manifest select _i;
            if ((_row select 0) == _bedKey) then {
                if (_source == "") then { _source = _row select 1; };
            };
        };
        if (_source != "") then {
            [_source, _position, _gain] call FUNC(playAmbientBed);
        };
    };
};

// Fauna: spawn up to the remaining allowance, then cull what is out of range
// or over the cap.  The spawn budget kernel owns the decision.
if (_animals) then {
    private _fauna = missionNamespace getVariable [QGVAR(fauna), []];
    if !(_fauna isEqualType []) then { _fauna = []; };

    private _liveCount = 0;
    for "_i" from 0 to ((count _fauna) - 1) do {
        private _agent = (_fauna select _i) select 1;
        if (!isNull _agent) then { _liveCount = _liveCount + 1; };
    };

    private _cap = missionNamespace getVariable [QGVAR(maxAnimals), 16];
    if !(_cap isEqualType 0) then { _cap = 16; };
    private _spawnRadius = missionNamespace getVariable [QGVAR(spawnRadius), 350];
    if !(_spawnRadius isEqualType 0) then { _spawnRadius = 350; };
    private _despawnRadius = missionNamespace getVariable [QGVAR(despawnRadius), 600];
    if !(_despawnRadius isEqualType 0) then { _despawnRadius = 600; };

    private _budget = [0, _spawnRadius, _despawnRadius, _liveCount, _cap] call FUNC(spawnBudget);
    if (((_budget select 1)) && ((_budget select 0) > 0)) then {
        private _created = [_position, _budget select 0] call FUNC(spawnFauna);
        missionNamespace setVariable [QGVAR(fauna), _fauna + _created];
    };

    [_position] call FUNC(cullFauna);
};

private _logMsg = format ["bed %1 gain %2 disturbance %3 spook %4 animals %5 density %6", _bedKey, _gain, _disturbance, _spook, _animals, _density];
AEE_LOG_DEBUG(_logMsg);

_state
