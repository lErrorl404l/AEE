// initSettings.inc.sqf - CBA Settings registration for aee_optics
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// optics stringtable.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Optics / Visibility ─────────────────────────────────────────────────────
[
    QGVAR(seeingFXIntensity),
    "SLIDER",
    [LLSTRING(seeingFXIntensity_Name), LLSTRING(seeingFXIntensity_Description)],
    "AEE Optics",
    [0, 0.1, 0.02, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(nightGrainMax),
    "SLIDER",
    [LLSTRING(nightGrainMax_Name), LLSTRING(nightGrainMax_Description)],
    "AEE Optics",
    [0, 1, 0.7, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rainGrainMax),
    "SLIDER",
    [LLSTRING(rainGrainMax_Name), LLSTRING(rainGrainMax_Description)],
    "AEE Optics",
    [0, 1, 0.4, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(fogGrainMax),
    "SLIDER",
    [LLSTRING(fogGrainMax_Name), LLSTRING(fogGrainMax_Description)],
    "AEE Optics",
    [0, 1, 0.15, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(mirageIntensity),
    "SLIDER",
    [LLSTRING(mirageIntensity_Name), LLSTRING(mirageIntensity_Description)],
    "AEE Optics",
    [0, 2, 1.0, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(mirageDensity),
    "SLIDER",
    [LLSTRING(mirageDensity_Name), LLSTRING(mirageDensity_Description)],
    "AEE Optics",
    [0.01, 0.5, 0.08, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(solarGlareIntensity),
    "SLIDER",
    [LLSTRING(solarGlareIntensity_Name), LLSTRING(solarGlareIntensity_Description)],
    "AEE Optics",
    [0, 2, 1.0, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(glareBlurMax),
    "SLIDER",
    [LLSTRING(glareBlurMax_Name), LLSTRING(glareBlurMax_Description)],
    "AEE Optics",
    [0, 1, 0.2, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(heatShimmerIntensity),
    "SLIDER",
    [LLSTRING(heatShimmerIntensity_Name), LLSTRING(heatShimmerIntensity_Description)],
    "AEE Optics",
    [0, 0.2, 0.04, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(dewBlurMax),
    "SLIDER",
    [LLSTRING(dewBlurMax_Name), LLSTRING(dewBlurMax_Description)],
    "AEE Optics",
    [0, 1, 0.4, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(snowBlindnessIntensity),
    "SLIDER",
    [LLSTRING(snowBlindnessIntensity_Name), LLSTRING(snowBlindnessIntensity_Description)],
    "AEE Optics",
    [0, 2, 1.0, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rainBlurScale),
    "SLIDER",
    [LLSTRING(rainBlurScale_Name), LLSTRING(rainBlurScale_Description)],
    "AEE Optics",
    [0, 1, 0.3, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(mirageOnsetTemp),
    "SLIDER",
    [LLSTRING(mirageOnsetTemp_Name), LLSTRING(mirageOnsetTemp_Description)],
    "AEE Optics",
    [20, 50, 35, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(mirageMinSunElev),
    "SLIDER",
    [LLSTRING(mirageMinSunElev_Name), LLSTRING(mirageMinSunElev_Description)],
    "AEE Optics",
    [0, 30, 15, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(smokePersistenceScale),
    "SLIDER",
    [LLSTRING(smokePersistenceScale_Name), LLSTRING(smokePersistenceScale_Description)],
    "AEE Optics",
    [0.2, 3, 1.0, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(snowVisibilityPenalty),
    "SLIDER",
    [LLSTRING(snowVisibilityPenalty_Name), LLSTRING(snowVisibilityPenalty_Description)],
    "AEE Optics",
    [0.3, 1, 0.7, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(vehicleShimmerBase),
    "SLIDER",
    [LLSTRING(vehicleShimmerBase_Name), LLSTRING(vehicleShimmerBase_Description)],
    "AEE Optics",
    [0, 1, 0.3, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(snowBlindnessBase),
    "SLIDER",
    [LLSTRING(snowBlindnessBase_Name), LLSTRING(snowBlindnessBase_Description)],
    "AEE Optics",
    [0, 0.5, 0.1, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(dewAccumRate),
    "SLIDER",
    [LLSTRING(dewAccumRate_Name), LLSTRING(dewAccumRate_Description)],
    "AEE Optics",
    [0, 0.2, 0.05, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(dewDecayRate),
    "SLIDER",
    [LLSTRING(dewDecayRate_Name), LLSTRING(dewDecayRate_Description)],
    "AEE Optics",
    [0, 0.1, 0.02, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rainAccumRate),
    "SLIDER",
    [LLSTRING(rainAccumRate_Name), LLSTRING(rainAccumRate_Description)],
    "AEE Optics",
    [0, 0.05, 0.01, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rainDecayRate),
    "SLIDER",
    [LLSTRING(rainDecayRate_Name), LLSTRING(rainDecayRate_Description)],
    "AEE Optics",
    [0, 0.1, 0.02, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(chromaCap),
    "SLIDER",
    [LLSTRING(chromaCap_Name), LLSTRING(chromaCap_Description)],
    "AEE Optics",
    [0, 0.2, 0.06, 0],
    true,
    {}
] call CBA_fnc_addSetting;
