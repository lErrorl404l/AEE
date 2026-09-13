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
    "AEE Physiology",
    [0, 1, 0.3, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Dehydration ────────────────────────────────────────────────────────────
[
    QGVAR(SweatRateScale),
    "SLIDER",
    [LLSTRING(SweatRateScale_Name), LLSTRING(SweatRateScale_Description)],
    "AEE Physiology",
    [0, 3, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(RehydrationRate),
    "SLIDER",
    [LLSTRING(RehydrationRate_Name), LLSTRING(RehydrationRate_Description)],
    "AEE Physiology",
    [0, 0.5, 0.05, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(HeatStrokeSensitivity),
    "SLIDER",
    [LLSTRING(HeatStrokeSensitivity_Name), LLSTRING(HeatStrokeSensitivity_Description)],
    "AEE Physiology",
    [0, 0.1, 0.03, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Altitude ───────────────────────────────────────────────────────────────
[
    QGVAR(RapidAscentThreshold),
    "SLIDER",
    [LLSTRING(RapidAscentThreshold_Name), LLSTRING(RapidAscentThreshold_Description)],
    "AEE Physiology",
    [50, 500, 150, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(AMSOffsetAltitude),
    "SLIDER",
    [LLSTRING(AMSOffsetAltitude_Name), LLSTRING(AMSOffsetAltitude_Description)],
    "AEE Physiology",
    [1500, 4000, 2500, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Hypoxia ────────────────────────────────────────────────────────────────
[
    QGVAR(HypoxiaRecovery),
    "SLIDER",
    [LLSTRING(HypoxiaRecovery_Name), LLSTRING(HypoxiaRecovery_Description)],
    "AEE Physiology",
    [0, 1, 0.1, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Scent ──────────────────────────────────────────────────────────────────
[
    QGVAR(ScentIntensity),
    "SLIDER",
    [LLSTRING(ScentIntensity_Name), LLSTRING(ScentIntensity_Description)],
    "AEE Physiology",
    [0, 2, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;
