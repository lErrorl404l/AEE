// initSettings.inc.sqf - CBA Settings registration for aee_atmos
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// atmos stringtable.

// ── Microburst ─────────────────────────────────────────────────────────────
[
    QGVAR(microburstTempThreshold),
    "SLIDER",
    [LLSTRING(microburstTempThreshold_Name), LLSTRING(microburstTempThreshold_Description)],
    "AEE Atmos",
    [20, 40, 28, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(microburstChance),
    "SLIDER",
    [LLSTRING(microburstChance_Name), LLSTRING(microburstChance_Description)],
    "AEE Atmos",
    [0, 0.1, 0.01, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(microburstDuration),
    "SLIDER",
    [LLSTRING(microburstDuration_Name), LLSTRING(microburstDuration_Description)],
    "AEE Atmos",
    [5, 60, 12, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(microburstGustMax),
    "SLIDER",
    [LLSTRING(microburstGustMax_Name), LLSTRING(microburstGustMax_Description)],
    "AEE Atmos",
    [20, 50, 36, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Lightning ──────────────────────────────────────────────────────────────
[
    QGVAR(lightningConvectionTemp),
    "SLIDER",
    [LLSTRING(lightningConvectionTemp_Name), LLSTRING(lightningConvectionTemp_Description)],
    "AEE Atmos",
    [20, 35, 25, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(lightningStrikeChance),
    "SLIDER",
    [LLSTRING(lightningStrikeChance_Name), LLSTRING(lightningStrikeChance_Description)],
    "AEE Atmos",
    [0, 0.2, 0.05, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Airframe icing ─────────────────────────────────────────────────────────
[
    QGVAR(icingShedRate),
    "SLIDER",
    [LLSTRING(icingShedRate_Name), LLSTRING(icingShedRate_Description)],
    "AEE Atmos",
    [0.5, 1, 0.9, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(maxIceMass),
    "SLIDER",
    [LLSTRING(maxIceMass_Name), LLSTRING(maxIceMass_Description)],
    "AEE Atmos",
    [20, 200, 100, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Fog ────────────────────────────────────────────────────────────────────
[
    QGVAR(radFogRampRate),
    "SLIDER",
    [LLSTRING(radFogRampRate_Name), LLSTRING(radFogRampRate_Description)],
    "AEE Atmos",
    [0, 0.5, 0.1, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(maxFogDensity),
    "SLIDER",
    [LLSTRING(maxFogDensity_Name), LLSTRING(maxFogDensity_Description)],
    "AEE Atmos",
    [0.2, 1, 0.8, 2],
    true,
    {}
] call CBA_fnc_addSetting;
