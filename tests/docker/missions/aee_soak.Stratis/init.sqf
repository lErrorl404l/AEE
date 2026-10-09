// AEE headless soak and stress mission.
//
// Runs on the dedicated server with -autoInit and the server.cfg mission
// template.  Drives the pure AI and wildlife kernels on a 1 s per-frame
// handler for the configured duration.  Each tick applies the disturbance
// kernel at moving cells, prunes the field and samples it.  Every 30 s it
// emits a sample line.  A stress configuration first drives the kernels to
// saturation, including a bounded test-only agent churn.  At the end it
// re-runs the PHASE10 and PHASE11 budgets and emits the same result lines.
// Writes [SOAK-*] lines to the RPT.  verify_soak.py checks them.
//
// This mission spawns no animal and plays no sound outside the explicit
// stress churn block.  The product layer stays inert on a dedicated server.

diag_log text "[AEE-SOAK] mission start";

// -- configuration ----------------------------------------------------------
// The harness writes soak_config.sqf into this mission folder.  A missing
// file leaves the two defaults in place.
private _soakMinutes = 20;
private _soakStress = false;
if (fileExists "soak_config.sqf") then {
    call compile preprocessFileLineNumbers "soak_config.sqf";
};
private _cfgMinutes = missionNamespace getVariable ["AEE_SOAK_MINUTES", 20];
if (_cfgMinutes isEqualType 0) then { _soakMinutes = _cfgMinutes; };
private _cfgStress = missionNamespace getVariable ["AEE_SOAK_STRESS", false];
if (_cfgStress isEqualType true) then { _soakStress = _cfgStress; };
if (_soakMinutes < 1) then { _soakMinutes = 1; };
diag_log text format ["[AEE-SOAK] config minutes=%1 stress=%2", _soakMinutes, _soakStress];

// -- kernel references ------------------------------------------------------
// Every kernel is fetched once with a non-nil default.  A missing kernel is a
// hard failure, because the soak would otherwise pass vacuously.
private _applyFn = missionNamespace getVariable ["aee_ai_fnc_disturbanceApply", 0];
private _pruneFn = missionNamespace getVariable ["aee_ai_fnc_disturbancePrune", 0];
private _sampleFn = missionNamespace getVariable ["aee_ai_fnc_disturbanceSample", 0];
private _keyFn = missionNamespace getVariable ["aee_ai_fnc_disturbanceKey", 0];
private _decayFn = missionNamespace getVariable ["aee_ai_fnc_stimulusDecay", 0];
private _spookRangeFn = missionNamespace getVariable ["aee_wildlife_fnc_spookRange", 0];
private _spawnBudgetFn = missionNamespace getVariable ["aee_wildlife_fnc_spawnBudget", 0];
private _needsTickFn = missionNamespace getVariable ["aee_wildlife_fnc_needsTick", 0];
private _cullFn = missionNamespace getVariable ["aee_wildlife_fnc_cullFauna", 0];
AEE_SOAK_FNS = [_applyFn, _pruneFn, _sampleFn, _keyFn, _decayFn, _spookRangeFn, _spawnBudgetFn, _needsTickFn, _cullFn];
{
    if !((_x) isEqualType {}) then {
        diag_log text "[SOAK-FAIL] kernel not compiled";
    };
} forEach AEE_SOAK_FNS;

// -- state ------------------------------------------------------------------
AEE_SOAK_FIELD = [];
AEE_SOAK_TICK = 0;
AEE_SOAK_START = -1;
AEE_SOAK_DURATION = _soakMinutes * 60;
AEE_SOAK_LASTSAMPLE = -1;
AEE_SOAK_SPOOK = 0;
AEE_SOAK_FIELDMAX = 0;
AEE_SOAK_FAILCOUNT = 0;
AEE_SOAK_HANDLE = -1;
AEE_SOAK_CHURN = [];
AEE_SOAK_CHURN_PENDING = false;
missionNamespace setVariable ["aee_ai_disturbance", []];
missionNamespace setVariable ["aee_wildlife_fauna", []];

