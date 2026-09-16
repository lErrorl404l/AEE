// initSettings.inc.sqf - CBA Settings registration for aee_compat_acre2
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// compat_acre2 stringtable.
//
// The addon has skipWhenMissingDependencies = 1, so these settings appear
// in the CBA menu only when ACRE2 is loaded.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Signal ─────────────────────────────────────────────────────────────────
[
    QGVAR(signalDBShift),
    "SLIDER",
    [LLSTRING(signalDBShift_Name), LLSTRING(signalDBShift_Description)],
    ["AEE", "Compat - ACRE2"],
    [0, 20, 8, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(signalSensitivityMin),
    "SLIDER",
    [LLSTRING(signalSensitivityMin_Name), LLSTRING(signalSensitivityMin_Description)],
    ["AEE", "Compat - ACRE2"],
    [-130, -90, -110, 0],
    true,
    {}
] call CBA_fnc_addSetting;
