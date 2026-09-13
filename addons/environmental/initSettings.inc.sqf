// initSettings.inc.sqf - CBA Settings registration for aee_environmental
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// environmental stringtable.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Frost ──────────────────────────────────────────────────────────────────
[
    QGVAR(FrostAccumRate),
    "SLIDER",
    [LLSTRING(FrostAccumRate_Name), LLSTRING(FrostAccumRate_Description)],
    ["AEE Core", "Environmental"],
    [0, 0.01, 0.001, 3],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(FrostDecayRate),
    "SLIDER",
    [LLSTRING(FrostDecayRate_Name), LLSTRING(FrostDecayRate_Description)],
    ["AEE Core", "Environmental"],
    [0, 0.05, 0.01, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Snow ───────────────────────────────────────────────────────────────────
[
    QGVAR(SnowAccretionRate),
    "SLIDER",
    [LLSTRING(SnowAccretionRate_Name), LLSTRING(SnowAccretionRate_Description)],
    ["AEE Core", "Environmental"],
    [0, 0.1, 0.01, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(MaxSnowDepth),
    "SLIDER",
    [LLSTRING(MaxSnowDepth_Name), LLSTRING(MaxSnowDepth_Description)],
    ["AEE Core", "Environmental"],
    [0.5, 10, 3.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Severe Weather ─────────────────────────────────────────────────────────
[
    QGVAR(SandstormWindThreshold),
    "SLIDER",
    [LLSTRING(SandstormWindThreshold_Name), LLSTRING(SandstormWindThreshold_Description)],
    ["AEE Core", "Environmental"],
    [5, 25, 10, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(BlowingSnowWindThreshold),
    "SLIDER",
    [LLSTRING(BlowingSnowWindThreshold_Name), LLSTRING(BlowingSnowWindThreshold_Description)],
    ["AEE Core", "Environmental"],
    [5, 20, 8, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(DustDevilTempThreshold),
    "SLIDER",
    [LLSTRING(DustDevilTempThreshold_Name), LLSTRING(DustDevilTempThreshold_Description)],
    ["AEE Core", "Environmental"],
    [25, 40, 30, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Hydrology ──────────────────────────────────────────────────────────────
[
    QGVAR(FlashFloodThreshold),
    "SLIDER",
    [LLSTRING(FlashFloodThreshold_Name), LLSTRING(FlashFloodThreshold_Description)],
    ["AEE Core", "Environmental"],
    [20, 100, 50, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(WettingRate),
    "SLIDER",
    [LLSTRING(WettingRate_Name), LLSTRING(WettingRate_Description)],
    ["AEE Core", "Environmental"],
    [0, 0.2, 0.05, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(DewRate),
    "SLIDER",
    [LLSTRING(DewRate_Name), LLSTRING(DewRate_Description)],
    ["AEE Core", "Environmental"],
    [0, 0.1, 0.02, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── CBRN ───────────────────────────────────────────────────────────────────
[
    QGVAR(CBRNBasePersistence),
    "SLIDER",
    [LLSTRING(CBRNBasePersistence_Name), LLSTRING(CBRNBasePersistence_Description)],
    ["AEE Core", "Environmental"],
    [1, 168, 24, 0],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Space Weather ──────────────────────────────────────────────────────────
[
    QGVAR(FlareChance),
    "SLIDER",
    [LLSTRING(FlareChance_Name), LLSTRING(FlareChance_Description)],
    ["AEE Core", "Environmental"],
    [0, 0.2, 0.05, 2],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(FlareDuration),
    "SLIDER",
    [LLSTRING(FlareDuration_Name), LLSTRING(FlareDuration_Description)],
    ["AEE Core", "Environmental"],
    [600, 36000, 10800, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(FlareDecayRate),
    "SLIDER",
    [LLSTRING(FlareDecayRate_Name), LLSTRING(FlareDecayRate_Description)],
    ["AEE Core", "Environmental"],
    [0, 0.2, 0.05, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Sound Propagation ──────────────────────────────────────────────────────
[
    QGVAR(InversionBoost),
    "SLIDER",
    [LLSTRING(InversionBoost_Name), LLSTRING(InversionBoost_Description)],
    ["AEE Core", "Environmental"],
    [0, 1.5, 0.6, 1],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(SoundPropagationScale),
    "SLIDER",
    [LLSTRING(SoundPropagationScale_Name), LLSTRING(SoundPropagationScale_Description)],
    ["AEE Core", "Environmental"],
    [0.5, 2, 1.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;
