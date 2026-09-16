// initSettings.inc.sqf — CBA Settings registration for aee_compat_realweather
//
// Included from XEH_preInit.sqf. Titles and descriptions come from the
// compat_realweather stringtable.

// The setting always registers.  The integration function gates on
// weather.json presence at runtime.  Any loadFile check here would log
// "Script weather.json not found" every launch — we do not do that.
[
    QGVAR(enabled),
    "CHECKBOX",
    [LLSTRING(enabled_Name), LLSTRING(enabled_Description)],
    ["AEE", "Compat - Real Weather"],
    false,
    true,
    {}
] call CBA_fnc_addSetting;
