// initSettings.inc.sqf - CBA Settings registration for aee_compat_ace3
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// compat_ace3 stringtable.
//
// The addon has skipWhenMissingDependencies = 1, so these settings appear
// in the CBA menu only when ACE3 is loaded.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Medical ────────────────────────────────────────────────────────────────
[
    QGVAR(medicalWBGTThreshold),
    "SLIDER",
    [LLSTRING(medicalWBGTThreshold_Name), LLSTRING(medicalWBGTThreshold_Description)],
    "AEE ACE3",
    [18, 35, 23, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(medicalRiskThreshold),
    "SLIDER",
    [LLSTRING(medicalRiskThreshold_Name), LLSTRING(medicalRiskThreshold_Description)],
    "AEE ACE3",
    [0, 1, 0.3, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(medicalHeatStrokeWBGT),
    "SLIDER",
    [LLSTRING(medicalHeatStrokeWBGT_Name), LLSTRING(medicalHeatStrokeWBGT_Description)],
    "AEE ACE3",
    [25, 45, 32, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(medicalBurnTemp),
    "SLIDER",
    [LLSTRING(medicalBurnTemp_Name), LLSTRING(medicalBurnTemp_Description)],
    "AEE ACE3",
    [20, 45, 25, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(medicalBurnDamageScale),
    "SLIDER",
    [LLSTRING(medicalBurnDamageScale_Name), LLSTRING(medicalBurnDamageScale_Description)],
    "AEE ACE3",
    [0, 0.01, 0.0005, 4],
    true,
    {}
] call CBA_fnc_addSetting;
