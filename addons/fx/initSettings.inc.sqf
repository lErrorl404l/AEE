// initSettings.inc.sqf - CBA Settings registration for aee_fx
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// fx stringtable.

// ── Vehicle Dust ────────────────────────────────────────────────────────────
[
    QGVAR(vehicleDustIntensity),
    "SLIDER",
    [LLSTRING(vehicleDustIntensity_Name), LLSTRING(vehicleDustIntensity_Description)],
    ["AEE FX", "Particles"],
    [0, 2, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(vehicleDustDensity),
    "SLIDER",
    [LLSTRING(vehicleDustDensity_Name), LLSTRING(vehicleDustDensity_Description)],
    ["AEE FX", "Particles"],
    [0.01, 0.2, 0.08, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Rain ────────────────────────────────────────────────────────────────────
[
    QGVAR(rainDropDensity),
    "SLIDER",
    [LLSTRING(rainDropDensity_Name), LLSTRING(rainDropDensity_Description)],
    ["AEE FX", "Particles"],
    [0.001, 0.02, 0.006, 3],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rainVehicleSoundVolume),
    "SLIDER",
    [LLSTRING(rainVehicleSoundVolume_Name), LLSTRING(rainVehicleSoundVolume_Description)],
    ["AEE FX", "Sound"],
    [0, 2, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Atmospheric Dust ────────────────────────────────────────────────────────
[
    QGVAR(atmosphericDustIntensity),
    "SLIDER",
    [LLSTRING(atmosphericDustIntensity_Name), LLSTRING(atmosphericDustIntensity_Description)],
    ["AEE FX", "Particles"],
    [0, 0.5, 0.08, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Lightning / Thunder ─────────────────────────────────────────────────────
[
    QGVAR(lightningFXChance),
    "SLIDER",
    [LLSTRING(lightningFXChance_Name), LLSTRING(lightningFXChance_Description)],
    ["AEE FX", "Events"],
    [0, 0.2, 0.05, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(lightningBrightness),
    "SLIDER",
    [LLSTRING(lightningBrightness_Name), LLSTRING(lightningBrightness_Description)],
    ["AEE FX", "Events"],
    [100, 5000, 1000, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(thunderVolume),
    "SLIDER",
    [LLSTRING(thunderVolume_Name), LLSTRING(thunderVolume_Description)],
    ["AEE FX", "Sound"],
    [0, 10, 3.5, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(lightningIgnitionChance),
    "SLIDER",
    [LLSTRING(lightningIgnitionChance_Name), LLSTRING(lightningIgnitionChance_Description)],
    ["AEE FX", "Events"],
    [0, 0.5, 0.1, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Wind / Severe Weather ───────────────────────────────────────────────────
[
    QGVAR(windNoiseVolume),
    "SLIDER",
    [LLSTRING(windNoiseVolume_Name), LLSTRING(windNoiseVolume_Description)],
    ["AEE FX", "Sound"],
    [0, 2, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(severeWeatherBlur),
    "SLIDER",
    [LLSTRING(severeWeatherBlur_Name), LLSTRING(severeWeatherBlur_Description)],
    ["AEE FX", "Events"],
    [0, 2, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;