// -- stress saturation burst ------------------------------------------------
// Bounded kernel calls only.  The single agent churn block is test code.  It
// creates 64 agents, culls them, asserts the list is empty, and deletes every
// agent.  This is the only place this mission creates an object.
if (_soakStress) then {
    diag_log text "[SOAK-BURST] start";
    AEE_SOAK_BURST_START = diag_tickTime;
    private _burstKeyFn = AEE_SOAK_FNS select 3;
    private _burstApplyFn = AEE_SOAK_FNS select 0;
    private _burstPruneFn = AEE_SOAK_FNS select 1;
    private _burstSpookFn = AEE_SOAK_FNS select 5;
    private _burstBudgetFn = AEE_SOAK_FNS select 6;
    private _burstNeedsFn = AEE_SOAK_FNS select 7;

    // 4000 distinct cells, then prune to the cap.
    private _cells = AEE_SOAK_FIELD;
    for "_i" from 0 to 3999 do {
        private _row = floor (_i / 100);
        private _col = _i - (_row * 100);
        private _cellKey = [[(_col * 50) + 25, (_row * 50) + 25, 0]] call _burstKeyFn;
        _cells = [_cells, _cellKey, 1, CBA_missionTime] call _burstApplyFn;
    };
    _cells = [_cells, CBA_missionTime, 256, 120] call _burstPruneFn;
    if ((count _cells) > 256) then {
        diag_log text format ["[SOAK-FAIL] distinct-cell burst field %1 over cap 256", count _cells];
        AEE_SOAK_FAILCOUNT = AEE_SOAK_FAILCOUNT + 1;
    };
    diag_log text format ["[SOAK-BURST] distinct cells=4000 field=%1", count _cells];

    // 100000 rapid applies at one cell.  The cell stays one entry.  The field
    // is pruned after this apply phase, before the cap is asserted.
    private _targetKey = [0, 0];
    for "_i" from 1 to 100000 do {
        _cells = [_cells, _targetKey, 1, CBA_missionTime] call _burstApplyFn;
    };
    _cells = [_cells, CBA_missionTime, 256, 120] call _burstPruneFn;
    if ((count _cells) > 256) then {
        diag_log text format ["[SOAK-FAIL] rapid-apply burst field %1 over cap 256", count _cells];
        AEE_SOAK_FAILCOUNT = AEE_SOAK_FAILCOUNT + 1;
    };
    diag_log text format ["[SOAK-BURST] rapid applies=100000 field=%1", count _cells];

    // 100000 spook-range calls at saturation.
    private _satRange = 0;
    for "_i" from 1 to 100000 do {
        _satRange = [1, 1, 20] call _burstSpookFn;
    };
    if (_satRange <= 0) then {
        diag_log text format ["[SOAK-FAIL] spook range %1 not positive at saturation", _satRange];
        AEE_SOAK_FAILCOUNT = AEE_SOAK_FAILCOUNT + 1;
    };
    diag_log text format ["[SOAK-BURST] spook calls=100000 range=%1", _satRange];

    // The spawn budget at the cap and above.
    private _atCap = [0, 350, 600, 16, 16] call _burstBudgetFn;
    private _aboveCap = [0, 350, 600, 20, 16] call _burstBudgetFn;
    private _capOk = ((_atCap select 1) isEqualTo false) && ((_atCap select 0) isEqualTo 0);
    private _aboveOk = ((_aboveCap select 1) isEqualTo false) && ((_aboveCap select 0) isEqualTo 0);
    if (!_capOk || !_aboveOk) then {
        diag_log text "[SOAK-FAIL] spawn budget allowed a spawn at or above the cap";
        AEE_SOAK_FAILCOUNT = AEE_SOAK_FAILCOUNT + 1;
    };
    diag_log text format ["[SOAK-BURST] spawn budget atCap=%1 aboveCap=%2", _atCap, _aboveCap];

    // The needs kernel at saturation.
    private _satNeeds = [1, 1, 100, 0.02, 0.03] call _burstNeedsFn;
    private _needsOk = ((_satNeeds select 0) isEqualTo 1) && ((_satNeeds select 1) isEqualTo 1) && ((_satNeeds select 2) isEqualTo 2);
    if (!_needsOk) then {
        diag_log text format ["[SOAK-FAIL] needs kernel at saturation returned %1", _satNeeds];
        AEE_SOAK_FAILCOUNT = AEE_SOAK_FAILCOUNT + 1;
    };
    diag_log text format ["[SOAK-BURST] needs at saturation=%1", _satNeeds];

    // Bounded agent churn.  Test code only.  createAgent is used directly
    // because fnc_spawnFauna gates on hasInterface and this is a server.
    // The spawn position is the first dry grid cell, so the engine never
    // rejects it for water.
    private _spawnPos = [100, 100, 0];
    private _dryFound = false;
    for "_gx" from 0 to 19 do {
        if (!_dryFound) then {
            for "_gy" from 0 to 19 do {
                if (!_dryFound) then {
                    private _cand = [(_gx * 200) + 100, (_gy * 200) + 100, 0];
                    if (!(surfaceIsWater _cand)) then {
                        _spawnPos = _cand;
                        _dryFound = true;
                    };
                };
            };
        };
    };
    private _churn = [];
    private _fauna = [];
    for "_i" from 1 to 64 do {
        private _agent = createAgent ["Rabbit_F", _spawnPos, [], 0, "NONE"];
        if (!isNull _agent) then {
            private _id = format ["soak_churn_%1", _i];
            _churn pushBack _agent;
            _fauna pushBack [_id, _agent, "Rabbit_F", _spawnPos];
        };
    };
    missionNamespace setVariable ["aee_wildlife_fauna", _fauna];
    if ((count _churn) != 64) then {
        diag_log text format ["[SOAK-FAIL] churn created %1 of 64 agents", count _churn];
        AEE_SOAK_FAILCOUNT = AEE_SOAK_FAILCOUNT + 1;
    };

    // The 10 m cull drops the overflow above the cap.  The 5000 m cull drops
    // every remaining agent because all of them are beyond the despawn radius.
    private _nearAnchor = [(_spawnPos select 0) + 10, _spawnPos select 1, 0];
    private _farAnchor = [(_spawnPos select 0) + 5000, (_spawnPos select 1) + 5000, 0];
    [_nearAnchor] call _cullFn;
    [_farAnchor] call _cullFn;
    private _faunaEnd = missionNamespace getVariable ["aee_wildlife_fauna", []];
    if !(_faunaEnd isEqualTo []) then {
        diag_log text format ["[SOAK-FAIL] churn fauna list not empty: %1", count _faunaEnd];
        AEE_SOAK_FAILCOUNT = AEE_SOAK_FAILCOUNT + 1;
    };
    {
        if (!isNull _x) then { deleteVehicle _x; };
    } forEach _churn;
    // deleteVehicle frees an agent only on the next frame, so the live check
    // is deferred to the soak handler and not run here.
    AEE_SOAK_CHURN = _churn;
    AEE_SOAK_CHURN_PENDING = true;
    diag_log text format ["[SOAK-BURST] churn created=64 list=%1", count _faunaEnd];

    AEE_SOAK_FIELD = _cells;
    diag_log text format ["[SOAK-BURST] done in %1 ms fail=%2", round ((diag_tickTime - AEE_SOAK_BURST_START) * 1000), AEE_SOAK_FAILCOUNT];
};

