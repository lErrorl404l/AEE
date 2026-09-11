// initSettings.inc.sqf - CBA Settings registration for aee_mobility
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// mobility stringtable.

// ── Flight Turbulence ──────────────────────────────────────────────────────
[
    QGVAR(flightTurbulence),
    "CHECKBOX",
    [LLSTRING(flightTurbulence_Name), LLSTRING(flightTurbulence_Description)],
    "AEE Mobility",
    true,   // default: enabled
    true,   // global — needs to be same for all clients
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(turbulenceScale),
    "SLIDER",
    [LLSTRING(turbulenceScale_Name), LLSTRING(turbulenceScale_Description)],
    "AEE Mobility",
    [0, 3, 1, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(turbulenceRadius),
    "SLIDER",
    [LLSTRING(turbulenceRadius_Name), LLSTRING(turbulenceRadius_Description)],
    "AEE Mobility",
    [500, 5000, 2000, 0],
    true,
    {}
] call CBA_fnc_addSetting;
