// initSettings.inc.sqf - CBA Settings registration for aee_optics
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// optics stringtable.
//
// ponytail: one call per setting; a bulk-register macro would add complexity
// that only pays off at 50+ settings.

// ── Optics / Visibility ─────────────────────────────────────────────────────
AEE_SETTING_SLIDER(seeingFXIntensity,"AEE Optics","Intensity",0,0.1,0.02,2);

AEE_SETTING_SLIDER(mirageIntensity,"AEE Optics","Intensity",0,2,1.0,0);

AEE_SETTING_SLIDER(mirageDensity,"AEE Optics","Intensity",0.01,0.5,0.08,2);

AEE_SETTING_SLIDER(solarGlareIntensity,"AEE Optics","Intensity",0,2,1.0,0);

// ── Atmospheric optical phenomena ──────────────────────────────────────────
AEE_SETTING_CHECKBOX(greenFlashEnabled,"AEE Optics","Atmosphere",true);

AEE_SETTING_SLIDER(glareBlurMax,"AEE Optics","Intensity",0,1,0.2,1);

AEE_SETTING_SLIDER(heatShimmerIntensity,"AEE Optics","Intensity",0,0.2,0.04,2);

AEE_SETTING_SLIDER(dewBlurMax,"AEE Optics","Intensity",0,1,0.4,1);

AEE_SETTING_SLIDER(snowBlindnessIntensity,"AEE Optics","Intensity",0,2,1.0,0);

AEE_SETTING_SLIDER(rainBlurScale,"AEE Optics","Intensity",0,1,0.3,1);

AEE_SETTING_SLIDER(mirageOnsetTemp,"AEE Optics","Thresholds",20,50,35,0);

AEE_SETTING_SLIDER(mirageMinSunElev,"AEE Optics","Thresholds",0,30,15,0);

AEE_SETTING_SLIDER(smokePersistenceScale,"AEE Optics","Atmosphere",0.2,3,1.0,1);

AEE_SETTING_SLIDER(snowVisibilityPenalty,"AEE Optics","Atmosphere",0.3,1,0.7,1);

AEE_SETTING_SLIDER(vehicleShimmerBase,"AEE Optics","Thresholds",0,1,0.3,1);

AEE_SETTING_SLIDER(snowBlindnessBase,"AEE Optics","Thresholds",0,0.5,0.1,1);

AEE_SETTING_SLIDER(dewAccumRate,"AEE Optics","Particles",0,0.2,0.05,2);

AEE_SETTING_SLIDER(dewDecayRate,"AEE Optics","Particles",0,0.1,0.02,2);

AEE_SETTING_SLIDER(rainAccumRate,"AEE Optics","Particles",0,0.05,0.01,2);

AEE_SETTING_SLIDER(rainDecayRate,"AEE Optics","Particles",0,0.1,0.02,2);

AEE_SETTING_SLIDER(chromaCap,"AEE Optics","Intensity",0,0.2,0.06,2);

// ── Thermal polarity (issue #196) ─────────────────────────────────────────
// Moved to aee_thermal/initSettings.inc.sqf with the rest of the thermal
// pipeline (white-hot default, black-hot user-selectable per FM 3-22.9).

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_optics_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Optics",false);
