// initSettings.inc.sqf - CBA Settings registration for aee_maritime
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// maritime stringtable.

// ── Tide ───────────────────────────────────────────────────────────────────
[
    QGVAR(tideAmplitude),
    "SLIDER",
    [LLSTRING(tideAmplitude_Name), LLSTRING(tideAmplitude_Description)],
    "AEE Maritime",
    [0.5, 5, 2.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Sea state ──────────────────────────────────────────────────────────────
[
    QGVAR(seaStateResponse),
    "SLIDER",
    [LLSTRING(seaStateResponse_Name), LLSTRING(seaStateResponse_Description)],
    "AEE Maritime",
    [0.1, 0.9, 0.3, 2],
    true,
    {}
] call CBA_fnc_addSetting;
