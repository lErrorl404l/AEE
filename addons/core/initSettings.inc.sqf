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
    "AEE",
    true,   // default: enabled
    true,   // global — needs to be same for all clients
    {}
] call CBA_fnc_addSetting;

// ── Simulation Update ──────────────────────────────────────────────────────
[
    QGVAR(updateInterval),
    "SLIDER",
    [LLSTRING(updateInterval_Name), LLSTRING(updateInterval_Description)],
    "AEE",
    [1, 60, 5, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Temperature ────────────────────────────────────────────────────────────
[
    QGVAR(tempLapseRateEnabled),
    "CHECKBOX",
    [LLSTRING(tempLapseRateEnabled_Name), LLSTRING(tempLapseRateEnabled_Description)],
    ["AEE", "Thermal"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(tempLapseRate),
    "SLIDER",
    [LLSTRING(tempLapseRate_Name), LLSTRING(tempLapseRate_Description)],
    ["AEE", "Thermal"],
    [0, 15, 6.5, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(tempDiurnalEnabled),
    "CHECKBOX",
    [LLSTRING(tempDiurnalEnabled_Name), LLSTRING(tempDiurnalEnabled_Description)],
    ["AEE", "Thermal"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Wind ───────────────────────────────────────────────────────────────────
[
    QGVAR(windEnabled),
    "CHECKBOX",
    [LLSTRING(windEnabled_Name), LLSTRING(windEnabled_Description)],
    ["AEE", "Atmosphere"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(windTerrainInfluence),
    "SLIDER",
    [LLSTRING(windTerrainInfluence_Name), LLSTRING(windTerrainInfluence_Description)],
    ["AEE", "Atmosphere"],
    [0, 1, 0.6, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(windGustFrequency),
    "SLIDER",
    [LLSTRING(windGustFrequency_Name), LLSTRING(windGustFrequency_Description)],
    ["AEE", "Atmosphere"],
    [0, 1, 0.3, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Humidity / Precipitation ───────────────────────────────────────────────
[
    QGVAR(humidityEnabled),
    "CHECKBOX",
    [LLSTRING(humidityEnabled_Name), LLSTRING(humidityEnabled_Description)],
    ["AEE", "Atmosphere"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(precipOrographicEnabled),
    "CHECKBOX",
    [LLSTRING(precipOrographicEnabled_Name), LLSTRING(precipOrographicEnabled_Description)],
    ["AEE", "Atmosphere"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Air Density ────────────────────────────────────────────────────────────
[
    QGVAR(airDensityEnabled),
    "CHECKBOX",
    [LLSTRING(airDensityEnabled_Name), LLSTRING(airDensityEnabled_Description)],
    ["AEE", "Atmosphere"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(icaoReferenceAlt),
    "SLIDER",
    [LLSTRING(icaoReferenceAlt_Name), LLSTRING(icaoReferenceAlt_Description)],
    ["AEE", "Atmosphere"],
    [-500, 5000, 0, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Biome / Köppen ─────────────────────────────────────────────────────────
[
    QGVAR(biomeEnabled),
    "CHECKBOX",
    [LLSTRING(biomeEnabled_Name), LLSTRING(biomeEnabled_Description)],
    ["AEE", "Biome"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(biomeOverride),
    "LIST",
    [LLSTRING(biomeOverride_Name), LLSTRING(biomeOverride_Description)],
    ["AEE", "Biome"],
    [
        ["AUTO","Af","Am","Aw","BSh","BSk","BWk","BWh","Csa","Csb","Cfa","Cfb","Cwa","Dfa","Dfb","Dfc","ET","EF"],
        ["Auto-detect","Af — Tropical Rainforest","Am — Monsoon Tropical","Aw — Tropical Savanna",
         "BSh — Hot Semi-Arid","BSk — Cold Semi-Arid","BWk — Cold Desert","BWh — Hot Desert",
         "Csa — Hot Mediterranean","Csb — Warm Mediterranean","Cfa — Humid Subtropical",
         "Cfb — Oceanic","Cwa — Monsoon Subtropical","Dfa — Hot Continental",
         "Dfb — Humid Continental","Dfc — Subarctic","ET — Tundra","EF — Ice Cap"]
    ],
    0,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(biomeTransitionRadius),
    "SLIDER",
    [LLSTRING(biomeTransitionRadius_Name), LLSTRING(biomeTransitionRadius_Description)],
    ["AEE", "Biome"],
    [500, 50000, 5000, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Terrain Microclimate ───────────────────────────────────────────────────
[
    QGVAR(microclimateRadius),
    "SLIDER",
    [LLSTRING(microclimateRadius_Name), LLSTRING(microclimateRadius_Description)],
    ["AEE", "Microclimate"],
    [10, 2000, 200, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(urbanHeatIsland),
    "SLIDER",
    [LLSTRING(urbanHeatIsland_Name), LLSTRING(urbanHeatIsland_Description)],
    ["AEE", "Microclimate"],
    [0, 1, 0.5, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(waterInfluenceRadius),
    "SLIDER",
    [LLSTRING(waterInfluenceRadius_Name), LLSTRING(waterInfluenceRadius_Description)],
    ["AEE", "Microclimate"],
    [100, 10000, 1000, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Reference Altitude ─────────────────────────────────────────────────────
[
    QGVAR(referenceAltitude),
    "SLIDER",
    [LLSTRING(referenceAltitude_Name), LLSTRING(referenceAltitude_Description)],
    "AEE",
    [-500, 8000, 0, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Clothing Insulation ─────────────────────────────────────────────────────
[
    QGVAR(clothingInsulation),
    "SLIDER",
    [LLSTRING(clothingInsulation_Name), LLSTRING(clothingInsulation_Description)],
    "AEE",
    [0.5, 2.0, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Mud Accretion ──────────────────────────────────────────────────────────
[
    QGVAR(mudAccretionEnabled),
    "CHECKBOX",
    [LLSTRING(mudAccretionEnabled_Name), LLSTRING(mudAccretionEnabled_Description)],
    ["AEE", "Mobility"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Diagnostic ─────────────────────────────────────────────────────────────
[
    QGVAR(diagnostic),
    "CHECKBOX",
    [LLSTRING(diagnostic_Name), LLSTRING(diagnostic_Description)],
    "AEE",
    false,
    false,
    {}
] call CBA_fnc_addSetting;

// ── Radio / Comms ──────────────────────────────────────────────────────────
[
    QGVAR(radioPropagationEnabled),
    "CHECKBOX",
    [LLSTRING(radioPropagationEnabled_Name), LLSTRING(radioPropagationEnabled_Description)],
    ["AEE", "Radio"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Vehicle Performance ─────────────────────────────────────────────────────
[
    QGVAR(enginePowerDegradationEnabled),
    "CHECKBOX",
    [LLSTRING(enginePowerDegradationEnabled_Name), LLSTRING(enginePowerDegradationEnabled_Description)],
    ["AEE", "Mobility"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Optics / Visibility ─────────────────────────────────────────────────────
[
    QGVAR(opticsEnabled),
    "CHECKBOX",
    [LLSTRING(opticsEnabled_Name), LLSTRING(opticsEnabled_Description)],
    ["AEE", "Optics"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Ground / Hydrology ──────────────────────────────────────────────────────
[
    QGVAR(hydrologyEnabled),
    "CHECKBOX",
    [LLSTRING(hydrologyEnabled_Name), LLSTRING(hydrologyEnabled_Description)],
    ["AEE", "Environmental"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Atmospheric Events ──────────────────────────────────────────────────────
[
    QGVAR(atmosphericEventsEnabled),
    "CHECKBOX",
    [LLSTRING(atmosphericEventsEnabled_Name), LLSTRING(atmosphericEventsEnabled_Description)],
    ["AEE", "Atmos"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Environmental / Seasonal ────────────────────────────────────────────────
[
    QGVAR(environmentalEnabled),
    "CHECKBOX",
    [LLSTRING(environmentalEnabled_Name), LLSTRING(environmentalEnabled_Description)],
    ["AEE", "Environmental"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Physiology / Heat Stress ────────────────────────────────────────────────
[
    QGVAR(physiologyEnabled),
    "CHECKBOX",
    [LLSTRING(physiologyEnabled_Name), LLSTRING(physiologyEnabled_Description)],
    ["AEE", "Physiology"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Maritime / Sea State ────────────────────────────────────────────────────
[
    QGVAR(maritimeEnabled),
    "CHECKBOX",
    [LLSTRING(maritimeEnabled_Name), LLSTRING(maritimeEnabled_Description)],
    ["AEE", "Maritime"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── FX / Particles / Sounds ─────────────────────────────────────────────────
[
    QGVAR(fxEnabled),
    "CHECKBOX",
    [LLSTRING(fxEnabled_Name), LLSTRING(fxEnabled_Description)],
    ["AEE", "FX"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;
