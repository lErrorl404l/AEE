// initSettings.inc.sqf — CBA Settings registration for aee_core
//
// Included from XEH_preInit.sqf.  Each setting maps to a CfgSettings(CBA)
// entry in config.cpp which supplies the compile-time default and metadata
// for the CBA Settings UI.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Master ─────────────────────────────────────────────────────────────────
[
    QGVAR(enabled),
    "CHECKBOX",
    ["Enable AEE Core", "Master switch for the AEE environment simulation module"],
    "AEE Core",
    true,   // default: enabled
    true,   // global — needs to be same for all clients
    {}
] call CBA_Settings_fnc_init;

// ── Simulation Update ──────────────────────────────────────────────────────
[
    QGVAR(updateInterval),
    "SLIDER",
    ["Update Interval", "Simulation update interval in seconds (lower = more frequent updates)"],
    "AEE Core",
    [1, 60, 5, 0],
    true,
    {}
] call CBA_Settings_fnc_init;

// ── Temperature ────────────────────────────────────────────────────────────
[
    QGVAR(tempLapseRateEnabled),
    "CHECKBOX",
    ["Enable Lapse Rate", "Enable elevation-based temperature lapse rate (standard atmosphere ~6.5 °C/km)"],
    "AEE Core — Temperature",
    true,
    true,
    {}
] call CBA_Settings_fnc_init;

[
    QGVAR(tempLapseRate),
    "SLIDER",
    ["Lapse Rate", "Temperature lapse rate in °C per 1000 m (default: 6.5 °C/km, ICAO standard)"],
    "AEE Core — Temperature",
    [0, 15, 6.5, 1],
    true,
    {}
] call CBA_Settings_fnc_init;

[
    QGVAR(tempDiurnalEnabled),
    "CHECKBOX",
    ["Enable Diurnal Cycle", "Enable diurnal temperature variation based on solar elevation angle"],
    "AEE Core — Temperature",
    true,
    true,
    {}
] call CBA_Settings_fnc_init;

// ── Wind ───────────────────────────────────────────────────────────────────
[
    QGVAR(windEnabled),
    "CHECKBOX",
    ["Enable Wind Simulation", "Enable dynamic wind simulation with terrain and thermal influences"],
    "AEE Core — Wind",
    true,
    true,
    {}
] call CBA_Settings_fnc_init;

[
    QGVAR(windTerrainInfluence),
    "SLIDER",
    ["Terrain Wind Influence", "Strength of terrain (ridge channelling, valley funnelling) on wind vectors (0..1)"],
    "AEE Core — Wind",
    [0, 1, 0.6, 1],
    true,
    {}
] call CBA_Settings_fnc_init;

[
    QGVAR(windGustFrequency),
    "SLIDER",
    ["Gust Frequency", "Relative frequency of gust events (0 = calm, 1 = very gusty)"],
    "AEE Core — Wind",
    [0, 1, 0.3, 1],
    true,
    {}
] call CBA_Settings_fnc_init;

// ── Humidity / Precipitation ───────────────────────────────────────────────
[
    QGVAR(humidityEnabled),
    "CHECKBOX",
    ["Enable Humidity Simulation", "Enable relative-humidity tracking and condensation/precipitation calculations"],
    "AEE Core — Humidity",
    true,
    true,
    {}
] call CBA_Settings_fnc_init;

[
    QGVAR(precipOrographicEnabled),
    "CHECKBOX",
    ["Enable Orographic Precipitation", "Enable orographic-lifting precipitation enhancement on windward slopes"],
    "AEE Core — Humidity",
    true,
    true,
    {}
] call CBA_Settings_fnc_init;

// ── Air Density ────────────────────────────────────────────────────────────
[
    QGVAR(airDensityEnabled),
    "CHECKBOX",
    ["Enable True Air Density", "Calculate density altitude and true air density using temperature, pressure, and humidity corrections"],
    "AEE Core — Air Density",
    true,
    true,
    {}
] call CBA_Settings_fnc_init;

[
    QGVAR(icaoReferenceAlt),
    "SLIDER",
    ["ICAO Reference Altitude", "Reference altitude (m MSL) for the ICAO standard atmosphere baseline"],
    "AEE Core — Air Density",
    [-500, 5000, 0, 0],
    true,
    {}
] call CBA_Settings_fnc_init;

// ── Biome / Köppen ─────────────────────────────────────────────────────────
[
    QGVAR(biomeEnabled),
    "CHECKBOX",
    ["Enable Köppen Biome Classification", "Use Köppen climate classification to differentiate biome types and their weather characteristics"],
    "AEE Core — Biome",
    true,
    true,
    {}
] call CBA_Settings_fnc_init;

[
    QGVAR(biomeTransitionRadius),
    "SLIDER",
    ["Biome Transition Radius", "Smoothing radius (m) for biome boundary transitions to avoid hard climatic edges"],
    "AEE Core — Biome",
    [500, 50000, 5000, 0],
    true,
    {}
] call CBA_Settings_fnc_init;

// ── Terrain Microclimate ───────────────────────────────────────────────────
[
    QGVAR(microclimateRadius),
    "SLIDER",
    ["Microclimate Radius", "Radius (m) for local terrain and vegetation microclimate effects (valley cool-air pooling, forest canopy)"],
    "AEE Core — Microclimate",
    [10, 2000, 200, 0],
    true,
    {}
] call CBA_Settings_fnc_init;

[
    QGVAR(urbanHeatIsland),
    "SLIDER",
    ["Urban Heat Island Effect", "Magnitude of urban heat-island temperature boost in built-up areas (0 = none, 1 = full)"],
    "AEE Core — Microclimate",
    [0, 1, 0.5, 1],
    true,
    {}
] call CBA_Settings_fnc_init;

[
    QGVAR(waterInfluenceRadius),
    "SLIDER",
    ["Water Body Influence Radius", "Radius (m) over which large water bodies moderate local temperature and humidity"],
    "AEE Core — Microclimate",
    [100, 10000, 1000, 0],
    true,
    {}
] call CBA_Settings_fnc_init;

// ── Reference Altitude ─────────────────────────────────────────────────────
[
    QGVAR(referenceAltitude),
    "SLIDER",
    ["Reference Altitude", "Override reference altitude (m MSL) for station pressure calculations. 0 = auto-detect from unit position"],
    "AEE Core",
    [-500, 8000, 0, 0],
    true,
    {}
] call CBA_Settings_fnc_init;

// ── Diagnostic ─────────────────────────────────────────────────────────────
[
    QGVAR(diagnostic),
    "CHECKBOX",
    ["Diagnostic Logging", "Enable verbose diagnostic logging (diag_log) for environment state changes"],
    "AEE Core",
    false,
    true,
    {}
] call CBA_Settings_fnc_init;
