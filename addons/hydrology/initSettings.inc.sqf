// initSettings.inc.sqf - CBA Settings registration for aee_hydrology
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the hydrology
// stringtable.

// ── Hydrology (issue #24) ─────────────────────────────────────────────────
// These drive the rainfall-runoff chain in fnc_calculateRiverWaterLevel.
// The defaults are the operational values the models were calibrated on,
// so the settings change the model rather than decorating it.
AEE_SETTING_SLIDER(riverSectionWidth_m,"AEE Hydrology","Hydrology",0.5,50,4,1);

AEE_SETTING_SLIDER(tidalReach_m,"AEE Hydrology","Hydrology",500,20000,5000,0);

AEE_SETTING_SLIDER(baseflowRate_perDay,"AEE Hydrology","Hydrology",0.01,1,0.2,2);

AEE_SETTING_SLIDER(catchmentArea_m2,"AEE Hydrology","Hydrology",10000,5000000,250000,0);

AEE_SETTING_SLIDER(bedSlope,"AEE Hydrology","Hydrology",0.0001,0.05,0.001,4);

AEE_SETTING_SLIDER(manningN,"AEE Hydrology","Hydrology",0.01,0.1,0.035,3);

AEE_SETTING_SLIDER(riverResponseRate,"AEE Hydrology","Hydrology",0.01,0.5,0.1,2);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name built
// from the component: aee_hydrology_logDebug.  Declaring it here, in its own
// addon, is what makes that name correct.  QGVAR(logDebug) resolves to
// aee_hydrology_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Hydrology",false);
