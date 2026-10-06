// initSettings.inc.sqf - CBA Settings registration for aee_ballistics
//
// Included from XEH_preInit.sqf. Titles and descriptions come from the
// ballistics stringtable.

// ── Ammo temperature model (issue #94) ────────────────────────────────────
// The tracked per-weapon ammo temperature is a lazy first-order exchange
// toward ambient (plus solar soak), with per-shot propellant heat.  These
// two settings tune the model.
AEE_SETTING_SLIDER(ammoTempTimeConstant,"AEE Ballistics","Ammo Temperature",30,3600,600,0);

AEE_SETTING_SLIDER(ammoHeatPerShotJ,"AEE Ballistics","Ammo Temperature",0,0.001,0.0001,4);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_ballistics_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Ballistics",false);
