// initSettings.inc.sqf - CBA Settings registration for aee_particles
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// particles stringtable.

// ── Vehicle dust ───────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(vehicleDustIntensity,"AEE Particles","Particles",0,2,1.0,1);

AEE_SETTING_SLIDER(vehicleDustDensity,"AEE Particles","Particles",0.01,0.2,0.08,2);

// ── Atmospheric dust ───────────────────────────────────────────────────────
AEE_SETTING_SLIDER(atmosphericDustIntensity,"AEE Particles","Particles",0,0.5,0.08,2);

// ── Weather coupling ───────────────────────────────────────────────────────
// The weather alpha multiplies the particle colours by (overcast + humidity
// / 100).  NOTE: the plan writes the typo weatherAlphalEnabled; the shipped
// name is weatherAlphaEnabled.
AEE_SETTING_CHECKBOX(weatherAlphaEnabled,"AEE Particles","Particles",true);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_particles_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Particles",false);
