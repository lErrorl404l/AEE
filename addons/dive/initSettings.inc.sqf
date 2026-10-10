// initSettings.inc.sqf - CBA Settings registration for aee_dive
//
// Included from XEH_preInit.sqf.  The diving knobs moved here from
// aee_physiology and took the aee_dive_* names (ADR-032).

// ── Diving (ZH-L16C, issue #118) ─────────────────────────────────────────
[
    QGVAR(diveEnabled),
    "CHECKBOX",
    [LLSTRING(DiveEnabled_Name), LLSTRING(DiveEnabled_Description)],
    ["AEE Dive", "Diving"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(diveGradientFactor),
    "SLIDER",
    [LLSTRING(DiveGradientFactor_Name), LLSTRING(DiveGradientFactor_Description)],
    ["AEE Dive", "Diving"],
    [0.5, 1.0, 1.0, 2],
    true,
    {}
] call CBA_fnc_addSetting;

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Dive",false);
