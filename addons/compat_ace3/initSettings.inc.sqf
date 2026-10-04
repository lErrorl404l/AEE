// initSettings.inc.sqf - CBA Settings registration for aee_compat_ace3
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// compat_ace3 stringtable.
//
// The addon has skipWhenMissingDependencies = 1, so these settings appear
// in the CBA menu only when ACE3 is loaded.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Medical ────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(medicalWBGTThreshold,"AEE","Compat - ACE3",18,35,23,1);

AEE_SETTING_SLIDER(medicalRiskThreshold,"AEE","Compat - ACE3",0,1,0.3,2);

AEE_SETTING_SLIDER(medicalHeatStrokeWBGT,"AEE","Compat - ACE3",25,45,32,1);

AEE_SETTING_SLIDER(medicalBurnTemp,"AEE","Compat - ACE3",20,45,25,1);

AEE_SETTING_SLIDER(medicalBurnDamageScale,"AEE","Compat - ACE3",0,0.01,0.0005,4);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_compat_ace3_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Compat - ACE3",false);
