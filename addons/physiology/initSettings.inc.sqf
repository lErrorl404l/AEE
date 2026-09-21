// initSettings.inc.sqf - CBA Settings registration for aee_physiology
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// physiology stringtable.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Heat Stress HUD ────────────────────────────────────────────────────────
[
    QGVAR(HUDWarningThreshold),
    "SLIDER",
    [LLSTRING(HUDWarningThreshold_Name), LLSTRING(HUDWarningThreshold_Description)],
    ["AEE Physiology", "Thresholds"],
    [0, 1, 0.3, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Dehydration ────────────────────────────────────────────────────────────
[
    QGVAR(SweatRateScale),
    "SLIDER",
    [LLSTRING(SweatRateScale_Name), LLSTRING(SweatRateScale_Description)],
    ["AEE Physiology", "Rates"],
    [0, 3, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(RehydrationRate),
    "SLIDER",
    [LLSTRING(RehydrationRate_Name), LLSTRING(RehydrationRate_Description)],
    ["AEE Physiology", "Rates"],
    [0, 0.5, 0.05, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(HeatStrokeSensitivity),
    "SLIDER",
    [LLSTRING(HeatStrokeSensitivity_Name), LLSTRING(HeatStrokeSensitivity_Description)],
    ["AEE Physiology", "Thresholds"],
    [0, 0.1, 0.03, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Altitude ───────────────────────────────────────────────────────────────
[
    QGVAR(RapidAscentThreshold),
    "SLIDER",
    [LLSTRING(RapidAscentThreshold_Name), LLSTRING(RapidAscentThreshold_Description)],
    ["AEE Physiology", "Thresholds"],
    [50, 500, 150, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(AMSOffsetAltitude),
    "SLIDER",
    [LLSTRING(AMSOffsetAltitude_Name), LLSTRING(AMSOffsetAltitude_Description)],
    ["AEE Physiology", "Thresholds"],
    [1500, 4000, 2500, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Hypoxia ────────────────────────────────────────────────────────────────
[
    QGVAR(HypoxiaRecovery),
    "SLIDER",
    [LLSTRING(HypoxiaRecovery_Name), LLSTRING(HypoxiaRecovery_Description)],
    ["AEE Physiology", "Rates"],
    [0, 1, 0.1, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Cross-sensitivity (dehydration <-> hypoxia) ───────────────────────────
[
    QGVAR(crossSensitivityEnabled),
    "CHECKBOX",
    [LLSTRING(CrossSensitivityEnabled_Name), LLSTRING(CrossSensitivityEnabled_Description)],
    ["AEE Physiology", "Coupling"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(crossSensitivityScale),
    "SLIDER",
    [LLSTRING(CrossSensitivityScale_Name), LLSTRING(CrossSensitivityScale_Description)],
    ["AEE Physiology", "Coupling"],
    [0, 2, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Scent ──────────────────────────────────────────────────────────────────
[
    QGVAR(ScentIntensity),
    "SLIDER",
    [LLSTRING(ScentIntensity_Name), LLSTRING(ScentIntensity_Description)],
    ["AEE Physiology", "Scent"],
    [0, 2, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Fatigue / sleep ────────────────────────────────────────────────────────
[
    QGVAR(fatigueEnabled),
    "CHECKBOX",
    [LLSTRING(FatigueEnabled_Name), LLSTRING(FatigueEnabled_Description)],
    ["AEE Physiology", "Fatigue"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(circadianAmplitude),
    "SLIDER",
    [LLSTRING(CircadianAmplitude_Name), LLSTRING(CircadianAmplitude_Description)],
    ["AEE Physiology", "Fatigue"],
    [0.05, 0.2, 0.12, 3],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Shooter stability ──────────────────────────────────────────────────────
[
    QGVAR(stabilityEnabled),
    "CHECKBOX",
    [LLSTRING(StabilityEnabled_Name), LLSTRING(StabilityEnabled_Description)],
    ["AEE Physiology", "Stability"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Cold weather ───────────────────────────────────────────────────────────
[
    QGVAR(coldWeatherEnabled),
    "CHECKBOX",
    [LLSTRING(ColdWeatherEnabled_Name), LLSTRING(ColdWeatherEnabled_Description)],
    ["AEE Physiology", "Cold Weather"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Diving (ZH-L16C, issue #118) ─────────────────────────────────────────
[
    QGVAR(diveEnabled),
    "CHECKBOX",
    [LLSTRING(DiveEnabled_Name), LLSTRING(DiveEnabled_Description)],
    ["AEE Physiology", "Diving"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(diveGradientFactor),
    "SLIDER",
    [LLSTRING(DiveGradientFactor_Name), LLSTRING(DiveGradientFactor_Description)],
    ["AEE Physiology", "Diving"],
    [0.5, 1.0, 1.0, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── G-LOC and altitude physiology (issue #135) ─────────────────────────────
[
    QGVAR(glocEnabled),
    "CHECKBOX",
    [LLSTRING(GlocEnabled_Name), LLSTRING(GlocEnabled_Description)],
    ["AEE Physiology", "G-LOC"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(agsmAvailable),
    "CHECKBOX",
    [LLSTRING(AGSM_Name), LLSTRING(AGSM_Description)],
    ["AEE Physiology", "G-LOC"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(gsuitEquipped),
    "CHECKBOX",
    [LLSTRING(GSuit_Name), LLSTRING(GSuit_Description)],
    ["AEE Physiology", "G-LOC"],
    false,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(seatReclined),
    "CHECKBOX",
    [LLSTRING(SeatReclined_Name), LLSTRING(SeatReclined_Description)],
    ["AEE Physiology", "G-LOC"],
    false,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Stamina-to-animation coupling (issue #212) ─────────────────────────────
// Couples the physiology state (fatigue, cold, load) to movement speed via
// setAnimSpeedCoef - an exhausted/hypothermic/overloaded soldier moves
// slower.  ACE3 advanced fatigue owns its own coef and is guarded.
[
    QGVAR(movementSpeed),
    "CHECKBOX",
    [LLSTRING(MovementSpeed_Name), LLSTRING(MovementSpeed_Description)],
    ["AEE Physiology", "Movement"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;
