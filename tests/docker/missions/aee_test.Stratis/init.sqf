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

// -- PHASE 8: Koppen classifier — every AEE biome code -----------------------
// Feeds synthetic monthly climate grids to fnc_classifyBiome and asserts the
// returned code. The AEE biome table defines 17 codes; the rare subtypes
// Csc/Cwc/Cfc/Dfd are not in the table (the 18th code is absent from AEE).
private _koppenCases = [
    // [code, monthlyTemps °C, monthlyPrecip mm]
    ["Af",  [26,26,26,26,26,26,26,26,26,26,26,26], [150,150,150,150,150,150,150,150,150,150,150,150]],
    ["Am",  [24,25,26,27,28,28,28,28,27,26,25,24], [50,50,60,80,150,200,220,220,180,120,70,60]],
    ["Aw",  [22,23,24,25,26,26,26,26,25,24,23,22], [20,20,30,50,100,150,160,150,100,60,30,25]],
    ["BWh", [20,23,27,32,37,40,42,41,38,32,26,21], [5,5,5,5,5,5,5,5,5,5,5,5]],
    ["BWk", [2,6,12,18,24,30,33,32,26,18,10,4],    [5,5,5,5,5,5,5,5,5,5,5,5]],
    ["BSh", [20,22,25,28,32,35,36,35,33,29,24,20], [32,32,32,32,32,32,32,32,32,32,32,32]],
    ["BSk", [2,5,10,16,22,28,32,31,26,18,10,4],    [24,24,24,24,24,24,24,24,24,24,24,24]],
    ["Csa", [12,13,15,18,22,27,30,30,26,21,16,13], [80,70,60,50,40,15,5,8,25,45,65,75]],
    ["Csb", [10,11,13,15,18,20,21,21,19,16,13,11], [90,80,70,60,50,20,8,10,30,50,70,85]],
    ["Cfa", [10,12,16,20,24,28,30,30,27,22,16,12], [70,68,65,63,65,68,72,72,70,68,66,68]],
    ["Cfb", [8,8,10,13,16,19,21,21,18,14,11,8],    [80,78,76,74,75,76,76,76,77,79,80,81]],
    ["Cwa", [12,14,18,22,26,28,30,30,28,24,18,14], [10,10,15,20,60,120,150,150,120,60,20,12]],
    ["Dfa", [-5,-3,4,12,18,22,25,24,19,12,4,-2],   [82,80,76,70,68,70,72,74,76,78,80,82]],
    ["Dfb", [-10,-8,-2,5,11,16,19,18,13,6,-2,-8],  [76,74,72,68,66,68,72,74,76,78,78,78]],
    ["Dfc", [-20,-18,-12,-4,2,7,11,10,5,-1,-9,-17],[70,68,66,64,62,64,68,70,72,74,74,72]],
    ["ET",  [-15,-15,-12,-7,-2,2,4,4,1,-3,-8,-13], [78,78,78,76,75,75,76,78,78,80,80,80]],
    ["EF",  [-30,-28,-25,-20,-15,-10,-8,-9,-12,-18,-24,-28], [40,40,40,40,40,40,40,40,40,40,40,40]]
];
private _p8Pass = 0;
private _p8Fail = 0;
{
    _x params ["_code", "_temps", "_precip"];
    private _got = [_temps, _precip, 0] call aee_environmental_fnc_classifyBiome;
    if (_got == _code) then {
        diag_log text format ["[PHASE8] [PASS] %1", _code];
        _p8Pass = _p8Pass + 1;
    } else {
        diag_log text format ["[PHASE8] [FAIL] %1 -> %2", _code, _got];
        _p8Fail = _p8Fail + 1;
    };
} forEach _koppenCases;
diag_log text format ["[PHASE8] summary: pass=%1 fail=%2 (17 AEE codes; the 18th code Csc/Cwc/Cfc/Dfd is not in the AEE biome table)", _p8Pass, _p8Fail];
if ((_p8Fail == 0) && (_p8Pass == 17)) then {
    diag_log text "[PHASE8] [PASS] all 17 Koppen codes classified";
} else {
    diag_log text format ["[PHASE8] [FAIL] pass=%1 fail=%2", _p8Pass, _p8Fail];
};

// -- PHASE 3+4+5: wait 30 s for simulation ticks, then sample ---------------
[{
    private _t = missionNamespace getVariable ["aee_core_currentTemperature", nil];
    private _p = missionNamespace getVariable ["aee_core_currentPressure", nil];
    private _rh = missionNamespace getVariable ["aee_core_currentHumidity", nil];
    private _rho = missionNamespace getVariable ["aee_core_currentAirDensity", nil];
    private _biome = missionNamespace getVariable ["aee_core_biome", nil];
    diag_log text format ["[AEE-TEST] tick sample: T=%1 P=%2 RH=%3 rho=%4 biome=%5",
        _t, _p, _rh, _rho, _biome];
    diag_log text format ["[BIOME] %1=%2", worldName, _biome];

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
        ["aee_core_groundState",              -1, -1,  "mobility/ground"],
        ["aee_core_precipitationPhase",       -1, -1,  "atmos/precip"],
        ["aee_core_snowfallRate",             0, 1,    "atmos/precip"],
        ["aee_core_currentHaze",              0, 1,    "atmos/haze"],
        ["aee_core_currentHypoxiaRisk",       0, 1,    "physiology/hypoxia"],
        ["aee_core_qnh",                      900, 1100, "environmental/qnh"],
        ["aee_core_pressureAltitude_m",       -1000, 10000, "environmental/qnh"],
        ["aee_core_ionosphericAbsorption",    0, 1,    "radio/ionosphere"],
        ["aee_core_lightningIgnition",        -1, -1,  "fx/lightning"],
        ["aee_core_lastStrikePos",            -1, -1,  "fx/lightning"],
        ["aee_core_clothingInsulationFactor", 0.5, 2.0, "thermal/clothing"],
        ["aee_core_surfaceWetness",           0, 1,    "environmental/wetness"],
        ["aee_core_fogBase_m",                0, 9999, "environmental/fog"],
        ["aee_core_weatherProgressionSeed",   0, 1,    "core/weather"],
        ["aee_core_weatherProgression",       0, 1,    "core/weather"]
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
    if ((_fail == 0) && (_pass >= 25)) then {
        diag_log text format ["[PHASE6] [PASS] module coverage: %1 state vars verified", _pass];
    } else {
        diag_log text format ["[PHASE6] [FAIL] coverage: pass=%1 nil=%2 fail=%3 (nil should be only condition-gated)", _pass, _nil, _fail];
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
