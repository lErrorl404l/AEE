#include "script_component.hpp"

class CfgPatches {
    class ADDON {
        name = COMPONENT_NAME;
        units[] = {};
        weapons[] = {};
        requiredVersion = REQUIRED_VERSION;
        requiredAddons[] = {
            "aee_main",
            "A3_Data_F",
            "cba_main",
            "cba_xeh"
        };
        author = "AEE Team";
        authors[] = {"AEE Team"};
        url = "https://github.com/AEE-Dev-Team/aee";
        VERSION_CONFIG;
    };
};

class CfgFunctions {
    class aee {
        class ADDON {
            file = QPATHTO_FOLDER(PATHTOF(XEH_preInit.sqf));
            preInit = 1;
            postInit = 1;
            recompile = RECOMPILE;
        };
    };
};

// ─── CBA Settings ──────────────────────────────────────────────────────────
// Settings are registered on the CfgSettings(CBA) X-config tree for
// addonBuilder / description.ext inheritance.  The run-time registration in
// XEH_preInit.sqf (via initSettings.inc.sqf) is authoritative; the entries
// here provide the compile-time defaults and metadata for in-game UI.
//
// Section reference: ACE3 CBA Settings table (§8)

class CfgSettings {
    class CBA {
        class X {
            // ── Master ─────────────────────────────────────────────────────
            class GVAR(enabled) {
                displayName = "Enable AEE Core";
                description = "Master switch for the AEE environment simulation module";
                typeName = "BOOL";
                defaultValue = 1;
            };

            // ── Simulation Update ──────────────────────────────────────────
            class GVAR(updateInterval) {
                displayName = "Update Interval";
                description = "Simulation update interval in seconds (lower = more frequent updates)";
                typeName = "SCALAR";
                defaultValue = 5;
            };

            // ── Temperature ────────────────────────────────────────────────
            class GVAR(tempLapseRateEnabled) {
                displayName = "Enable Lapse Rate";
                description = "Enable elevation-based temperature lapse rate (standard atmosphere ~6.5 °C/km)";
                typeName = "BOOL";
                defaultValue = 1;
            };

            class GVAR(tempLapseRate) {
                displayName = "Lapse Rate";
                description = "Temperature lapse rate in °C per 1000 m (default: 6.5 °C/km, ICAO standard)";
                typeName = "SCALAR";
                defaultValue = 6.5;
            };

            class GVAR(tempDiurnalEnabled) {
                displayName = "Enable Diurnal Cycle";
                description = "Enable diurnal temperature variation based on solar elevation angle";
                typeName = "BOOL";
                defaultValue = 1;
            };

            // ── Wind ───────────────────────────────────────────────────────
            class GVAR(windEnabled) {
                displayName = "Enable Wind Simulation";
                description = "Enable dynamic wind simulation with terrain and thermal influences";
                typeName = "BOOL";
                defaultValue = 1;
            };

            class GVAR(windTerrainInfluence) {
                displayName = "Terrain Wind Influence";
                description = "Strength of terrain (ridge channelling, valley funnelling) on wind vectors (0..1)";
                typeName = "SCALAR";
                defaultValue = 0.6;
            };

            class GVAR(windGustFrequency) {
                displayName = "Gust Frequency";
                description = "Relative frequency of gust events (0 = calm, 1 = very gusty)";
                typeName = "SCALAR";
                defaultValue = 0.3;
            };

            // ── Humidity / Precipitation ───────────────────────────────────
            class GVAR(humidityEnabled) {
                displayName = "Enable Humidity Simulation";
                description = "Enable relative-humidity tracking and condensation/precipitation calculations";
                typeName = "BOOL";
                defaultValue = 1;
            };

            class GVAR(precipOrographicEnabled) {
                displayName = "Enable Orographic Precipitation";
                description = "Enable orographic-lifting precipitation enhancement on windward slopes";
                typeName = "BOOL";
                defaultValue = 1;
            };

            // ── Air Density ────────────────────────────────────────────────
            class GVAR(airDensityEnabled) {
                displayName = "Enable True Air Density";
                description = "Calculate density altitude and true air density using temperature, pressure, and humidity corrections";
                typeName = "BOOL";
                defaultValue = 1;
            };

            class GVAR(icaoReferenceAlt) {
                displayName = "ICAO Reference Altitude";
                description = "Reference altitude (m MSL) for the ICAO standard atmosphere baseline";
                typeName = "SCALAR";
                defaultValue = 0;
            };

            // ── Biome / Köppen ─────────────────────────────────────────────
            class GVAR(biomeEnabled) {
                displayName = "Enable Köppen Biome Classification";
                description = "Use Köppen climate classification to differentiate biome types and their weather characteristics";
                typeName = "BOOL";
                defaultValue = 1;
            };

            class GVAR(biomeTransitionRadius) {
                displayName = "Biome Transition Radius";
                description = "Smoothing radius (m) for biome boundary transitions to avoid hard climatic edges";
                typeName = "SCALAR";
                defaultValue = 5000;
            };

            // ── Terrain Microclimate ───────────────────────────────────────
            class GVAR(microclimateRadius) {
                displayName = "Microclimate Radius";
                description = "Radius (m) for local terrain and vegetation microclimate effects (valley cool-air pooling, forest canopy)";
                typeName = "SCALAR";
                defaultValue = 200;
            };

            class GVAR(urbanHeatIsland) {
                displayName = "Urban Heat Island Effect";
                description = "Magnitude of urban heat-island temperature boost in built-up areas (0 = none, 1 = full)";
                typeName = "SCALAR";
                defaultValue = 0.5;
            };

            class GVAR(waterInfluenceRadius) {
                displayName = "Water Body Influence Radius";
                description = "Radius (m) over which large water bodies moderate local temperature and humidity";
                typeName = "SCALAR";
                defaultValue = 1000;
            };

            // ── Diagnostic ─────────────────────────────────────────────────
            class GVAR(diagnostic) {
                displayName = "Diagnostic Logging";
                description = "Enable verbose diagnostic logging (diag_log) for environment state changes";
                typeName = "BOOL";
                defaultValue = 0;
            };

            // ── Reference Altitude ─────────────────────────────────────────
            class GVAR(referenceAltitude) {
                displayName = "Reference Altitude";
                description = "Override reference altitude (m MSL) for station pressure calculations. 0 = auto-detect from unit position";
                typeName = "SCALAR";
                defaultValue = 0;
            };
        };
    };
};
