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

// ── Weather film grain (aee-workshop-copy item 5) ─────────────────────────
// The rain-scaled grain is re-derived from Real Lighting and Weather (Workshop
// 2809399991); no mod content is copied.  Intensity 0 makes the grain
// invisible.  The grain disengages below half the rain threshold, the module
// hysteresis pattern, so a value at the boundary does not toggle every tick.
AEE_SETTING_SLIDER(weatherGrainIntensity,"AEE Optics","Intensity",0,1,0.5,2);
AEE_SETTING_SLIDER(weatherGrainRainThreshold,"AEE Optics","Intensity",0,1,0.2,2);

// ── Scene-aware shadow distance (aee-workshop-copy item 6) ────────────────
// The shadow distance follows the scene classification.  The values are
// re-derived from Adaptive Shadows (Workshop 3792830104); no mod content is
// copied.  The classifier is heuristic and its thresholds are UNSOURCED.
AEE_SETTING_CHECKBOX(shadowAdaptiveEnabled,"AEE Optics","Shadows",true);
AEE_SETTING_SLIDER(shadowMinDistance,"AEE Optics","Shadows",0,500,50,0);
AEE_SETTING_SLIDER(shadowMaxDistance,"AEE Optics","Shadows",25,2000,500,0);
AEE_SETTING_SLIDER(shadowSampleCount,"AEE Optics","Shadows",5,25,13,0);
AEE_SETTING_SLIDER(shadowUpdateInterval,"AEE Optics","Shadows",0.10,2,0.10,2);
AEE_SETTING_SLIDER(shadowOpeningSensitivity,"AEE Optics","Shadows",3,50,12,0);
AEE_SETTING_SLIDER(shadowFarSceneInfluence,"AEE Optics","Shadows",0,100,75,0);
AEE_SETTING_SLIDER(shadowMovementProtection,"AEE Optics","Shadows",0,10,0.6,2);
AEE_SETTING_SLIDER(shadowCameraTurnProtection,"AEE Optics","Shadows",0,500,0,0);
AEE_SETTING_SLIDER(shadowOpticsProtection,"AEE Optics","Shadows",0,500,0,0);
AEE_SETTING_SLIDER(shadowTargetFPS,"AEE Optics","Shadows",0,240,0,0);

// ── Vision-driven view distance (issue #138) ──────────────────────────────
// Drives the engine's view distance from the physics visibility state
// (fog, haze, rain, NELM, acuity).  Defaults ON; disable to keep the
// player's own view distance setting.
AEE_SETTING_CHECKBOX(viewDistanceEnabled,"AEE Optics","Visibility",true);

// ── ECOTI environment HUD ──────────────────────────────────────────────────
// A night-vision operator aid: heading, grid, altitude, time and the aee
// environment state over the NVG view.  Default OFF (a HUD is an operator
// choice); the HUD workers gate on this setting each tick, so it toggles
// live.
AEE_SETTING_CHECKBOX(hudEnabled,"AEE HUD","Displays",false);

// ── Thermal polarity (issue #196) ─────────────────────────────────────────
// Moved to aee_thermal/initSettings.inc.sqf with the rest of the thermal
// pipeline (white-hot default, black-hot user-selectable per FM 3-22.9).

// ── Eye adaptation (issue #141) ───────────────────────────────────────────
// AEE pins the camera aperture and owns the eye adaptation rate.  Every
// value here is traced to a published source or marked UNSOURCED in the
// stringtable description and beside the constant in the kernel.
AEE_SETTING_CHECKBOX(eyeAdaptationEnabled,"AEE Optics","Eye Adaptation",true);

