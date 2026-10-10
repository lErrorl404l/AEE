// initSettings.inc.sqf - CBA Settings registration for aee_weatherfx
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// weatherfx stringtable.

// ── Exhaust / heat haze ────────────────────────────────────────────────────
AEE_SETTING_SLIDER(exhaustShimmerAlpha,"AEE Weather FX","Particles",0,0.5,0.15,2);

AEE_SETTING_CHECKBOX(heatHazeEnabled,"AEE Weather FX","Particles",true);

AEE_SETTING_SLIDER(heatHazeMaxAlpha,"AEE Weather FX","Particles",0,0.45,0.45,2);

// ── Rain ────────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(rainDropDensity,"AEE Weather FX","Particles",0.001,0.02,0.006,3);

AEE_SETTING_SLIDER(rainVehicleSoundVolume,"AEE Weather FX","Sound",0,2,1.0,1);

// ── Lightning / thunder ─────────────────────────────────────────────────────
AEE_SETTING_SLIDER(lightningFXChance,"AEE Weather FX","Events",0,0.2,0.05,2);

AEE_SETTING_SLIDER(lightningBrightness,"AEE Weather FX","Events",100,5000,1000,0);

AEE_SETTING_SLIDER(thunderVolume,"AEE Weather FX","Sound",0,10,3.5,1);

AEE_SETTING_SLIDER(lightningIgnitionChance,"AEE Weather FX","Events",0,0.5,0.1,2);

// ── Wind / severe weather ───────────────────────────────────────────────────
AEE_SETTING_SLIDER(windNoiseVolume,"AEE Weather FX","Sound",0,2,1.0,1);

AEE_SETTING_SLIDER(severeWeatherBlur,"AEE Weather FX","Events",0,2,1.0,1);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_weatherfx_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Weather FX",false);
