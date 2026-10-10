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
private _tickStart = if (AEE_TRACE_ON) then { diag_tickTime } else { 0 };
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
private _biome = [QEGVAR(weather,localBiome), "", 2] call EFUNC(lib,readState);

private _forceBiome = missionNamespace getVariable ["aee_wildlife_forceBiome", ""];
if !(_forceBiome isEqualType "") then { _forceBiome = ""; };
if (_forceBiome != "") then { _biome = _forceBiome; };

private _isNight = sunOrMoon < 0.5;
private _forceNight = missionNamespace getVariable ["aee_wildlife_forceNight", 0];  // non-nil default: nil leaves a private undefined (SQF) and the isEqualType guard throws every tick
if (_forceNight isEqualType false) then { _isNight = _forceNight; };

private _nearWater = 0;
if (_hasUnit) then {
    private _coast = [_position, 200] call EFUNC(weather,getCoastDistance);
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
private _soil = [QEGVAR(core,soilMoisture), 0.2, 1] call EFUNC(lib,readState);
private _wetness = [QEGVAR(core,surfaceWetness), 0, 1] call EFUNC(lib,readState);

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

        // Continuous sources: the local unit's movement and the nearby
        // vehicle and aircraft engines.  Each is a sound event at its own
        // position, so the same propagation kernel carries it.  The scan is
        // bounded by the radius and the engine count.
        private _soundEvents = missionNamespace getVariable [QGVAR(soundEvents), []];
        if !(_soundEvents isEqualType []) then { _soundEvents = []; };

        private _walk = speed _unit;
        if (_walk > 1.5) then {
            private _walkStrength = ((_walk / 8) max 0.01) min 1;
            private _footDb = (["footstep"] call EFUNC(ambience,acousticSourceDb)) + (20 * (log _walkStrength));
            _soundEvents = [
                _soundEvents, getPosASL _unit, _footDb, "footstep", _now,
                WILDLIFE_ACOUSTIC_EVENT_CAP, WILDLIFE_ACOUSTIC_EVENT_HORIZON
            ] call EFUNC(ambience,acousticPublish);
        };

        private _engines = 0;
        private _engineSources = [];
        { _engineSources pushBack [_x, "vehicle"]; } forEach (_position nearEntities ["LandVehicle", 200]);
        { _engineSources pushBack [_x, "aircraft"]; } forEach (_position nearEntities ["Air", 200]);
        { _engineSources pushBack [_x, "vehicle"]; } forEach (_position nearEntities ["Ship", 200]);

        {
            if (_engines < 8) then {
                private _vehicle = _x select 0;
                private _kind = _x select 1;
                if ((!isNull _vehicle) && (isEngineOn _vehicle)) then {
                    _soundEvents = [
                        _soundEvents, getPosASL _vehicle,
                        ([_kind] call EFUNC(ambience,acousticSourceDb)), _kind, _now,
                        WILDLIFE_ACOUSTIC_EVENT_CAP, WILDLIFE_ACOUSTIC_EVENT_HORIZON
                    ] call EFUNC(ambience,acousticPublish);
                    _engines = _engines + 1;
                };
            };
        } forEach _engineSources;

        missionNamespace setVariable [QGVAR(soundEvents), _soundEvents];

        // Bound the field before it is published: drop stale cells, then cap
        // by decayed magnitude.  The prune kernel owns the policy.
        _field = [_field, _now, AI_CELL_CAP, AI_CELL_HORIZON] call EFUNC(ai,disturbancePrune);
        missionNamespace setVariable [QEGVAR(ai,disturbance), _field];
    };
};

// The auditory stimulus is the propagated sound level at the listener, not a
// fixed range.  The bus holds the recent sound events; fnc_acousticLevel
// spreads, absorbs and occludes them.  The occluder list is bounded by
// fnc_acousticOccluders, and the propagation index is AEE's published
// currentSoundPropagation, so this reuses the existing weather absorption.
private _propIndex = missionNamespace getVariable [QEGVAR(weather,currentSoundPropagation), 1];
if !(_propIndex isEqualType 0) then { _propIndex = 1; };
private _listenerAsl = _position;
if (_hasUnit) then { _listenerAsl = getPosASL _unit; };
private _occluders = [_position] call EFUNC(ambience,acousticOccluders);
private _soundEvents = missionNamespace getVariable [QGVAR(soundEvents), []];
if !(_soundEvents isEqualType []) then { _soundEvents = []; };
private _acoustic = [
    _soundEvents, _listenerAsl, _now, WILDLIFE_ACOUSTIC_EVENT_HORIZON,
    _propIndex, _occluders
] call EFUNC(ambience,acousticSample);
private _acousticLevel = _acoustic select 0;