// -- finalizer --------------------------------------------------------------
// Runs the core and wildlife budgets against the real functions, then emits
// the result and the done marker.  It mirrors the PHASE10 and PHASE11 blocks
// in the aee_test mission exactly.
AEE_SOAK_FINAL = {
    private _p10Pass = 0;
    private _p10Fail = 0;

    private _perfTests = [
        ["aee_core_fnc_updateEnvironment", [], 100, 0.005],
        ["aee_thermal_fnc_updateTemperature", [player], 100, 0.001],
        ["aee_optics_fnc_calculateSolarGlare", [player], 100, 0.001],
        ["aee_optics_fnc_calculateSnowBlindness", [player], 100, 0.001],
        ["aee_ballistics_fnc_calculateCrosswindBallistics", [player], 100, 0.001],
        ["aee_weather_fnc_getBiome", [], 100, 0.001]
    ];

    {
        _x params ["_fnName", "_args", "_iters", "_budget"];
        if (isNil "_budget") then { _budget = 0.001; };
        private _fn = missionNamespace getVariable [_fnName, 0];
        if !(_fn isEqualType {}) then {
            diag_log text format ["[PHASE10] [FAIL] %1 not compiled", _fnName];
            _p10Fail = _p10Fail + 1;
        } else {
            for "_w" from 1 to (round (_iters / 4)) do { _args call _fn; };
            private _best = 1e9;
            for "_s" from 1 to 3 do {
                private _start = diag_tickTime;
                for "_i" from 1 to (round (_iters / 3)) do {
                    _args call _fn;
                };
                private _elapsed = diag_tickTime - _start;
                if (_elapsed < _best) then { _best = _elapsed; };
            };
            private _perCall = _best / (round (_iters / 3));
            if (_perCall < _budget) then {
                diag_log text format ["[PHASE10] [PASS] %1: %2 ms/call (budget %3 ms, best of 3)",
                    _fnName, round (_perCall * 1000), round (_budget * 1000)];
                _p10Pass = _p10Pass + 1;
            } else {
                diag_log text format ["[PHASE10] [FAIL] %1: %2 ms/call (budget %3 ms, best of 3)",
                    _fnName, round (_perCall * 1000), round (_budget * 1000)];
                _p10Fail = _p10Fail + 1;
            };
        };
    } forEach _perfTests;

    if (_p10Fail == 0) then {
        diag_log text format ["[PHASE10] [PASS] performance: %1 functions within budget", _p10Pass];
    } else {
        diag_log text format ["[PHASE10] [FAIL] performance: %1 passed, %2 exceeded budget", _p10Pass, _p10Fail];
    };

    private _p11Pass = 0;
    private _p11Fail = 0;
    private _perfTests11 = [
        ["aee_wildlife_fnc_wildlifeTick", [[0, 0, 0], true], 100, 0.002]
    ];

    {
        _x params ["_fnName", "_args", "_iters", "_budget"];
        if (isNil "_budget") then { _budget = 0.002; };
        private _fn = missionNamespace getVariable [_fnName, 0];
        if !(_fn isEqualType {}) then {
            diag_log text format ["[PHASE11] [FAIL] %1 not compiled", _fnName];
            _p11Fail = _p11Fail + 1;
        } else {
            for "_w" from 1 to (round (_iters / 4)) do { _args call _fn; };
            private _best = 1e9;
            for "_s" from 1 to 3 do {
                private _start = diag_tickTime;
                for "_i" from 1 to (round (_iters / 3)) do {
                    _args call _fn;
                };
                private _elapsed = diag_tickTime - _start;
                if (_elapsed < _best) then { _best = _elapsed; };
            };
            private _perCall = _best / (round (_iters / 3));
            if (_perCall < _budget) then {
                diag_log text format ["[PHASE11] [PASS] %1: %2 ms/call (budget %3 ms, best of 3)",
                    _fnName, round (_perCall * 1000), round (_budget * 1000)];
                _p11Pass = _p11Pass + 1;
            } else {
                diag_log text format ["[PHASE11] [FAIL] %1: %2 ms/call (budget %3 ms, best of 3)",
                    _fnName, round (_perCall * 1000), round (_budget * 1000)];
                _p11Fail = _p11Fail + 1;
            };
        };
    } forEach _perfTests11;

    if (_p11Fail == 0) then {
        diag_log text format ["[PHASE11] [PASS] wildlife: %1 tick within budget", _p11Pass];
    } else {
        diag_log text format ["[PHASE11] [FAIL] wildlife: %1 passed, %2 exceeded budget", _p11Pass, _p11Fail];
    };

    private _agents = missionNamespace getVariable ["aee_ai_agents", []];
    private _agentsEnd = 0;
    if (_agents isEqualType []) then { _agentsEnd = count _agents; };
    diag_log text format ["[SOAK-RESULT] field_max=%1 agents_end=%2", round (AEE_SOAK_FIELDMAX * 1000) / 1000, _agentsEnd];
    diag_log text "[AEE-SOAK] DONE";
};

