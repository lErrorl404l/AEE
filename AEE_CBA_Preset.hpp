// AEE CBA Settings Preset
// Balanced defaults for the Ace Environment Extension.
// Place in your mission's description.ext or as a separate CBA preset file.
//
// Generated from the addon's initSettings.inc.sqf and config.cpp.

class AEE_Preset {
    // ── Master ──────────────────────────────────────────────────────────────
    class aee_core_enabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };
    class aee_core_updateInterval {
        value = 5;
        typeName = "SCALAR";
        force = 1;
    };
    class aee_core_referenceAltitude {
        value = 0;
        typeName = "SCALAR";
        force = 1;
    };
    class aee_core_diagnostic {
        value = 0;
        typeName = "BOOL";
        force = 1;
    };

    // ── Temperature ─────────────────────────────────────────────────────────
    class aee_core_tempLapseRateEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };
    class aee_core_tempLapseRate {
        value = 6.5;
        typeName = "SCALAR";
        force = 1;
    };
    class aee_core_tempDiurnalEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };

    // ── Wind ────────────────────────────────────────────────────────────────
    class aee_core_windEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };
    class aee_core_windTerrainInfluence {
        value = 0.6;
        typeName = "SCALAR";
        force = 1;
    };
    class aee_core_windGustFrequency {
        value = 0.3;
        typeName = "SCALAR";
        force = 1;
    };

    // ── Humidity / Precipitation ───────────────────────────────────────────
    class aee_core_humidityEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };
    class aee_core_precipOrographicEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };

    // ── Air Density ────────────────────────────────────────────────────────
    class aee_core_airDensityEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };
    class aee_core_icaoReferenceAlt {
        value = 0;
        typeName = "SCALAR";
        force = 1;
    };

    // ── Biome / Koppen ─────────────────────────────────────────────────────
    class aee_core_biomeEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };
    class aee_core_biomeTransitionRadius {
        value = 5000;
        typeName = "SCALAR";
        force = 1;
    };

    // ── Microclimate ────────────────────────────────────────────────────────
    class aee_core_microclimateRadius {
        value = 200;
        typeName = "SCALAR";
        force = 1;
    };
    class aee_core_urbanHeatIsland {
        value = 0.5;
        typeName = "SCALAR";
        force = 1;
    };
    class aee_core_waterInfluenceRadius {
        value = 1000;
        typeName = "SCALAR";
        force = 1;
    };

    // ── Radio / Comms ──────────────────────────────────────────────────────
    class aee_core_radioPropagationEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };

    // ── Vehicle Performance ────────────────────────────────────────────────
    class aee_core_enginePowerDegradationEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };

    // ── Optics / Visibility ────────────────────────────────────────────────
    class aee_core_opticsEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };

    // ── Ground / Hydrology ─────────────────────────────────────────────────
    class aee_core_hydrologyEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };

    // ── Atmospheric Events ─────────────────────────────────────────────────
    class aee_core_atmosphericEventsEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };

    // ── Environmental / Seasonal ────────────────────────────────────────────
    class aee_core_environmentalEnabled {
        value = 1;
        typeName = "BOOL";
        force = 1;
    };
};
