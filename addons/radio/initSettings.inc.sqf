// initSettings.inc.sqf - CBA Settings registration for aee_radio
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// radio stringtable.

// ── Propagation ────────────────────────────────────────────────────────────
[
    QGVAR(txPower),
    "SLIDER",
    [LLSTRING(txPower_Name), LLSTRING(txPower_Description)],
    ["AEE Radio", "Link"],
    [20, 50, 37, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(propagationRange),
    "SLIDER",
    [LLSTRING(propagationRange_Name), LLSTRING(propagationRange_Description)],
    ["AEE Radio", "Link"],
    [0.5, 3, 2.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;