// The vegetation signal from aee_weather_terrainSignals.  The shape is
// [surfaceVotes, vegVotes, structureVotes, waterFrac, meanElevM, maxElevM].
// vegVotes is a HashMap biome code -> indicator vote weight, published by the
// terrain scan.  The strongest single vote is the vegetation score, clamped
// to 0..1.  Max rather than sum: one tree votes for several Koppen codes, so
// a sum double-counts one species.  A map with no classified tree or bush
// yields an empty map and therefore an open-ground score of 0.
private _signals = [QEGVAR(weather,terrainSignals), [], 3] call EFUNC(lib,readState);
private _vegScore = [_signals] call FUNC(vegScore);

// The settlement overlay.  Element 2 of the terrain signals carries the
// structure votes, the same shape as the vegetation votes, so the strongest
// single vote is the settlement score (max, not sum).  The coastal flag is
// the near-water signal below the water threshold.
private _settlement = 0;
if ((count _signals) >= 3) then {
    private _structVotes = _signals select 2;
    if (_structVotes isEqualType 0) then {
        _settlement = ((_structVotes max 0) min 1);
    } else {
        if (_structVotes isEqualType createHashMap) then {
            private _structList = values _structVotes;
            for "_s" from 0 to ((count _structList) - 1) do {
                private _vote = _structList select _s;
                if ((_vote isEqualType 0) && (_vote > _settlement)) then { _settlement = _vote; };
            };
        };
    };
};
private _coastal = (_nearWater > 0.2);

private _manifest = missionNamespace getVariable [QGVAR(manifest), []];
if !(_manifest isEqualType []) then { _manifest = []; };

private _bed = [
    _biome, _isNight, _nearWater, _wind, _disturbance, _manifest, _rainAmount,
    _vegScore, _settlement, _coastal
] call EFUNC(ambience,soundBedForContext);
private _bedKey = _bed select 0;
private _bedGain = _bed select 1;

private _decay = missionNamespace getVariable [QEGVAR(ambience,silenceDecay), 0.05];
if !(_decay isEqualType 0) then { _decay = 0.05; };

private _silence = [_disturbance, _decay] call EFUNC(ambience,disturbanceSilence);
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
    if (_acousticLevel > WILDLIFE_SPOOK_ACOUSTIC_MIN) then { _spook = true; };
};

private _spookRange = 0;
if (_spook) then {
    private _sensitivity = missionNamespace getVariable [QGVAR(spookSensitivity), 1];
    if !(_sensitivity isEqualType 0) then { _sensitivity = 1; };
    _spookRange = [_disturbance, _sensitivity, 20] call FUNC(spookRange);
};

private _state = [_bedKey, _gain, _disturbance, _spook, _spookRange];

// The consolidated line.  It emits INFO on the first call and DEBUG after,
// and its own guard makes the call one statement when tracing is off.
[_state] call FUNC(logWildlifeState);  // fnc_logWildlifeState

if (_dryRun) exitWith { _state };
if (!_hasUnit) exitWith { _state };

private _enabled = missionNamespace getVariable [QGVAR(enabled), true];
if !(_enabled isEqualType true) then { _enabled = true; };
if (!_enabled) exitWith { _state };

private _ambient = missionNamespace getVariable [QEGVAR(ambience,ambientEnabled), true];
if !(_ambient isEqualType true) then { _ambient = true; };

// The fauna switches are read here so the slice-two runtime and the debug line
// share one guarded read.
private _animals = missionNamespace getVariable [QGVAR(animalsEnabled), false];
if !(_animals isEqualType true) then { _animals = false; };

if (_spook) then {
    [_spookPosition, 0.9] call FUNC(spookWave);
};

