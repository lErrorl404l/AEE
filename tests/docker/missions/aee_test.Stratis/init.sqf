// AEE headless test mission.
// Runs on the dedicated server with -autoInit and the server.cfg Missions
// template. Writes [PHASE<n>] [PASS|FAIL] lines to the RPT; verify.py checks
// them. CBA_fnc_waitAndExecute takes [function, args, delay].

diag_log text "[AEE-TEST] mission start";

// -- PHASE 1: settings registered by initSettings.inc.sqf ------------------
private _enabled = missionNamespace getVariable ["aee_core_enabled", -1];
private _interval = missionNamespace getVariable ["aee_core_updateInterval", -1];
diag_log text format ["[AEE-TEST] settings: enabled=%1 interval=%2", _enabled, _interval];
if ((_enabled == true) && (_interval == 5)) then {
    diag_log text "[PHASE1] [PASS] settings registered (enabled=true, interval=5)";
} else {
    diag_log text format ["[PHASE1] [FAIL] settings: enabled=%1 interval=%2", _enabled, _interval];
};

// -- PHASE 2: functions compiled and resolvable -----------------------------
private _fnEnv = missionNamespace getVariable ["aee_core_fnc_updateEnvironment", nil];
private _fnBiome = missionNamespace getVariable ["aee_environmental_fnc_getBiome", nil];
private _fnTemp = missionNamespace getVariable ["aee_thermal_fnc_updateTemperature", nil];
if ((!isNil "_fnEnv") && (!isNil "_fnBiome") && (!isNil "_fnTemp")) then {
    diag_log text "[PHASE2] [PASS] functions resolved (core, environmental, thermal)";
} else {
    diag_log text format ["[PHASE2] [FAIL] functions nil: core=%1 biome=%2 thermal=%3",
        isNil "_fnEnv", isNil "_fnBiome", isNil "_fnTemp"];
};

// -- diagnostic: does getBiome store a value? --------------------------------
private _biomeBefore = missionNamespace getVariable ["aee_core_biome", "<missing>"];
diag_log text format ["[AEE-TEST] biome before call: %1", _biomeBefore];
[] call aee_environmental_fnc_getBiome;
private _biomeAfter = missionNamespace getVariable ["aee_core_biome", "<missing>"];
diag_log text format ["[AEE-TEST] biome after explicit call: %1", _biomeAfter];

// -- PHASE 3+4+5: wait 30 s for simulation ticks, then sample ---------------
[{
    private _t = missionNamespace getVariable ["aee_core_currentTemperature", nil];
    private _p = missionNamespace getVariable ["aee_core_currentPressure", nil];
    private _rh = missionNamespace getVariable ["aee_core_currentHumidity", nil];
    private _rho = missionNamespace getVariable ["aee_core_currentAirDensity", nil];
    private _biome = missionNamespace getVariable ["aee_core_biome", nil];
    diag_log text format ["[AEE-TEST] tick sample: T=%1 P=%2 RH=%3 rho=%4 biome=%5",
        _t, _p, _rh, _rho, _biome];

    if ((!isNil "_t") && (!isNil "_p") && (!isNil "_rh") && (!isNil "_rho") && (!isNil "_biome")) then {
        private _okT = (_t > -60) && (_t < 60);
        private _okP = (_p > 900) && (_p < 1100);
        private _okRH = (_rh >= 0) && (_rh <= 100);
        private _okRho = (_rho > 0.5) && (_rho < 1.6);
        if (_okT && _okP && _okRH && _okRho) then {
            diag_log text format ["[PHASE3] [PASS] state: T=%1 P=%2 RH=%3 rho=%4 biome=%5",
                _t, _p, _rh, _rho, _biome];
        } else {
            diag_log text format ["[PHASE3] [FAIL] state out of range: T=%1 P=%2 RH=%3 rho=%4",
                _t, _p, _rh, _rho];
        };
    } else {
        diag_log text format ["[PHASE3] [FAIL] state nil: T=%1 P=%2 RH=%3 rho=%4 biome=%5",
            isNil "_t", isNil "_p", isNil "_rh", isNil "_rho", isNil "_biome"];
    };

    // -- PHASE 4: compat gating ---------------------------------------------
    private _ace = isClass (configFile >> "CfgPatches" >> "ace_common");
    private _compat = isClass (configFile >> "CfgPatches" >> "aee_compat_ace3");
    if ((!_ace) && (!_compat)) then {
        diag_log text "[PHASE4] [PASS] compat gating (no ACE3, compat skipped)";
    } else {
        diag_log text format ["[PHASE4] [FAIL] compat: ace=%1 aee_compat=%2", _ace, _compat];
    };

    // -- PHASE 5: determinism -- temperature delta over 5 s must be small ----
    private _t1 = missionNamespace getVariable ["aee_core_currentTemperature", -999];
    [{
        params ["_t1"];
        private _t2 = missionNamespace getVariable ["aee_core_currentTemperature", -999];
        private _delta = abs (_t2 - _t1);
        if (_delta < 2) then {
            diag_log text format ["[PHASE5] [PASS] deterministic delta over 5 s = %1", _delta];
        } else {
            diag_log text format ["[PHASE5] [FAIL] delta over 5 s = %1", _delta];
        };
        diag_log text "[AEE-TEST] DONE";
    }, [_t1], 5] call CBA_fnc_waitAndExecute;
}, [], 30] call CBA_fnc_waitAndExecute;
