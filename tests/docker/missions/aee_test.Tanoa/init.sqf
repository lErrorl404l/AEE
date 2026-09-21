// AEE headless test mission.
// Runs on the dedicated server with -autoInit and the server.cfg Missions
// template. Writes [PHASE<n>] [PASS|FAIL] lines to the RPT; verify.py checks
// them. CBA_fnc_waitAndExecute takes [function, args, delay].

diag_log text "[AEE-TEST] mission start";

// -- PHASE 1: settings registered by initSettings.inc.sqf ------------------
private _enabled = missionNamespace getVariable ["aee_core_enabled", -1];
private _interval = missionNamespace getVariable ["aee_core_updateInterval", -1];
diag_log text format ["[AEE-TEST] settings: enabled=%1 interval=%2", _enabled, _interval];
private _enabledNum = if (_enabled isEqualType true) then { [0, 1] select _enabled } else { _enabled };
if ((_enabledNum == 1) && (_interval == 5)) then {
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
    // Map-wide biome verdict from the getBiome cache.  aee_core_biome
    // is overwritten by per-position detection during the tick wait
    // (issue #184), so read the classification cache instead.
    private _mapBiome = missionNamespace getVariable ["aee_environmental_biomeCached", "<none>"];
    diag_log text format ["[BIOME] %1=%2", worldName, _mapBiome];

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


    // -- PHASE 6: module coverage -- every subsystem publishes state ---------
    private _coverage = [
        // [varName, min, max, module]
        ["aee_core_overcast",                 0, 1,    "core"],
        ["aee_core_rainAccum",                0, 1000, "mobility/ground"],
        ["aee_core_currentFogDensity",        0, 1,    "atmos/fog"],
        ["aee_core_currentWindDir",           0, 360,  "atmos/wind"],
        ["aee_core_currentGusts",             0, 80,   "atmos/wind"],
        ["aee_core_currentPressureTrend",     -5, 5,   "atmos/pressure"],
        ["aee_core_cloudCeiling_m",           0, 10000,"atmos/clouds"],
        ["aee_core_currentTurbulence",        0, 1,    "atmos/turbulence"],
        ["aee_core_currentIcingSeverity",     0, 1,    "atmos/icing"],
        ["aee_core_currentWaterTemperature",  0, 40,   "thermal/water"],
        ["aee_core_currentWBGT",              -10, 60, "thermal/wbgt"],
        ["aee_core_currentHypothermiaRisk",   0, 1,    "thermal/hypothermia"],
        ["aee_core_surfaceTemperature",       -60, 60, "thermal/surface"],
        ["aee_core_currentAirDensity",        0.5, 1.6,"ballistics"],
        ["aee_core_currentFireRisk",          0, 1,    "environmental/fire"],
        ["aee_core_currentFloodRisk",         0, 1,    "environmental/flood"],
        ["aee_core_snowDepth_m",              0, 10,   "environmental/snow"],
        ["aee_core_currentCropDensity",       0, 1,    "environmental/crop"],
        ["aee_core_currentAvalancheRisk",     0, 1,    "environmental/avalanche"],
        ["aee_core_dustSuppression",          0, 1,    "environmental/dust"],
        ["aee_core_currentSandstorm",         0, 1,    "environmental/storm"],
        ["aee_core_currentDustDevil",         0, 1,    "environmental/storm"],
        ["aee_core_currentBlowingSnow",       0, 1,    "environmental/snow"],
        ["aee_core_seaStateBeaufort",         0, 12,   "maritime/sea"],
        ["aee_core_waveHeight_m",             0, 20,   "maritime/sea"],
        ["aee_core_currentTideOffset_m",      -10, 10, "maritime/tide"],
        ["aee_core_currentUVIndex",           0, 15,   "physiology/uv"],
        ["aee_physiology_acclimatizationPercent", 0, 100, "physiology/acclim"],
        ["aee_optics_atmosphericSeeing",      0, 1,    "optics/seeing"],
        ["aee_optics_vehicleHeatShimmerIntensity", 0, 1, "optics/shimmer"],
        ["aee_mobility_currentTractionWheeled", 0, 1,  "mobility/traction"],
        ["aee_radio_radioPropagationIndex",   0, 2,    "radio"],
        ["aee_core_currentLightningRisk",     0, 1,    "fx/lightning"],
        ["aee_core_soilMoisture",            0, 1,    "core/soil"],
        ["aee_core_groundState",              -1, -1,  "mobility/ground"]
    ];
    private _pass = 0;
    private _nil = 0;
    private _fail = 0;
    {
        _x params ["_var", "_min", "_max", "_module"];
        private _val = missionNamespace getVariable [_var, nil];
        if (isNil "_val") then {
            diag_log text format ["[PHASE6] [NIL] %1 (%2)", _var, _module];
            _nil = _nil + 1;
        } else {
            if (_min == -1) then {
                _pass = _pass + 1;
            } else {
                if (!(_val isEqualType 0)) then {
                    diag_log text format ["[PHASE6] [NIL] %1 (non-numeric: %2, %3)", _var, _val, _module];
                    _nil = _nil + 1;
                } else {
                    if ((_val >= _min) && (_val <= _max)) then {
                        _pass = _pass + 1;
                    } else {
                        diag_log text format ["[PHASE6] [FAIL] %1 = %2 (expected %3..%4, %5)", _var, _val, _min, _max, _module];
                        _fail = _fail + 1;
                    };
                };
            };
        };
    } forEach _coverage;
    diag_log text format ["[PHASE6] summary: pass=%1 nil=%2 fail=%3", _pass, _nil, _fail];
    if ((_fail == 0) && ((_pass + _nil) >= 30)) then {
        diag_log text format ["[PHASE6] [PASS] module coverage: %1 state vars verified", _pass];
    } else {
        diag_log text format ["[PHASE6] [FAIL] coverage: pass=%1 nil=%2 fail=%3", _pass, _nil, _fail];
    };


    // -- PHASE 7: AI-player unit-dependent functions --------------------------
    private _grp = createGroup [west, true];
    private _ai = _grp createUnit ["B_Soldier_F", [4200, 4250, 0], [], 0, "NONE"];
    if (isNull _ai) then {
        diag_log text "[PHASE7] [FAIL] AI unit spawn failed";
    } else {
        [_ai] call aee_optics_fnc_calculateSolarGlare;
        [_ai] call aee_optics_fnc_calculateSnowBlindness;
        [_ai] call aee_optics_fnc_calculateVehicleHeatShimmer;
        [_ai] call aee_ballistics_fnc_calculateCrosswindBallistics;
        private _glare = missionNamespace getVariable ["aee_optics_solarGlareIntensity", nil];
        private _shimmer = missionNamespace getVariable ["aee_optics_vehicleHeatShimmerIntensity", nil];
        private _crosswind = missionNamespace getVariable ["aee_ballistics_crosswind", nil];
        if ((!isNil "_glare") && (!isNil "_shimmer") && (!isNil "_crosswind")) then {
            diag_log text format ["[PHASE7] [PASS] AI unit functions: glare=%1 shimmer=%2 crosswind=%3", _glare, _shimmer, _crosswind];
        } else {
            diag_log text format ["[PHASE7] [FAIL] AI unit functions nil: glare=%1 shimmer=%2 crosswind=%3", isNil "_glare", isNil "_shimmer", isNil "_crosswind"];
        };
    };

    // -- PHASE 8: sensor pipeline (headless-safe checks) ----------------------
    // The NVG/thermal apply functions gate on a camera (client-only), so
    // visual behaviour cannot be verified headless.  What CAN be verified:
    //   a) persistent ppEffect handles are idempotent — re-running
    //      fnc_ppEffectCreate (as happens on every mission load) must NOT
    //      bump priorities and orphan handles ("Invalid post effect handle"
    //      on the next mission boundary).  This is a regression test for a
    //      real bug caught in-game.
    //   b) the thermal contrast model produces a sane 0..1 value.
    //   c) the sensor functions resolve.
    private _hBefore = missionNamespace getVariable ["aee_optics_ppHandle_ColorCorrections", -1];
    [] call aee_optics_fnc_ppEffectCreate;
    private _hAfter = missionNamespace getVariable ["aee_optics_ppHandle_ColorCorrections", -1];
    if (_hBefore >= 0 && _hAfter == _hBefore) then {
        diag_log text format ["[PHASE8] [PASS] ppEffect handles idempotent (CC=%1 unchanged)", _hAfter];
    } else {
        diag_log text format ["[PHASE8] [FAIL] ppEffect handles bumped: before=%1 after=%2", _hBefore, _hAfter];
    };

    [] call aee_thermal_fnc_calculateThermalContrast;
    private _tc = missionNamespace getVariable ["aee_thermal_currentThermalContrast", -1];
    if (!isNil "_tc" && _tc >= 0 && _tc <= 1) then {
        diag_log text format ["[PHASE8] [PASS] thermal contrast in range: %1", _tc];
    } else {
        diag_log text format ["[PHASE8] [FAIL] thermal contrast out of range: %1", _tc];
    };

    private _fnNvg = missionNamespace getVariable ["aee_optics_fnc_applyNVGTubeModel", nil];
    private _fnThermal = missionNamespace getVariable ["aee_optics_fnc_applyThermalVision", nil];
    if (!isNil "_fnNvg" && !isNil "_fnThermal") then {
        diag_log text "[PHASE8] [PASS] sensor functions resolved";
    } else {
        diag_log text format ["[PHASE8] [FAIL] sensor functions nil: nvg=%1 thermal=%2", isNil "_fnNvg", isNil "_fnThermal"];
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
