// initSettings.inc.sqf - CBA Settings registration for aee_strain
//
// Included from XEH_preInit.sqf.  The heat/cold strain, dehydration,
// fatigue, stability and movement-speed knobs moved here from
// aee_physiology and took the aee_strain_* names (ADR-032).

// ── Dehydration ────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(SweatRateScale,"AEE Strain","Rates",0,3,1.0,1);

AEE_SETTING_SLIDER(RehydrationRate,"AEE Strain","Rates",0,0.5,0.05,2);

AEE_SETTING_SLIDER(HeatStrokeSensitivity,"AEE Strain","Thresholds",0,0.1,0.03,2);

// ── Cross-sensitivity (dehydration <-> hypoxia) ───────────────────────────
[
    QGVAR(crossSensitivityEnabled),
    "CHECKBOX",
    [LLSTRING(CrossSensitivityEnabled_Name), LLSTRING(CrossSensitivityEnabled_Description)],
    ["AEE Strain", "Coupling"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(crossSensitivityScale),
    "SLIDER",
    [LLSTRING(CrossSensitivityScale_Name), LLSTRING(CrossSensitivityScale_Description)],
    ["AEE Strain", "Coupling"],
    [0, 2, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Fatigue / sleep ────────────────────────────────────────────────────────
[
    QGVAR(fatigueEnabled),
    "CHECKBOX",
    [LLSTRING(FatigueEnabled_Name), LLSTRING(FatigueEnabled_Description)],
    ["AEE Strain", "Fatigue"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(circadianAmplitude),
    "SLIDER",
    [LLSTRING(CircadianAmplitude_Name), LLSTRING(CircadianAmplitude_Description)],
    ["AEE Strain", "Fatigue"],
    [0.05, 0.2, 0.12, 3],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Shooter stability ──────────────────────────────────────────────────────
[
    QGVAR(stabilityEnabled),
    "CHECKBOX",
    [LLSTRING(StabilityEnabled_Name), LLSTRING(StabilityEnabled_Description)],
    ["AEE Strain", "Stability"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Cold weather ───────────────────────────────────────────────────────────
[
    QGVAR(coldWeatherEnabled),
    "CHECKBOX",
    [LLSTRING(ColdWeatherEnabled_Name), LLSTRING(ColdWeatherEnabled_Description)],
    ["AEE Strain", "Cold Weather"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Stamina-to-animation coupling (issue #212) ─────────────────────────────
[
    QGVAR(movementSpeed),
    "CHECKBOX",
    [LLSTRING(MovementSpeed_Name), LLSTRING(MovementSpeed_Description)],
    ["AEE Strain", "Movement"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Strain",false);
