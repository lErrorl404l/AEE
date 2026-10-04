// initSettings.inc.sqf - CBA Settings registration for aee_fx
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// fx stringtable.

// ── Vehicle Dust ────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(vehicleDustIntensity,"AEE FX","Particles",0,2,1.0,1);

AEE_SETTING_SLIDER(vehicleDustDensity,"AEE FX","Particles",0.01,0.2,0.08,2);

// ── Exhaust ─────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(exhaustShimmerAlpha,"AEE FX","Particles",0,0.5,0.15,0);

// ── Rain ────────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(rainDropDensity,"AEE FX","Particles",0.001,0.02,0.006,3);

AEE_SETTING_SLIDER(rainVehicleSoundVolume,"AEE FX","Sound",0,2,1.0,1);

// ── Atmospheric Dust ────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(atmosphericDustIntensity,"AEE FX","Particles",0,0.5,0.08,2);

// ── Lightning / Thunder ─────────────────────────────────────────────────────
AEE_SETTING_SLIDER(lightningFXChance,"AEE FX","Events",0,0.2,0.05,2);

AEE_SETTING_SLIDER(lightningBrightness,"AEE FX","Events",100,5000,1000,0);

AEE_SETTING_SLIDER(thunderVolume,"AEE FX","Sound",0,10,3.5,1);

AEE_SETTING_SLIDER(lightningIgnitionChance,"AEE FX","Events",0,0.5,0.1,2);

// ── Wind / Severe Weather ───────────────────────────────────────────────────
AEE_SETTING_SLIDER(windNoiseVolume,"AEE FX","Sound",0,2,1.0,1);

AEE_SETTING_SLIDER(severeWeatherBlur,"AEE FX","Events",0,2,1.0,1);

// ── Blast injury channel (issue #132) ──────────────────────────────────────
// Kingery-Bulmash overpressure + Bowen pressure-impulse injury, applied
// via the explosion event hook.  Default on; disable for arcade settings.
AEE_SETTING_CHECKBOX(blastInjuryEnabled,"AEE FX","Events",true);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_fx_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","FX",false);
