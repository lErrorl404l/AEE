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
    ["AEE", "Core"],
    true,   // default: enabled
    true,   // global — needs to be same for all clients
    {}
] call CBA_fnc_addSetting;

// ── Simulation Update ──────────────────────────────────────────────────────
AEE_SETTING_SLIDER(updateInterval,"AEE","Core",1,60,5,0);

// ── Temperature ────────────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(tempLapseRateEnabled,"AEE","Thermal",true);

AEE_SETTING_SLIDER(tempLapseRate,"AEE","Thermal",0,15,6.5,1);

AEE_SETTING_CHECKBOX(tempDiurnalEnabled,"AEE","Thermal",true);

// ── Wind ───────────────────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(windEnabled,"AEE","Atmosphere",true);

AEE_SETTING_SLIDER(windTerrainInfluence,"AEE","Atmosphere",0,1,0.6,1);

AEE_SETTING_SLIDER(windGustFrequency,"AEE","Atmosphere",0,1,0.3,1);

// ── Humidity / Precipitation ───────────────────────────────────────────────
AEE_SETTING_CHECKBOX(humidityEnabled,"AEE","Atmosphere",true);

AEE_SETTING_CHECKBOX(precipOrographicEnabled,"AEE","Atmosphere",true);

// ── Air Density ────────────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(airDensityEnabled,"AEE","Atmosphere",true);

AEE_SETTING_SLIDER(icaoReferenceAlt,"AEE","Atmosphere",-500,5000,0,0);

// ── Biome / Köppen ─────────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(biomeEnabled,"AEE","Biome",true);

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

AEE_SETTING_SLIDER(biomeTransitionRadius,"AEE","Biome",500,50000,5000,0);

// ── Terrain Microclimate ───────────────────────────────────────────────────
AEE_SETTING_SLIDER(microclimateRadius,"AEE","Microclimate",10,2000,200,0);

AEE_SETTING_SLIDER(urbanHeatIsland,"AEE","Microclimate",0,1,0.5,1);

AEE_SETTING_SLIDER(waterInfluenceRadius,"AEE","Microclimate",100,10000,1000,0);

// ── Reference Altitude ─────────────────────────────────────────────────────
AEE_SETTING_SLIDER(referenceAltitude,"AEE","Core",-500,8000,0,0);

// ── Clothing Insulation ─────────────────────────────────────────────────────
AEE_SETTING_SLIDER(clothingInsulation,"AEE","Thermal",0.5,2.0,1.0,1);

// ── Mud Accretion ──────────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(mudAccretionEnabled,"AEE","Mobility",true);

// ── Radio / Comms ──────────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(radioPropagationEnabled,"AEE","Radio",true);

// ── Vehicle Performance ─────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(enginePowerDegradationEnabled,"AEE","Mobility",true);

// ── Optics / Visibility ─────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(opticsEnabled,"AEE","Optics",true);

// ── Ground / Hydrology ──────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(hydrologyEnabled,"AEE","Environmental",true);

// ── Atmospheric Events ──────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(atmosphericEventsEnabled,"AEE","Atmosphere",true);

// ── Nuclear EMP (issue #9) ──────────────────────────────────────────────────
// The EMP event model.  The switch gates the tick and the trigger; with no
// burst triggered (aee_core_fnc_triggerEmp) the model is inert, so the default
// is on and a mission opts in by triggering the event.
AEE_SETTING_CHECKBOX(empEnabled,"AEE","EMP",true);

// ── Environmental / Seasonal ────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(environmentalEnabled,"AEE","Environmental",true);

// ── Physiology / Heat Stress ────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(physiologyEnabled,"AEE","Physiology",true);

// ── Maritime / Sea State ────────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(maritimeEnabled,"AEE","Maritime",true);

// ── FX / Particles / Sounds ─────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(fxEnabled,"AEE","FX",true);

// ── Collision diagnostics (issue #172) ────────────────────────────────────
AEE_SETTING_CHECKBOX(collisionDebug,"AEE Debug","FX",false);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The switch behind AEE_LOG_DEBUG.  Without a declared setting the flag
// could only be set from the debug console, so the DEBUG lines were
// unreachable in practice.  This registers it in the settings UI and sets
// GVAR(logDebug), which the macros read.
[
    QGVAR(logDebug),
    "CHECKBOX",
    [LLSTRING(logDebug_Name), LLSTRING(logDebug_Description)],
    ["AEE Debug", "Core"],
    false,
    true,
    {
        // The macros test both names; keep them in step so a mission that
        // reads aee_core_logDebug sees the same state as the setting.
        missionNamespace setVariable [QGVAR(logDebug), _this];
        missionNamespace setVariable ["aee_core_logDebug", _this];
    }
] call CBA_fnc_addSetting;

// ── Diagnostics: ballistics ───────────────────────────────────────────────
// Per-module switch.  A whole-mod DEBUG stream is unreadable in a firefight,
// so one module can be traced alone.
// ── Diagnostics: physiology and the carried load ──────────────────────────
// ── Diagnostics: effect emitters ──────────────────────────────────────────
// Footfall, rotor wash and the surface dust: the values a headless test
// cannot see, so a client trace needs to print them.

// ── Client scan cadence ───────────────────────────────────────────────────
// The dynamic-light scan walks nearby objects to find lit lamps. It is
// client-only and its result changes only when a lamp toggles or the
// weather attenuates it. 0 scans every tick.
AEE_SETTING_SLIDER(lightScanInterval,"AEE","Core",0,120,30,0);

// ── Work distribution ─────────────────────────────────────────────────────
// Where the environment computation runs. AEE computes identical values on
// every machine by design, with no network traffic, which is what makes it
// scale to a large milsim session. This setting exists for the units that
// cannot take that default: a server with headroom and clients that are
// already frame-limited.
[
    QGVAR(computeMode),
    "LIST",
    [LLSTRING(computeMode_Name), LLSTRING(computeMode_Description)],
    ["AEE", "Core"],
    [
        ["DETERMINISTIC", "SERVER_MAP_ONLY"],
        [
            "Deterministic (recommended: no network, every machine computes)",
            "Server map facts only (one terrain sweep shared, position work stays local)"
        ],
        0
    ],
    true,
    {}
] call CBA_fnc_addSetting;
