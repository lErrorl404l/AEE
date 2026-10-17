// initSettings.inc.sqf - CBA Settings registration for aee_magnetism
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// magnetism stringtable.

// ── World Magnetic Model ─────────────────────────────────────────────────
AEE_SETTING_CHECKBOX(wmmExtrapolate,"AEE Magnetism","Compass",true);
AEE_SETTING_CHECKBOX(compassFerrousDeviation,"AEE Magnetism","Compass",true);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_magnetism_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Magnetism",false);
