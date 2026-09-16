// initSettings.inc.sqf - CBA Settings registration for aee_compat_tfar
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// compat_tfar stringtable.
//
// The addon has skipWhenMissingDependencies = 1, so these settings appear
// in the CBA menu only when TFAR is loaded.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Signal ─────────────────────────────────────────────────────────────────
[
    QGVAR(signalMultScale),
    "SLIDER",
    [LLSTRING(signalMultScale_Name), LLSTRING(signalMultScale_Description)],
    ["AEE", "Compat - TFAR"],
    [0, 2, 0.6, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(signalMultMin),
    "SLIDER",
    [LLSTRING(signalMultMin_Name), LLSTRING(signalMultMin_Description)],
    ["AEE", "Compat - TFAR"],
    [0.1, 1, 0.3, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(signalMultMax),
    "SLIDER",
    [LLSTRING(signalMultMax_Name), LLSTRING(signalMultMax_Description)],
    ["AEE", "Compat - TFAR"],
    [1, 3, 1.5, 2],
    true,
    {}
] call CBA_fnc_addSetting;
