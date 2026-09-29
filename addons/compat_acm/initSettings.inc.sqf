// initSettings.inc.sqf - CBA Settings registration for aee_compat_acm
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// compat_acm stringtable.
//
// The addon has skipWhenMissingDependencies = 1, so these settings appear
// in the CBA menu only when ACM is loaded.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── CBRN ───────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(CBRNBasePersistence,"AEE","Compat - ACM",6,72,24,0);

AEE_SETTING_SLIDER(CBRNContamThreshold,"AEE","Compat - ACM",0,0.1,0.01,3);

AEE_SETTING_SLIDER(CBRNMaxBuildup,"AEE","Compat - ACM",50,150,100,0);
