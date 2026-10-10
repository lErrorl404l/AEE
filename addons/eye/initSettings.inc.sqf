// initSettings.inc.sqf - CBA Settings registration for aee_eye
//
// Included from XEH_preInit.sqf after the ADR-032 settings migration.  Each
// setting registers with CBA_fnc_addSetting; the eye-adaptation knobs moved
// here from aee_optics and took the aee_eye_* names.  No default changed.

// ── Eye adaptation (issue #141) ───────────────────────────────────────────
// AEE pins the camera aperture and owns the eye adaptation rate.  Every
// value here is traced to a published source or marked UNSOURCED in the
// stringtable description and beside the constant in the kernel.
AEE_SETTING_CHECKBOX(eyeAdaptationEnabled,"AEE Eye","Eye Adaptation",true);

AEE_SETTING_SLIDER(eyeReflectance,"AEE Eye","Eye Adaptation",0.05,0.5,0.18,2);
AEE_SETTING_SLIDER(eyeTauLight,"AEE Eye","Eye Adaptation",0.2,30,2.0,1);
AEE_SETTING_SLIDER(eyeTauDarkCone,"AEE Eye","Eye Adaptation",10,600,120,0);
AEE_SETTING_SLIDER(eyeTauDarkRod,"AEE Eye","Eye Adaptation",60,1800,400,0);
AEE_SETTING_SLIDER(eyePupilTauConstrict,"AEE Eye","Eye Adaptation",0.05,1,0.25,2);
AEE_SETTING_SLIDER(eyePupilTauDilate,"AEE Eye","Eye Adaptation",0.1,2,0.475,3);
AEE_SETTING_SLIDER(eyeMesopicLow,"AEE Eye","Eye Adaptation",0.001,0.1,0.005,3);
AEE_SETTING_SLIDER(eyeMesopicHigh,"AEE Eye","Eye Adaptation",0.5,20,5,1);
AEE_SETTING_SLIDER(eyeFastBlend,"AEE Eye","Eye Adaptation",0,1,0.35,2);
AEE_SETTING_SLIDER(eyeAmbientLuxScale,"AEE Eye","Eye Adaptation",0.001,10,1,3);
AEE_SETTING_SLIDER(eyeLocalLuxScale,"AEE Eye","Eye Adaptation",0.001,10,1,3);
AEE_SETTING_SLIDER(eyeBlindingLuxScale,"AEE Eye","Eye Adaptation",0,100000,0,0);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_eye_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Eye",false);
