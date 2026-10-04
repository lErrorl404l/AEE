// initSettings.inc.sqf — CBA Settings registration for aee_compat_realweather
//
// Included from XEH_preInit.sqf. Titles and descriptions come from the
// compat_realweather stringtable.

// The setting always registers.  The integration function gates on
// weather.json presence at runtime.  Any loadFile check here would log
// "Script weather.json not found" every launch — we do not do that.
AEE_SETTING_CHECKBOX(enabled,"AEE","Compat - Real Weather",false);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_compat_realweather_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE","Compat - Real Weather Diagnostics",false);