if (_ambient) then {
    private _seed = round (_now * 100);
    // The call pitch carries the seeded jitter, the temperature (cricket
    // stridulation) and, for a moving source, the Doppler shift.
    private _callTemp = [QEGVAR(core,currentTemperature), 15, 1] call EFUNC(lib,readState);
    if (_gain > 0.01) then {
        // A deterministic weighted draw over every row with the bed key, so
        // a multi-file context varies instead of playing only its first row.
        private _source = [_manifest, _bedKey, _seed] call FUNC(pickBedSource);
        if (_source != "") then {
            private _bedPitch = [_seed, "", _callTemp, 0] call EFUNC(ambience,callPitch);
            [_source, _position, _gain, _bedPitch] call EFUNC(ambience,playAmbientBed);
        };
    };

    // The behaviour-gated species layer.  The scheduler returns the calls for
    // the current hour; the tick plays a few each second and advances through
    // the schedule, so the dawn chorus is dense and the midday lull is near
    // silent.  The mix carries each group's corpus bins and its sound group.
    private _hourKey = floor (_now / 3600);
    private _cached = missionNamespace getVariable [QGVAR(soundSchedule), []];
    // The schedule is rebuilt on an hour change.  Build it as the value of an
    // if-expression so the local is assigned at THIS scope level, never read
    // back from a local written inside the nested rebuild block.  The hour
    // test is gated, so a short or malformed cache falls through to rebuild.
    private _cacheHit = if ((_cached isEqualType []) && {((count _cached) >= 3)}) then {
        (_cached select 0) == _hourKey
    } else {
        false
    };
    private _schedule = if (_cacheHit) then {
        _cached
    } else {
        private _corpus = missionNamespace getVariable [QGVAR(ecologyCorpus), []];
        if !(_corpus isEqualType []) then { _corpus = []; };
        private _assetMap = missionNamespace getVariable [QGVAR(assetMap), []];
        if !(_assetMap isEqualType []) then { _assetMap = []; };
        private _sunElev = [QEGVAR(core,currentSunElevation), 45, 1] call EFUNC(lib,readState);
        private _temperature = [QEGVAR(core,currentTemperature), 15, 1] call EFUNC(lib,readState);
        private _today = date;
        private _month = 1;
        private _hour = 12;
        if ((count _today) >= 4) then {
            _month = _today select 1;
            _hour = _today select 3;
        };
        private _platforms = [];
        if (isClass (configFile >> "CfgSoundShaders" >> "Deercall_Forest_Night_SoundShader")) then {
            _platforms = ["enoch"];
        };
        private _matches = [
            _biome, _sunElev, _temperature, _month, _nearWater, _vegScore,
            "ground", _settlement, [_wind, _rainAmount], _seed, _corpus
        ] call FUNC(getSpeciesMatch);
        private _mix = [];
        for "_m" from 0 to ((count _matches) - 1) do {
            private _match = _matches select _m;
            private _groupId = _match select 0;
            for "_r" from 0 to ((count _corpus) - 1) do {
                private _row = _corpus select _r;
                if ((_row select 1) == _groupId) then {
                    _mix pushBack [_groupId, _row select 12, _match select 1, _row select 10];
                };
            };
        };
        private _emissions = [
            _hour, _sunElev, _month, _temperature, _wind, _rainAmount, _gain,
            _mix, _assetMap, _platforms, _seed
        ] call EFUNC(ambience,soundTick);
        private _fresh = [_hourKey, _emissions, 0];
        missionNamespace setVariable [QGVAR(soundSchedule), _fresh];
        _fresh
    };

    private _emissions = _schedule select 1;
    if !(_emissions isEqualType []) then { _emissions = []; };
    private _cursor = _schedule select 2;
    if !(_cursor isEqualType 0) then { _cursor = 0; };
    private _total = count _emissions;
    if (_total > 0) then {
        for "_k" from 0 to (WILDLIFE_SOUND_INSTANCE_CAP - 1) do {
            private _emission = _emissions select ((_cursor + _k) mod _total);
            // The species call carries the seeded jitter and the temperature
            // term; the ambient layer has no radial velocity, so no Doppler.
            private _emissionPitch = [(_seed + _k), (_emission select 0), _callTemp, 0] call EFUNC(ambience,callPitch);
            [_emission select 1, _position, _emission select 2, WILDLIFE_SOUND_MAX_DISTANCE, objNull, _emissionPitch] call EFUNC(ambience,playOneShot);
        };
        _cursor = (_cursor + WILDLIFE_SOUND_INSTANCE_CAP) mod _total;
    };
    _schedule set [2, _cursor];
    missionNamespace setVariable [QGVAR(soundSchedule), _schedule];
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

    // Keep a sustained emitter attached to each active animal, bounded to the
    // active fauna near the player.  The scheduler emits behaviour-gated
    // one-shots against the animal object; this keeps a looping source
    // attached where a species has one, and releases it on despawn or when
    // the class changes, so an emitter cannot leak.
    [_position] call EFUNC(ambience,emitterSync);
};

// The tick duration is recorded only inside the trace gate, so the
// production cost stays zero with tracing off.  The state line reads the
// value on the next tick.
if (AEE_TRACE_ON) then {
    missionNamespace setVariable [QGVAR(lastTickMs), (diag_tickTime - _tickStart) * 1000];
};

_state
