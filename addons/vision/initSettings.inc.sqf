// initSettings.inc.sqf - CBA Settings registration for aee_vision
//
// Included from XEH_preInit.sqf after the ADR-032 settings migration.  Each
// setting registers with CBA_fnc_addSetting; the post-process, base-grade,
// human-vision and shadow knobs moved here from aee_optics and took the
// aee_vision_* names.  No default changed.

// ── Weather film grain (aee-workshop-copy item 5) ─────────────────────────
// The rain-scaled grain is re-derived from Real Lighting and Weather (Workshop
// 2809399991); no mod content is copied.  Intensity 0 makes the grain
// invisible.  The grain disengages below half the rain threshold, the module
// hysteresis pattern, so a value at the boundary does not toggle every tick.
AEE_SETTING_SLIDER(weatherGrainIntensity,"AEE Vision","Intensity",0,1,0.5,2);
AEE_SETTING_SLIDER(weatherGrainRainThreshold,"AEE Vision","Intensity",0,1,0.2,2);

// ── Scene-aware shadow distance (aee-workshop-copy item 6) ────────────────
// The shadow distance follows the scene classification.  The values are
// re-derived from Adaptive Shadows (Workshop 3792830104); no mod content is
// copied.  The classifier is heuristic and its thresholds are UNSOURCED.
AEE_SETTING_CHECKBOX(shadowAdaptiveEnabled,"AEE Vision","Shadows",true);
AEE_SETTING_SLIDER(shadowMinDistance,"AEE Vision","Shadows",0,500,50,0);
AEE_SETTING_SLIDER(shadowMaxDistance,"AEE Vision","Shadows",25,2000,500,0);
AEE_SETTING_SLIDER(shadowSampleCount,"AEE Vision","Shadows",5,25,13,0);
AEE_SETTING_SLIDER(shadowUpdateInterval,"AEE Vision","Shadows",0.10,2,0.10,2);
AEE_SETTING_SLIDER(shadowOpeningSensitivity,"AEE Vision","Shadows",3,50,12,0);
AEE_SETTING_SLIDER(shadowFarSceneInfluence,"AEE Vision","Shadows",0,100,75,0);
AEE_SETTING_SLIDER(shadowMovementProtection,"AEE Vision","Shadows",0,10,0.6,2);
AEE_SETTING_SLIDER(shadowCameraTurnProtection,"AEE Vision","Shadows",0,500,0,0);
AEE_SETTING_SLIDER(shadowOpticsProtection,"AEE Vision","Shadows",0,500,0,0);
AEE_SETTING_SLIDER(shadowTargetFPS,"AEE Vision","Shadows",0,240,0,0);

// ── Vision-driven view distance (issue #138) ──────────────────────────────
// Drives the engine's view distance from the physics visibility state
// (fog, haze, rain, NELM, acuity).  Defaults ON; disable to keep the
// player's own view distance setting.
AEE_SETTING_CHECKBOX(viewDistanceEnabled,"AEE Vision","Visibility",true);

// ── Base grade and acuity (image realism) ─────────────────────────────────
// A normal-vision grade that deepens tone separation and the black point,
// plus a FilmGrain acuity candidate.  The engine has no Sharpen effect, so
// scene sharpening stays the operator's video option; the grade applies on
// normal vision only and owns its own effects, so it never fights the
// single-slot weather ColorCorrections.
AEE_SETTING_CHECKBOX(baseGradeEnabled,"AEE Vision","Image",true);
AEE_SETTING_SLIDER(baseGradeContrast,"AEE Vision","Image",0.8,1.6,1.15,2);
AEE_SETTING_SLIDER(baseGradeBrightness,"AEE Vision","Image",0.7,1.3,1.0,2);
AEE_SETTING_SLIDER(baseGradeBlackPoint,"AEE Vision","Image",-0.1,0.1,-0.02,3);
AEE_SETTING_SLIDER(baseGradeSaturation,"AEE Vision","Image",0,0.5,0,2);
AEE_SETTING_SLIDER(baseGradeSharpness,"AEE Vision","Image",1,20,4,1);
AEE_SETTING_SLIDER(baseGradeGrain,"AEE Vision","Image",0,0.05,0.006,3);
AEE_SETTING_CHECKBOX(baseGradeAcuityEnabled,"AEE Vision","Image",true);

// ── Human-vision model (perception) ───────────────────────────────────────
// The physical normal-vision model.  It ships ON: it subsumes the aesthetic
// base grade in place and reads the eye adaptation model.  Every constant is
// traced to a published source or marked UNSOURCED in the stringtable
// description.
AEE_SETTING_CHECKBOX(visionModelEnabled,"AEE Vision","Vision",true);
AEE_SETTING_CHECKBOX(visionToneEnabled,"AEE Vision","Vision",true);
AEE_SETTING_SLIDER(visionToneStrength,"AEE Vision","Vision",0,1,0.25,2);
AEE_SETTING_SLIDER(visionContrastScale,"AEE Vision","Vision",0.5,1.5,1.0,2);
AEE_SETTING_CHECKBOX(visionWhiteBalance,"AEE Vision","Vision",false);

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
// resolves to aee_vision_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Vision",false);

// ── Perception monitor (AEE Debug > Perception) ───────────────────────────
// The player-perception monitor publishes the reconstructed view state each
// tick.  Publishing script state is cheap, so the monitor ships ON.  The
// HUD is the noisy surface and ships OFF.
AEE_SETTING_CHECKBOX(perceptionMonitor,"AEE Debug","Perception",true);
AEE_SETTING_CHECKBOX(perceptionHud,"AEE Debug","Perception",false);
AEE_SETTING_SLIDER(perceptionInterval,"AEE Debug","Perception",0.1,2.0,0.5,1);