AEE_SETTING_SLIDER(eyeReflectance,"AEE Optics","Eye Adaptation",0.05,0.5,0.18,2);
AEE_SETTING_SLIDER(eyeTauLight,"AEE Optics","Eye Adaptation",0.2,30,2.0,1);
AEE_SETTING_SLIDER(eyeTauDarkCone,"AEE Optics","Eye Adaptation",10,600,120,0);
AEE_SETTING_SLIDER(eyeTauDarkRod,"AEE Optics","Eye Adaptation",60,1800,400,0);
AEE_SETTING_SLIDER(eyePupilTauConstrict,"AEE Optics","Eye Adaptation",0.05,1,0.25,2);
AEE_SETTING_SLIDER(eyePupilTauDilate,"AEE Optics","Eye Adaptation",0.1,2,0.475,3);
AEE_SETTING_SLIDER(eyeMesopicLow,"AEE Optics","Eye Adaptation",0.001,0.1,0.005,3);
AEE_SETTING_SLIDER(eyeMesopicHigh,"AEE Optics","Eye Adaptation",0.5,20,5,1);
AEE_SETTING_SLIDER(eyeFastBlend,"AEE Optics","Eye Adaptation",0,1,0.35,2);
AEE_SETTING_SLIDER(eyeAmbientLuxScale,"AEE Optics","Eye Adaptation",0.001,10,1,3);
AEE_SETTING_SLIDER(eyeLocalLuxScale,"AEE Optics","Eye Adaptation",0.001,10,1,3);
AEE_SETTING_SLIDER(eyeBlindingLuxScale,"AEE Optics","Eye Adaptation",0,100000,0,0);

// ── Base grade and acuity (image realism) ─────────────────────────────────
// A normal-vision grade that deepens tone separation and the black point,
// plus a FilmGrain acuity candidate.  The engine has no Sharpen effect, so
// scene sharpening stays the operator's video option; the grade applies on
// normal vision only and owns its own effects, so it never fights the
// single-slot weather ColorCorrections.
AEE_SETTING_CHECKBOX(baseGradeEnabled,"AEE Optics","Image",true);
AEE_SETTING_SLIDER(baseGradeContrast,"AEE Optics","Image",0.8,1.6,1.15,2);
AEE_SETTING_SLIDER(baseGradeBrightness,"AEE Optics","Image",0.7,1.3,1.0,2);
AEE_SETTING_SLIDER(baseGradeBlackPoint,"AEE Optics","Image",-0.1,0.1,-0.02,3);
AEE_SETTING_SLIDER(baseGradeSaturation,"AEE Optics","Image",0,0.5,0,2);
AEE_SETTING_SLIDER(baseGradeSharpness,"AEE Optics","Image",1,20,4,1);
AEE_SETTING_SLIDER(baseGradeGrain,"AEE Optics","Image",0,0.05,0.006,3);
AEE_SETTING_CHECKBOX(baseGradeAcuityEnabled,"AEE Optics","Image",true);

// ── Human-vision model (perception) ───────────────────────────────────────
// The physical normal-vision model.  It ships ON: it subsumes the aesthetic
// base grade in place and reads the eye adaptation model.  Every constant is
// traced to a published source or marked UNSOURCED in the stringtable
// description.
AEE_SETTING_CHECKBOX(visionModelEnabled,"AEE Optics","Vision",true);
AEE_SETTING_CHECKBOX(visionToneEnabled,"AEE Optics","Vision",true);
AEE_SETTING_SLIDER(visionToneStrength,"AEE Optics","Vision",0,1,0.25,2);
AEE_SETTING_SLIDER(visionContrastScale,"AEE Optics","Vision",0.5,1.5,1.0,2);
AEE_SETTING_CHECKBOX(visionWhiteBalance,"AEE Optics","Vision",false);

// Colour-stage calibration (AEE Experimental > Vision).  The degree of
// adaptation D is CIECAM02 (CIE 159:2004).  The mesopic desaturation amplitude
// and the Purkinje tint amplitude are UNSOURCED.
AEE_SETTING_SLIDER(visionAdaptationDegree,"AEE Experimental","Vision",0,1,1.0,2);
AEE_SETTING_SLIDER(visionMesopicDesaturation,"AEE Experimental","Vision",0,0.5,0,2);
AEE_SETTING_SLIDER(visionPurkinjeStrength,"AEE Experimental","Vision",0,1,0,2);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_optics_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Optics",false);

// ── Perception monitor (AEE Debug > Perception) ───────────────────────────
// The player-perception monitor publishes the reconstructed view state each
// tick.  Publishing script state is cheap, so the monitor ships ON.  The
// HUD is the noisy surface and ships OFF.
AEE_SETTING_CHECKBOX(perceptionMonitor,"AEE Debug","Perception",true);
AEE_SETTING_CHECKBOX(perceptionHud,"AEE Debug","Perception",false);
AEE_SETTING_SLIDER(perceptionInterval,"AEE Debug","Perception",0.1,2.0,0.5,1);
