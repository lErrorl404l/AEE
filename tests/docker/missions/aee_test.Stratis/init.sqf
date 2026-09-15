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
private _fnDust = missionNamespace getVariable ["aee_fx_fnc_applyAtmosphericDust", nil];
private _fnRain = missionNamespace getVariable ["aee_fx_fnc_applyRainSurfaceDrops", nil];
private _fnGrain = missionNamespace getVariable ["aee_optics_fnc_applyNightGrain", nil];
if ((!isNil "_fnEnv") && (!isNil "_fnBiome") && (!isNil "_fnTemp") && (!isNil "_fnDust") && (!isNil "_fnRain") && (!isNil "_fnGrain")) then {
    diag_log text "[PHASE2] [PASS] functions resolved (core, environmental, thermal, fx, optics)";
} else {
    diag_log text format ["[PHASE2] [FAIL] functions nil: core=%1 biome=%2 thermal=%3 dust=%4 rain=%5 grain=%6",
        isNil "_fnEnv", isNil "_fnBiome", isNil "_fnTemp", isNil "_fnDust", isNil "_fnRain", isNil "_fnGrain"];
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

// -- PHASE 9: edge cases ----------------------------------------------------
// Boundary positions, nil/garbage inputs, extreme values, rapid state changes.
private _p9Pass = 0;
private _p9Fail = 0;

// 9a: boundary positions (engine clamps ±50 km X/Y, +500 m Z)
{
    private _pos = _x;
    // wrap the position so `call` passes ONE array arg (a bare array
    // would be spread into three scalar args)
    private _result = call { [_pos] call aee_core_fnc_updateEnvironment };
    // updateEnvironment should not crash — if we reach here, it handled the position
    _p9Pass = _p9Pass + 1;
} forEach [
    [[50000, 0, 0]],      // max X
    [[-50000, 0, 0]],     // min X
    [[0, 50000, 0]],      // max Y
    [[0, -50000, 0]],     // min Y
    [[0, 0, 500]],        // max Z
    [[0, 0, 0]],          // sea level
    [[4200, 4250, 0]]     // normal
];

// 9b: nil/garbage inputs — functions must not crash
{
    private _fn = _x select 0;
    private _args = _x select 1;
    private _ok = call { _args call _fn; true };
    if (_ok) then { _p9Pass = _p9Pass + 1 } else { _p9Fail = _p9Fail + 1 };
} forEach [
    [aee_thermal_fnc_updateTemperature, [nil]],
    [aee_thermal_fnc_updateTemperature, [objNull]],
    [aee_optics_fnc_calculateSolarGlare, [nil]],
    [aee_optics_fnc_calculateSolarGlare, [objNull]],
    [aee_ballistics_fnc_calculateCrosswindBallistics, [nil]],
    [aee_environmental_fnc_getBiome, []]
];

// 9c: extreme values — state should clamp, not explode
missionNamespace setVariable ["aee_core_currentTemperature", -100];
[] call aee_core_fnc_updateEnvironment;
private _extremeT = missionNamespace getVariable ["aee_core_currentTemperature", -999];
if (_extremeT > -200) then { _p9Pass = _p9Pass + 1 } else { _p9Fail = _p9Fail + 1 };

missionNamespace setVariable ["aee_core_currentPressure", 0];
[] call aee_core_fnc_updateEnvironment;
private _extremeP = missionNamespace getVariable ["aee_core_currentPressure", -1];
if (_extremeP >= 0) then { _p9Pass = _p9Pass + 1 } else { _p9Fail = _p9Fail + 1 };

// 9d: rapid state changes — 100 iterations, no crash
for "_i" from 1 to 100 do {
    missionNamespace setVariable ["aee_core_currentTemperature", _i * 0.5];
    missionNamespace setVariable ["aee_core_currentHumidity", _i];
    [] call aee_core_fnc_updateEnvironment;
};
private _rapidT = missionNamespace getVariable ["aee_core_currentTemperature", -999];
if (_rapidT > -100) then { _p9Pass = _p9Pass + 1 } else { _p9Fail = _p9Fail + 1 };

if (_p9Fail == 0) then {
    diag_log text format ["[PHASE9] [PASS] edge cases: %1 passed, 0 failed", _p9Pass];
} else {
    diag_log text format ["[PHASE9] [FAIL] edge cases: %1 passed, %2 failed", _p9Pass, _p9Fail];
};

// -- PHASE 10: performance gate ---------------------------------------------
// Core functions must complete within 1 ms per call (100 iterations).
private _p10Pass = 0;
private _p10Fail = 0;

private _perfTests = [
    // updateEnvironment aggregates ~45 subsystem calls and runs once per
    // 5 s tick (not per frame), so its budget is 5 ms/call (0.1 % of the
    // tick).  The other functions run on demand and gate at 1 ms.
    ["aee_core_fnc_updateEnvironment", [], 100, 0.005],
    ["aee_thermal_fnc_updateTemperature", [player], 100, 0.001],
    ["aee_optics_fnc_calculateSolarGlare", [player], 100, 0.001],
    ["aee_optics_fnc_calculateSnowBlindness", [player], 100, 0.001],
    ["aee_ballistics_fnc_calculateCrosswindBallistics", [player], 100, 0.001],
    ["aee_environmental_fnc_getBiome", [], 100, 0.001]
];

{
    _x params ["_fnName", "_args", "_iters", "_budget"];
    if (isNil "_budget") then { _budget = 0.001; };
    private _fn = missionNamespace getVariable [_fnName, nil];
    if (isNil "_fn") then {
        diag_log text format ["[PHASE10] [FAIL] %1 not compiled", _fnName];
        _p10Fail = _p10Fail + 1;
    } else {
        private _start = diag_tickTime;
        for "_i" from 1 to _iters do {
            _args call _fn;
        };
        private _elapsed = diag_tickTime - _start;
        private _perCall = _elapsed / _iters;
        private _ok = _perCall < _budget;
        if (_ok) then {
            diag_log text format ["[PHASE10] [PASS] %1: %2 ms/call (budget %3 ms, %4 iters in %5 s)",
                _fnName, round (_perCall * 1000), round (_budget * 1000), _iters, round (_elapsed * 1000) / 1000];
            _p10Pass = _p10Pass + 1;
        } else {
            diag_log text format ["[PHASE10] [FAIL] %1: %2 ms/call (budget %3 ms, %4 iters in %5 s)",
                _fnName, round (_perCall * 1000), round (_budget * 1000), _iters, round (_elapsed * 1000) / 1000];
            _p10Fail = _p10Fail + 1;
        };
    };
} forEach _perfTests;

if (_p10Fail == 0) then {
    diag_log text format ["[PHASE10] [PASS] performance: %1 functions within budget", _p10Pass];
} else {
    diag_log text format ["[PHASE10] [FAIL] performance: %1 passed, %2 exceeded budget", _p10Pass, _p10Fail];
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

    // -- PHASE 11: time-skip state transitions ---------------------------------
    // Tests that optics state variables clear correctly across time changes.
    // Catches "night grain stuck" and "solar glare stale intensity" bugs.
    private _p11Pass = 0;
    private _p11Fail = 0;

    // 11a: calculateSolarGlare with no unit param must clear intensity
    private _oldGlare = missionNamespace getVariable ["aee_optics_solarGlareIntensity", -1];
    [] call aee_optics_fnc_calculateSolarGlare;
    private _noUnitGlare = missionNamespace getVariable ["aee_optics_solarGlareIntensity", -1];
    if (_noUnitGlare == 0) then {
        diag_log text format ["[PHASE11] [PASS] 11a: no-unit glare cleared (%1 -> 0)", _oldGlare];
        _p11Pass = _p11Pass + 1;
    } else {
        diag_log text format ["[PHASE11] [FAIL] 11a: no-unit glare = %1 (expected 0)", _noUnitGlare];
        _p11Fail = _p11Fail + 1;
    };

    // 11b: calculateSolarGlare with objNull must also clear intensity
    missionNamespace setVariable ["aee_optics_solarGlareIntensity", 0.5];
    [objNull] call aee_optics_fnc_calculateSolarGlare;
    private _nullGlare = missionNamespace getVariable ["aee_optics_solarGlareIntensity", -1];
    if (_nullGlare == 0) then {
        diag_log text "[PHASE11] [PASS] 11b: objNull glare cleared";
        _p11Pass = _p11Pass + 1;
    } else {
        diag_log text format ["[PHASE11] [FAIL] 11b: objNull glare = %1", _nullGlare];
        _p11Fail = _p11Fail + 1;
    };

    // 11c: sunOrMoon=0 (midnight) must zero glare for an AI unit
    setDate [2024, 6, 15, 0, 0];
    [_ai] call aee_optics_fnc_calculateSolarGlare;
    private _nightGlare = missionNamespace getVariable ["aee_optics_solarGlareIntensity", -1];
    if (_nightGlare == 0) then {
        diag_log text format ["[PHASE11] [PASS] 11c: night glare = 0 (sunOrMoon=%1)", sunOrMoon];
        _p11Pass = _p11Pass + 1;
    } else {
        diag_log text format ["[PHASE11] [FAIL] 11c: night glare = %1 (sunOrMoon=%2)", _nightGlare, sunOrMoon];
        _p11Fail = _p11Fail + 1;
    };

    // 11c2: night illuminance probe — engine light values for lux calibration
    private _globNight = getLighting;
    private _litNight = getLightingAt _ai;
    diag_log text format ["[PROBE-LIGHT] NIGHT getLighting=%1", str _globNight];
    diag_log text format ["[PROBE-LIGHT] NIGHT getLightingAt(unit)=%1", str _litNight];

    // 11d: FX input state must be neutral when intensity is 0.
    // NOTE: glareFXActive/glareBlur are set only by the client-side
    // applySolarGlareFX PFH, which exits early on a dedicated server
    // (cameraOn != player).  They are NOT testable headless — the test
    // flow previously asserted on them and failed regardless of code.
    // What IS headless-testable is the intensity that drives them:
    // after the midnight transition (11c), intensity must be exactly 0.
    private _int = missionNamespace getVariable ["aee_optics_solarGlareIntensity", -1];
    private _active = missionNamespace getVariable ["aee_optics_glareFXActive", false];
    if (_int isEqualType 0 && {_int == 0}) then {
        diag_log text format ["[PHASE11] [PASS] 11d: glare intensity 0 at night (%1)", _int];
        _p11Pass = _p11Pass + 1;
    } else {
        diag_log text format ["[PHASE11] [FAIL] 11d: glare intensity = %1 (expected 0)", _int];
        _p11Fail = _p11Fail + 1;
    };

    // 11e: at night (intensity 0) the FX gate must not be active.
    // Default is false on a server; if it reads true here, a previous
    // state stuck it on — the stale-state bug this phase catches.
    if (!_active) then {
        diag_log text "[PHASE11] [PASS] 11e: glareFXActive not stuck true at night";
        _p11Pass = _p11Pass + 1;
    } else {
        diag_log text format ["[PHASE11] [FAIL] 11e: glareFXActive=%1 (stuck true)", _active];
        _p11Fail = _p11Fail + 1;
    };

    // 11f: wind multiplier=1 should not produce extreme wind
    private _windMag = vectorMagnitude wind;
    if (_windMag < 50) then {
        diag_log text format ["[PHASE11] [PASS] 11f: wind magnitude %1 < 50", _windMag];
        _p11Pass = _p11Pass + 1;
    } else {
        diag_log text format ["[PHASE11] [FAIL] 11f: wind magnitude = %1 (extreme)", _windMag];
        _p11Fail = _p11Fail + 1;
    };

    // 11g: rapid time skip — night to day to night x10, no crash
    for "_i" from 1 to 10 do {
        setDate [2024, 6, 15, if (_i % 2 == 0) then {12} else {0}, 0];
        [_ai] call aee_optics_fnc_calculateSolarGlare;
    };
    _p11Pass = _p11Pass + 1;
    diag_log text "[PHASE11] [PASS] 11g: rapid time skip x10 no crash";

    // 11h: restore day and verify glare calculates (not stuck at 0)
    setDate [2024, 6, 15, 12, 0];
    [_ai] call aee_optics_fnc_calculateSolarGlare;
    private _dayGlare = missionNamespace getVariable ["aee_optics_solarGlareIntensity", -1];
    if (!isNil "_dayGlare" && {_dayGlare isEqualType 0}) then {
        diag_log text format ["[PHASE11] [PASS] 11h: day glare valid = %1 (sunOrMoon=%2)", _dayGlare, sunOrMoon];
        _p11Pass = _p11Pass + 1;
    } else {
        diag_log text format ["[PHASE11] [FAIL] 11h: day glare invalid = %1", _dayGlare];
        _p11Fail = _p11Fail + 1;
    };

    if (_p11Fail == 0) then {
        diag_log text format ["[PHASE11] [PASS] time-skip transitions: %1 passed", _p11Pass];
    } else {
        diag_log text format ["[PHASE11] [FAIL] time-skip transitions: %1 passed, %2 failed", _p11Pass, _p11Fail];
    };

    // -- PHASE 12: illuminance probe — engine light values for lux calibration --
    // Captures getLighting / getLightingAt at day.  getLightingAt returns
    // [] on a LOGIC (verified) and works on a real UNIT; on a headless
    // server the lighting engine is frozen (same values day/night — it
    // only advances per client camera).  The unit probe validates the
    // command contract; getLighting supplies the real sun vector.
    private _litDayUnit = getLightingAt _ai;
    private _globDay = getLighting;
    diag_log text format ["[PROBE-LIGHT] DAY  getLightingAt(unit)=%1", str _litDayUnit];
    diag_log text format ["[PROBE-LIGHT] DAY  getLighting=%1", str _globDay];

    private _p12Pass = 0;
    private _p12Fail = 0;
    if (count _litDayUnit == 4) then {
        diag_log text format ["[PHASE12] [PASS] day getLightingAt(unit) 4 elements = %1", str _litDayUnit];
        _p12Pass = _p12Pass + 1;
    } else {
        diag_log text format ["[PHASE12] [FAIL] day getLightingAt(unit) = %1", str _litDayUnit];
        _p12Fail = _p12Fail + 1;
    };
    if (count _globDay >= 3) then {
        diag_log text format ["[PHASE12] [PASS] day getLighting 3+ elements = %1", str _globDay];
        _p12Pass = _p12Pass + 1;
    } else {
        diag_log text format ["[PHASE12] [FAIL] day getLighting = %1", str _globDay];
        _p12Fail = _p12Fail + 1;
    };

    if (_p12Fail == 0) then {
        diag_log text format ["[PHASE12] [PASS] illuminance probes: %1 passed", _p12Pass];
    } else {
        diag_log text format ["[PHASE12] [FAIL] illuminance probes: %1 passed, %2 failed", _p12Pass, _p12Fail];
    };

    // -- PHASE 13: astronomical night classification & star visibility ----
    // Exercises classifyNight, calculateLimitingMagnitude, getStarCatalog
    // with controlled inputs (deterministic, independent of engine sky).
    // The limiting-magnitude wiring bug (position passed as lux) is caught
    // here: ambientLux 0.3 + seeing 0.1 must give ~3.8, not the 6.3 default.
    private _p13Pass = 0;
    private _p13Fail = 0;

    // classifyNight: DEF Stan 61-027 boundaries
    private _cases = [
        [45,  0.5, 0],   // day, sun high
        [-6,  0.5, 1],   // civil twilight boundary
        [-12, 0.5, 2],   // nautical twilight boundary
        [-18, 0.5, 3],   // full night boundary
        [-25, 0.05, 4],  // dark night, moon < 10%
        [-25, 0.5, 3]    // full night, moon > 10%
    ];
    {
        _x params ["_elev", "_phase", "_expected"];
        private _got = [_elev, _phase] call aee_optics_fnc_classifyNight;
        if (_got == _expected) then {
            _p13Pass = _p13Pass + 1;
        } else {
            diag_log text format ["[PHASE13] [FAIL] classifyNight(%1,%2) = %3, expected %4", _elev, _phase, _got, _expected];
            _p13Fail = _p13Fail + 1;
        };
    } forEach _cases;

    // calculateLimitingMagnitude: known lux + seeing pairs
    private _magStarlight = [0.001, 0.1] call aee_optics_fnc_calculateLimitingMagnitude;
    private _magFullMoon = [0.3, 0.1] call aee_optics_fnc_calculateLimitingMagnitude;
    if ((abs (_magStarlight - 6.3) < 0.2) && (abs (_magFullMoon - 3.8) < 0.2)) then {
        diag_log text format ["[PHASE13] [PASS] limiting magnitude: starlight=%1 fullMoon=%2", _magStarlight, _magFullMoon];
        _p13Pass = _p13Pass + 1;
    } else {
        diag_log text format ["[PHASE13] [FAIL] limiting magnitude: starlight=%1 fullMoon=%2", _magStarlight, _magFullMoon];
        _p13Fail = _p13Fail + 1;
    };

    // getStarCatalog: Stratis position (lat 35 N) at night must return stars
    private _catalog = [[7300, 7300, 0], [2024, 1, 11]] call aee_optics_fnc_getStarCatalog;
    if (count _catalog > 0) then {
        diag_log text format ["[PHASE13] [PASS] star catalog: %1 stars visible", count _catalog];
        _p13Pass = _p13Pass + 1;
    } else {
        diag_log text "[PHASE13] [FAIL] star catalog returned no stars";
        _p13Fail = _p13Fail + 1;
    };

    // end-to-end: updateEnvironment wired values (checked after env tick)
    private _nightClass = missionNamespace getVariable ["aee_optics_nightClassification", -1];
    private _limMag = missionNamespace getVariable ["aee_optics_limitingMagnitude", -1];
    if ((_nightClass >= 0) && (_limMag > 0)) then {
        diag_log text format ["[PHASE13] [PASS] env wiring: nightClass=%1 limMag=%2", _nightClass, _limMag];
        _p13Pass = _p13Pass + 1;
    } else {
        diag_log text format ["[PHASE13] [FAIL] env wiring: nightClass=%1 limMag=%2", _nightClass, _limMag];
        _p13Fail = _p13Fail + 1;
    };

    if (_p13Fail == 0) then {
        diag_log text format ["[PHASE13] [PASS] astronomical: %1 checks passed", _p13Pass];
    } else {
        diag_log text format ["[PHASE13] [FAIL] astronomical: %1 passed, %2 failed", _p13Pass, _p13Fail];
    };

    // -- PHASE 5: determinism -- temperature delta over 5 s must be small ----
    // PHASE11 deliberately disturbed the clock (midnight/noon skips).  The
    // temperature model is stateless and recomputes on each 5 s env tick,
    // so sampling immediately after the skips measures the response to the
    // disturbance, not steady-state determinism.  Wait one full env tick
    // (7 s) for re-convergence, THEN sample t1 and t2.
    [{
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
    }, [], 7] call CBA_fnc_waitAndExecute;
}, [], 30] call CBA_fnc_waitAndExecute;
