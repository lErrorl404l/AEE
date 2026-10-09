// initSettings.inc.sqf - CBA Settings registration for aee_magnetism
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// magnetism stringtable.

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_magnetism_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Magnetism",false);