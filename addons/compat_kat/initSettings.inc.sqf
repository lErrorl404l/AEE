// initSettings.inc.sqf - CBA Settings registration for aee_compat_kat
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// compat_kat stringtable.
//
// The addon has skipWhenMissingDependencies = 1, so these settings appear
// in the CBA menu only when KAT is loaded.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Circulation ────────────────────────────────────────────────────────────
[
    QGVAR(fluidDrainBase),
    "SLIDER",
    [LLSTRING(fluidDrainBase_Name), LLSTRING(fluidDrainBase_Description)],
    ["AEE", "Compat - KAT"],
    [0, 0.2, 0.05, 3],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Hypoxia ────────────────────────────────────────────────────────────────
[
    QGVAR(spo2RiskScale),
    "SLIDER",
    [LLSTRING(spo2RiskScale_Name), LLSTRING(spo2RiskScale_Description)],
    ["AEE", "Compat - KAT"],
    [10, 50, 32, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(spo2Floor),
    "SLIDER",
    [LLSTRING(spo2Floor_Name), LLSTRING(spo2Floor_Description)],
    ["AEE", "Compat - KAT"],
    [50, 90, 60, 0],
    true,
    {}
] call CBA_fnc_addSetting;
