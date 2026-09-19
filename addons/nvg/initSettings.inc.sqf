// ── NVG battery drain (issue #36) ──────────────────────────────────────────
// Opt-in: battery drain + temperature derating is hardcore (battery dies
// mid-op), so it defaults OFF.  When enabled, the drain rate is scaled
// by the physiology battery temperature derating.
[
    QGVAR(nvgBatteryEnabled),
    "CHECKBOX",
    [LLSTRING(nvgBatteryEnabled_Name), LLSTRING(nvgBatteryEnabled_Description)],
    ["AEE NVG", "Intensity"],
    false,
    true,
    {}
] call CBA_fnc_addSetting;
