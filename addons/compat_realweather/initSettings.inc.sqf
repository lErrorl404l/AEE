// initSettings.inc.sqf — CBA Settings registration for aee_compat_realweather
//
// Included from XEH_preInit.sqf. Titles and descriptions come from the
// compat_realweather stringtable.

[
    QGVAR(enabled),
    "CHECKBOX",
    [LLSTRING(enabled_Name), LLSTRING(enabled_Description)],
    "AEE Real Weather",
    false,
    true,
    {}
] call CBA_fnc_addSetting;
