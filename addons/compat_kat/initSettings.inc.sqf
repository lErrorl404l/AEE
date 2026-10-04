// initSettings.inc.sqf - CBA Settings registration for aee_compat_kat
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// compat_kat stringtable.
//
// The addon has skipWhenMissingDependencies = 1, so these settings appear
// in the CBA menu only when KAT is loaded.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Circulation ────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(fluidDrainBase,"AEE","Compat - KAT",0,0.2,0.05,3);

// ── Hypoxia ────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(spo2RiskScale,"AEE","Compat - KAT",10,50,32,0);

AEE_SETTING_SLIDER(spo2Floor,"AEE","Compat - KAT",50,90,60,0);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_compat_kat_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE","Compat - KAT Diagnostics",false);
