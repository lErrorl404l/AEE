// initSettings.inc.sqf — CBA Settings registration for aee_compat_realweather
//
// Included from XEH_preInit.sqf. Titles and descriptions come from the
// compat_realweather stringtable.

// Register the setting only when the mission provides weather.json.
// Without the file the feature cannot operate, so the setting must not
// appear.  loadFile logs a one-line notice when the file is absent;
// that is informative and happens once at preInit.
private _hasFile = (loadFile "weather.json") != "";
if (_hasFile) then {
    [
        QGVAR(enabled),
        "CHECKBOX",
        [LLSTRING(enabled_Name), LLSTRING(enabled_Description)],
        "AEE Real Weather",
        false,
        true,
        {}
    ] call CBA_fnc_addSetting;
};
