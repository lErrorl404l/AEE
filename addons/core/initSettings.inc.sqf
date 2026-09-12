// initSettings.inc.sqf - CBA Settings registration for aee_core
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// core stringtable.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Master ─────────────────────────────────────────────────────────────────
[
    QGVAR(enabled),
    "CHECKBOX",
    [LLSTRING(enabled_Name), LLSTRING(enabled_Description)],
    "AEE Core",
    true,   // default: enabled
    true,   // global — needs to be same for all clients
    {}
] call CBA_fnc_addSetting;

// ── Simulation Update ──────────────────────────────────────────────────────
[
    QGVAR(updateInterval),
    "SLIDER",
    [LLSTRING(updateInterval_Name), LLSTRING(updateInterval_Description)],
    "AEE Core",
    [1, 60, 5, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Temperature ────────────────────────────────────────────────────────────
[
    QGVAR(tempLapseRateEnabled),
    "CHECKBOX",
    [LLSTRING(tempLapseRateEnabled_Name), LLSTRING(tempLapseRateEnabled_Description)],
    ["AEE Core", "Temperature"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(tempLapseRate),
    "SLIDER",
    [LLSTRING(tempLapseRate_Name), LLSTRING(tempLapseRate_Description)],
    ["AEE Core", "Temperature"],
    [0, 15, 6.5, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(tempDiurnalEnabled),
    "CHECKBOX",
    [LLSTRING(tempDiurnalEnabled_Name), LLSTRING(tempDiurnalEnabled_Description)],
    ["AEE Core", "Temperature"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Wind ───────────────────────────────────────────────────────────────────
[
    QGVAR(windEnabled),
    "CHECKBOX",
    [LLSTRING(windEnabled_Name), LLSTRING(windEnabled_Description)],
    ["AEE Core", "Wind"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(windTerrainInfluence),
    "SLIDER",
    [LLSTRING(windTerrainInfluence_Name), LLSTRING(windTerrainInfluence_Description)],
    ["AEE Core", "Wind"],
    [0, 1, 0.6, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(windGustFrequency),
    "SLIDER",
    [LLSTRING(windGustFrequency_Name), LLSTRING(windGustFrequency_Description)],
    ["AEE Core", "Wind"],
    [0, 1, 0.3, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Humidity / Precipitation ───────────────────────────────────────────────
[
    QGVAR(humidityEnabled),
    "CHECKBOX",
    [LLSTRING(humidityEnabled_Name), LLSTRING(humidityEnabled_Description)],
    ["AEE Core", "Humidity"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(precipOrographicEnabled),
    "CHECKBOX",
    [LLSTRING(precipOrographicEnabled_Name), LLSTRING(precipOrographicEnabled_Description)],
    ["AEE Core", "Humidity"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Air Density ────────────────────────────────────────────────────────────
[
    QGVAR(airDensityEnabled),
    "CHECKBOX",
    [LLSTRING(airDensityEnabled_Name), LLSTRING(airDensityEnabled_Description)],
    ["AEE Core", "Air Density"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(icaoReferenceAlt),
    "SLIDER",
    [LLSTRING(icaoReferenceAlt_Name), LLSTRING(icaoReferenceAlt_Description)],
    ["AEE Core", "Air Density"],
    [-500, 5000, 0, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Biome / Köppen ─────────────────────────────────────────────────────────
[
    QGVAR(biomeEnabled),
    "CHECKBOX",
    [LLSTRING(biomeEnabled_Name), LLSTRING(biomeEnabled_Description)],
    ["AEE Core", "Biome"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(biomeTransitionRadius),
    "SLIDER",
    [LLSTRING(biomeTransitionRadius_Name), LLSTRING(biomeTransitionRadius_Description)],
    ["AEE Core", "Biome"],
    [500, 50000, 5000, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Terrain Microclimate ───────────────────────────────────────────────────
[
    QGVAR(microclimateRadius),
    "SLIDER",
    [LLSTRING(microclimateRadius_Name), LLSTRING(microclimateRadius_Description)],
    ["AEE Core", "Microclimate"],
    [10, 2000, 200, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(urbanHeatIsland),
    "SLIDER",
    [LLSTRING(urbanHeatIsland_Name), LLSTRING(urbanHeatIsland_Description)],
    ["AEE Core", "Microclimate"],
    [0, 1, 0.5, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(waterInfluenceRadius),
    "SLIDER",
    [LLSTRING(waterInfluenceRadius_Name), LLSTRING(waterInfluenceRadius_Description)],
    ["AEE Core", "Microclimate"],
    [100, 10000, 1000, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Reference Altitude ─────────────────────────────────────────────────────
[
    QGVAR(referenceAltitude),
    "SLIDER",
    [LLSTRING(referenceAltitude_Name), LLSTRING(referenceAltitude_Description)],
    "AEE Core",
    [-500, 8000, 0, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Clothing Insulation ─────────────────────────────────────────────────────
[
    QGVAR(clothingInsulation),
    "SLIDER",
    [LLSTRING(clothingInsulation_Name), LLSTRING(clothingInsulation_Description)],
    "AEE Core",
    [0.5, 2.0, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Mud Accretion ──────────────────────────────────────────────────────────
[
    QGVAR(mudAccretionEnabled),
    "CHECKBOX",
    [LLSTRING(mudAccretionEnabled_Name), LLSTRING(mudAccretionEnabled_Description)],
    ["AEE Core", "Mud"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Diagnostic ─────────────────────────────────────────────────────────────
[
    QGVAR(diagnostic),
    "CHECKBOX",
    [LLSTRING(diagnostic_Name), LLSTRING(diagnostic_Description)],
    "AEE Core",
    false,
    false,
    {}
] call CBA_fnc_addSetting;

// ── Radio / Comms ──────────────────────────────────────────────────────────
[
    QGVAR(radioPropagationEnabled),
    "CHECKBOX",
    [LLSTRING(radioPropagationEnabled_Name), LLSTRING(radioPropagationEnabled_Description)],
    ["AEE Core", "Radio / Comms"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Vehicle Performance ─────────────────────────────────────────────────────
[
    QGVAR(enginePowerDegradationEnabled),
    "CHECKBOX",
    [LLSTRING(enginePowerDegradationEnabled_Name), LLSTRING(enginePowerDegradationEnabled_Description)],
    ["AEE Core", "Vehicle Performance"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Optics / Visibility ─────────────────────────────────────────────────────
[
    QGVAR(opticsEnabled),
    "CHECKBOX",
    [LLSTRING(opticsEnabled_Name), LLSTRING(opticsEnabled_Description)],
    ["AEE Core", "Optics / Visibility"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Ground / Hydrology ──────────────────────────────────────────────────────
[
    QGVAR(hydrologyEnabled),
    "CHECKBOX",
    [LLSTRING(hydrologyEnabled_Name), LLSTRING(hydrologyEnabled_Description)],
    ["AEE Core", "Ground / Hydrology"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Atmospheric Events ──────────────────────────────────────────────────────
[
    QGVAR(atmosphericEventsEnabled),
    "CHECKBOX",
    [LLSTRING(atmosphericEventsEnabled_Name), LLSTRING(atmosphericEventsEnabled_Description)],
    ["AEE Core", "Atmospheric Events"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Environmental / Seasonal ────────────────────────────────────────────────
[
    QGVAR(environmentalEnabled),
    "CHECKBOX",
    [LLSTRING(environmentalEnabled_Name), LLSTRING(environmentalEnabled_Description)],
    ["AEE Core", "Environmental"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Physiology / Heat Stress ────────────────────────────────────────────────
[
    QGVAR(physiologyEnabled),
    "CHECKBOX",
    [LLSTRING(physiologyEnabled_Name), LLSTRING(physiologyEnabled_Description)],
    ["AEE Core", "Physiology"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Maritime / Sea State ────────────────────────────────────────────────────
[
    QGVAR(maritimeEnabled),
    "CHECKBOX",
    [LLSTRING(maritimeEnabled_Name), LLSTRING(maritimeEnabled_Description)],
    ["AEE Core", "Maritime"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── FX / Particles / Sounds ─────────────────────────────────────────────────
[
    QGVAR(fxEnabled),
    "CHECKBOX",
    [LLSTRING(fxEnabled_Name), LLSTRING(fxEnabled_Description)],
    ["AEE Core", "FX"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;
