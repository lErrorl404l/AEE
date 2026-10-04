// initSettings.inc.sqf - CBA Settings registration for aee_compat_acre2
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// compat_acre2 stringtable.
//
// The addon has skipWhenMissingDependencies = 1, so these settings appear
// in the CBA menu only when ACRE2 is loaded.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Signal ─────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(signalDBShift,"AEE","Compat - ACRE2",0,20,8,1);

AEE_SETTING_SLIDER(signalSensitivityMin,"AEE","Compat - ACRE2",-130,-90,-110,0);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_compat_acre2_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE","Compat - ACRE2 Diagnostics",false);
