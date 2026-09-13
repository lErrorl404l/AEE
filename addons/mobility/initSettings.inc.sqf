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

// ── Traction ────────────────────────────────────────────────────────────────
[
    QGVAR(mudAccretionRate),
    "SLIDER",
    [LLSTRING(mudAccretionRate_Name), LLSTRING(mudAccretionRate_Description)],
    "AEE Mobility",
    [0, 0.02, 0.002, 3],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(mudDecayRate),
    "SLIDER",
    [LLSTRING(mudDecayRate_Name), LLSTRING(mudDecayRate_Description)],
    "AEE Mobility",
    [0.9, 1, 0.99, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(tractionScale),
    "SLIDER",
    [LLSTRING(tractionScale_Name), LLSTRING(tractionScale_Description)],
    "AEE Mobility",
    [0.5, 1.5, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Vehicle Performance ─────────────────────────────────────────────────────
[
    QGVAR(minEnginePower),
    "SLIDER",
    [LLSTRING(minEnginePower_Name), LLSTRING(minEnginePower_Description)],
    "AEE Mobility",
    [0.1, 0.8, 0.3, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Environment ─────────────────────────────────────────────────────────────
[
    QGVAR(routeRecoveryRate),
    "SLIDER",
    [LLSTRING(routeRecoveryRate_Name), LLSTRING(routeRecoveryRate_Description)],
    "AEE Mobility",
    [1, 1.01, 1.001, 3],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(routeDamageRate),
    "SLIDER",
    [LLSTRING(routeDamageRate_Name), LLSTRING(routeDamageRate_Description)],
    "AEE Mobility",
    [0, 0.0001, 0.00002, 5],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(riverResponseRate),
    "SLIDER",
    [LLSTRING(riverResponseRate_Name), LLSTRING(riverResponseRate_Description)],
    "AEE Mobility",
    [0.01, 0.5, 0.1, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rainAccumDecay),
    "SLIDER",
    [LLSTRING(rainAccumDecay_Name), LLSTRING(rainAccumDecay_Description)],
    "AEE Mobility",
    [0.9, 1, 0.97, 2],
    true,
    {}
] call CBA_fnc_addSetting;