// -- the 1 s soak handler ---------------------------------------------------
// The handler drives the kernels, samples every 30 s, and finalizes when the
// configured duration is reached.  It removes itself exactly once.
AEE_SOAK_START = CBA_missionTime;
AEE_SOAK_HANDLE = [{
    private _n = CBA_missionTime;
    private _field = AEE_SOAK_FIELD;
    private _tick = AEE_SOAK_TICK + 1;
    private _tickStart = diag_tickTime;
    private _applyFn = AEE_SOAK_FNS select 0;
    private _pruneFn = AEE_SOAK_FNS select 1;
    private _sampleFn = AEE_SOAK_FNS select 2;
    private _keyFn = AEE_SOAK_FNS select 3;
    private _decayFn = AEE_SOAK_FNS select 4;

    // deleteVehicle frees an agent on the next frame, so the churn live check
    // runs on the second tick, after the engine has processed the deletion.
    if ((AEE_SOAK_CHURN_PENDING) && (_tick >= 2)) then {
        private _aliveAfter = 0;
        {
            if (!isNull _x) then { _aliveAfter = _aliveAfter + 1; };
        } forEach AEE_SOAK_CHURN;
        if (_aliveAfter != 0) then {
            diag_log text format ["[SOAK-FAIL] churn left %1 live agents", _aliveAfter];
            AEE_SOAK_FAILCOUNT = AEE_SOAK_FAILCOUNT + 1;
        };
        AEE_SOAK_CHURN_PENDING = false;
    };

    // Up to 9 applies per tick at deterministic moving cells.
    for "_i" from 0 to 8 do {
        private _angle = (_tick * 37) + (_i * 41);
        private _cellPos = [(sin _angle) * 120, (cos _angle) * 120, 0];
        private _cellKey = [_cellPos] call _keyFn;
        _field = [_field, _cellKey, 0.8, _n] call _applyFn;
    };

    // Prune with the owner policy, then sample the field at one cell.
    _field = [_field, _n, 256, 120] call _pruneFn;
    private _probe = [_field, [0, 0], _n, 45] call _sampleFn;
    private _spook = AEE_SOAK_SPOOK;
    if (_probe > 0.6) then { _spook = _spook + 1; };
    private _tickMs = (diag_tickTime - _tickStart) * 1000;

    AEE_SOAK_FIELD = _field;
    AEE_SOAK_TICK = _tick;
    AEE_SOAK_SPOOK = _spook;
    missionNamespace setVariable ["aee_ai_disturbance", _field];

    private _elapsed = _n - AEE_SOAK_START;
    if ((_elapsed - AEE_SOAK_LASTSAMPLE) >= 30 || AEE_SOAK_LASTSAMPLE < 0) then {
        private _max = 0;
        {
            private _decayed = [(_x select 1), _n - (_x select 2), 45] call _decayFn;
            if (_decayed > _max) then { _max = _decayed; };
        } forEach _field;

        private _fauna = missionNamespace getVariable ["aee_wildlife_fauna", []];
        private _live = 0;
        if (_fauna isEqualType []) then {
            { if (!isNull (_x select 1)) then { _live = _live + 1; }; } forEach _fauna;
        };
        private _sounds = missionNamespace getVariable ["aee_wildlife_soundInstances", []];
        private _soundCount = 0;
        if (_sounds isEqualType []) then { _soundCount = count _sounds; };
        private _agents = missionNamespace getVariable ["aee_ai_agents", []];
        private _agentCount = 0;
        if (_agents isEqualType []) then { _agentCount = count _agents; };

        diag_log text format ["[SOAK-SAMPLE] t=%1 tick=%2ms field=%3 max=%4 fauna=%5 sound=%6 agents=%7 spook=%8",
            round _elapsed, round _tickMs, count _field, round (_max * 1000) / 1000, _live, _soundCount, _agentCount, _spook];

        if ((count _field) > 256) then {
            diag_log text format ["[SOAK-FAIL] field %1 over cap 256 at t=%2", count _field, round _elapsed];
            AEE_SOAK_FAILCOUNT = AEE_SOAK_FAILCOUNT + 1;
        };
        if (_soundCount > 8) then {
            diag_log text format ["[SOAK-FAIL] sound %1 over cap 8 at t=%2", _soundCount, round _elapsed];
            AEE_SOAK_FAILCOUNT = AEE_SOAK_FAILCOUNT + 1;
        };
        if (_live > 16) then {
            diag_log text format ["[SOAK-FAIL] fauna %1 over cap 16 at t=%2", _live, round _elapsed];
            AEE_SOAK_FAILCOUNT = AEE_SOAK_FAILCOUNT + 1;
        };

        if (_max > AEE_SOAK_FIELDMAX) then { AEE_SOAK_FIELDMAX = _max; };
        AEE_SOAK_LASTSAMPLE = _elapsed;
    };

    if (_elapsed >= AEE_SOAK_DURATION) then {
        [AEE_SOAK_HANDLE] call CBA_fnc_removePerFrameHandler;
        diag_log text format ["[SOAK-SAMPLE] final t=%1 ticks=%2 fail=%3", round _elapsed, _tick, AEE_SOAK_FAILCOUNT];
        call AEE_SOAK_FINAL;
    };
}, 1] call CBA_fnc_addPerFrameHandler;

diag_log text format ["[AEE-SOAK] handler started duration=%1s", AEE_SOAK_DURATION];
