// initSettings.inc.sqf - CBA Settings registration for aee_mobility
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// mobility stringtable.

// ── Flight Turbulence ──────────────────────────────────────────────────────
[
    QGVAR(flightTurbulence),
    "CHECKBOX",
    [LLSTRING(flightTurbulence_Name), LLSTRING(flightTurbulence_Description)],
    ["AEE Mobility", "Turbulence"],
    true,   // default: enabled
    true,   // global — needs to be same for all clients
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(turbulenceScale),
    "SLIDER",
    [LLSTRING(turbulenceScale_Name), LLSTRING(turbulenceScale_Description)],
    ["AEE Mobility", "Turbulence"],
    [0, 3, 1, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(turbulenceRadius),
    "SLIDER",
    [LLSTRING(turbulenceRadius_Name), LLSTRING(turbulenceRadius_Description)],
    ["AEE Mobility", "Turbulence"],
    [500, 5000, 2000, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Traction ────────────────────────────────────────────────────────────────
[
    QGVAR(mudAccretionRate),
    "SLIDER",
    [LLSTRING(mudAccretionRate_Name), LLSTRING(mudAccretionRate_Description)],
    ["AEE Mobility", "Hydrology"],
    [0, 0.02, 0.002, 3],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(mudDecayRate),
    "SLIDER",
    [LLSTRING(mudDecayRate_Name), LLSTRING(mudDecayRate_Description)],
    ["AEE Mobility", "Hydrology"],
    [0.9, 1, 0.99, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(tractionScale),
    "SLIDER",
    [LLSTRING(tractionScale_Name), LLSTRING(tractionScale_Description)],
    ["AEE Mobility", "Traction"],
    [0.5, 1.5, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Vehicle Performance ─────────────────────────────────────────────────────
[
    QGVAR(minEnginePower),
    "SLIDER",
    [LLSTRING(minEnginePower_Name), LLSTRING(minEnginePower_Description)],
    ["AEE Mobility", "Traction"],
    [0.1, 0.8, 0.3, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Environment ─────────────────────────────────────────────────────────────
[
    QGVAR(routeRecoveryRate),
    "SLIDER",
    [LLSTRING(routeRecoveryRate_Name), LLSTRING(routeRecoveryRate_Description)],
    ["AEE Mobility", "Route"],
    [1, 1.01, 1.001, 3],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(routeDamageRate),
    "SLIDER",
    [LLSTRING(routeDamageRate_Name), LLSTRING(routeDamageRate_Description)],
    ["AEE Mobility", "Route"],
    [0, 0.0001, 0.00002, 5],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(riverResponseRate),
    "SLIDER",
    [LLSTRING(riverResponseRate_Name), LLSTRING(riverResponseRate_Description)],
    ["AEE Mobility", "Hydrology"],
    [0.01, 0.5, 0.1, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rainAccumDecay),
    "SLIDER",
    [LLSTRING(rainAccumDecay_Name), LLSTRING(rainAccumDecay_Description)],
    ["AEE Mobility", "Hydrology"],
    [0.9, 1, 0.97, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Brake fade (issue #133) ────────────────────────────────────────────────
[
    QGVAR(brakeCoolingTau),
    "SLIDER",
    [LLSTRING(brakeCoolingTau_Name), LLSTRING(brakeCoolingTau_Description)],
    ["AEE Mobility", "Traction"],
    [100, 900, 450, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(brakeRotorMassKg),
    "SLIDER",
    [LLSTRING(brakeRotorMassKg_Name), LLSTRING(brakeRotorMassKg_Description)],
    ["AEE Mobility", "Traction"],
    [4, 40, 16, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(brakeHeatFraction),
    "SLIDER",
    [LLSTRING(brakeHeatFraction_Name), LLSTRING(brakeHeatFraction_Description)],
    ["AEE Mobility", "Traction"],
    [0.1, 1, 0.6, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Hydrology (issue #24) ─────────────────────────────────────────────────
// These drive the rainfall-runoff chain in fnc_calculateRiverWaterLevel.
// The defaults are the operational values the models were calibrated on,
// so the settings change the model rather than decorating it.
[
    QGVAR(riverSectionWidth_m),
    "SLIDER",
    [LLSTRING(riverSectionWidth_m_Name), LLSTRING(riverSectionWidth_m_Description)],
    ["AEE Mobility", "Hydrology"],
    [0.5, 50, 4, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(tidalReach_m),
    "SLIDER",
    [LLSTRING(tidalReach_m_Name), LLSTRING(tidalReach_m_Description)],
    ["AEE Mobility", "Hydrology"],
    [500, 20000, 5000, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(baseflowRate_perDay),
    "SLIDER",
    [LLSTRING(baseflowRate_perDay_Name), LLSTRING(baseflowRate_perDay_Description)],
    ["AEE Mobility", "Hydrology"],
    [0.01, 1, 0.2, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(catchmentArea_m2),
    "SLIDER",
    [LLSTRING(catchmentArea_m2_Name), LLSTRING(catchmentArea_m2_Description)],
    ["AEE Mobility", "Hydrology"],
    [10000, 5000000, 250000, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(bedSlope),
    "SLIDER",
    [LLSTRING(bedSlope_Name), LLSTRING(bedSlope_Description)],
    ["AEE Mobility", "Hydrology"],
    [0.0001, 0.05, 0.001, 5],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(manningN),
    "SLIDER",
    [LLSTRING(manningN_Name), LLSTRING(manningN_Description)],
    ["AEE Mobility", "Hydrology"],
    [0.01, 0.1, 0.035, 3],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Vehicle Rollover ───────────────────────────────────────────────────────
// The threshold physics is the Static Stability Factor (NHTSA) with the
// Gillespie slope correction. Each control is a real input to that model,
// so none of them is inert.
[
    QGVAR(rolloverEnabled),
    "CHECKBOX",
    [LLSTRING(rolloverEnabled_Name), LLSTRING(rolloverEnabled_Description)],
    ["AEE Mobility", "Rollover"],
    true,   // default: enabled
    true,   // global — the threshold must match on every machine
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rolloverDynamicFactor),
    "SLIDER",
    [LLSTRING(rolloverDynamicFactor_Name), LLSTRING(rolloverDynamicFactor_Description)],
    ["AEE Mobility", "Rollover"],
    [0.7, 0.9, 0.8, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rolloverHoldFrames),
    "SLIDER",
    [LLSTRING(rolloverHoldFrames_Name), LLSTRING(rolloverHoldFrames_Description)],
    ["AEE Mobility", "Rollover"],
    [1, 60, 10, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rolloverTorqueScale),
    "SLIDER",
    [LLSTRING(rolloverTorqueScale_Name), LLSTRING(rolloverTorqueScale_Description)],
    ["AEE Mobility", "Rollover"],
    [0.05, 1.0, 0.25, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rolloverRadius),
    "SLIDER",
    [LLSTRING(rolloverRadius_Name), LLSTRING(rolloverRadius_Description)],
    ["AEE Mobility", "Rollover"],
    [10, 200, 50, 0],
    true,
    {}
] call CBA_fnc_addSetting;
