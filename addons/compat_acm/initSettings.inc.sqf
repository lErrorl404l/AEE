// initSettings.inc.sqf - CBA Settings registration for aee_compat_acm
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// compat_acm stringtable.
//
// The addon has skipWhenMissingDependencies = 1, so these settings appear
// in the CBA menu only when ACM is loaded.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── CBRN ───────────────────────────────────────────────────────────────────
[
    QGVAR(CBRNBasePersistence),
    "SLIDER",
    [LLSTRING(CBRNBasePersistence_Name), LLSTRING(CBRNBasePersistence_Description)],
    "AEE ACM",
    [6, 72, 24, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(CBRNContamThreshold),
    "SLIDER",
    [LLSTRING(CBRNContamThreshold_Name), LLSTRING(CBRNContamThreshold_Description)],
    "AEE ACM",
    [0, 0.1, 0.01, 3],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(CBRNMaxBuildup),
    "SLIDER",
    [LLSTRING(CBRNMaxBuildup_Name), LLSTRING(CBRNMaxBuildup_Description)],
    "AEE ACM",
    [50, 150, 100, 0],
    true,
    {}
] call CBA_fnc_addSetting;
