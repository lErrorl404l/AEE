// initSettings.inc.sqf - CBA Settings registration for aee_altitude
//
// Included from XEH_preInit.sqf.  The altitude, hypoxia and G-LOC knobs
// moved here from aee_physiology and took the aee_altitude_* names
// (ADR-032).

// ── Altitude ───────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(RapidAscentThreshold,"AEE Altitude","Thresholds",50,500,150,0);

AEE_SETTING_SLIDER(AMSOffsetAltitude,"AEE Altitude","Thresholds",1500,4000,2500,0);

// ── Hypoxia ────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(HypoxiaRecovery,"AEE Altitude","Rates",0,1,0.1,1);

// ── G-LOC and altitude physiology (issue #135) ─────────────────────────────
[
    QGVAR(glocEnabled),
    "CHECKBOX",
    [LLSTRING(GlocEnabled_Name), LLSTRING(GlocEnabled_Description)],
    ["AEE Altitude", "G-LOC"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(agsmAvailable),
    "CHECKBOX",
    [LLSTRING(AGSM_Name), LLSTRING(AGSM_Description)],
    ["AEE Altitude", "G-LOC"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(gsuitEquipped),
    "CHECKBOX",
    [LLSTRING(GSuit_Name), LLSTRING(GSuit_Description)],
    ["AEE Altitude", "G-LOC"],
    false,
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(seatReclined),
    "CHECKBOX",
    [LLSTRING(SeatReclined_Name), LLSTRING(SeatReclined_Description)],
    ["AEE Altitude", "G-LOC"],
    false,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Altitude",false);
