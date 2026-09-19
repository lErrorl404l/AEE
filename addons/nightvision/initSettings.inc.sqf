// ── NVG battery drain (issue #36) ──────────────────────────────────────────
// Opt-in: battery drain + temperature derating is hardcore (battery dies
// mid-op), so it defaults OFF.  When enabled, the drain rate is scaled
// by the physiology battery temperature derating.
[
    QGVAR(nvgBatteryEnabled),
    "CHECKBOX",
    [LLSTRING(nvgBatteryEnabled_Name), LLSTRING(nvgBatteryEnabled_Description)],
    ["AEE Night Vision", "Intensity"],
    false,
    true,
    {}
] call CBA_fnc_addSetting;

// ── NVG grain maximum (issue #203) ─────────────────────────────────────────
// Grain intensity ceilings by condition.  Moved here from aee_optics so the
// nightvision module is self-contained (standalone-distributable).
[
    QGVAR(nightGrainMax),
    "SLIDER",
    [LLSTRING(nightGrainMax_Name), LLSTRING(nightGrainMax_Description)],
    ["AEE Night Vision", "Intensity"],
    [0, 1, 0.7, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(rainGrainMax),
    "SLIDER",
    [LLSTRING(rainGrainMax_Name), LLSTRING(rainGrainMax_Description)],
    ["AEE Night Vision", "Intensity"],
    [0, 1, 0.4, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(fogGrainMax),
    "SLIDER",
    [LLSTRING(fogGrainMax_Name), LLSTRING(fogGrainMax_Description)],
    ["AEE Night Vision", "Intensity"],
    [0, 1, 0.15, 0],
    true,
    {}
] call CBA_fnc_addSetting;
