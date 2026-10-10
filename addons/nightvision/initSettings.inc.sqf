// ── NVG battery drain (issue #36) ──────────────────────────────────────────
// Opt-in: battery drain + temperature derating is hardcore (battery dies
// mid-op), so it defaults OFF.  When enabled, the drain rate is scaled
// by the physiology battery temperature derating.
AEE_SETTING_CHECKBOX(nvgBatteryEnabled,"AEE Night Vision","Intensity",false);

// ── NVG grain maximum (issue #203) ─────────────────────────────────────────
// Grain intensity ceilings by condition.  Moved here from aee_optics so the
// nightvision module is self-contained (standalone-distributable).
AEE_SETTING_SLIDER(nightGrainMax,"AEE Night Vision","Intensity",0,1,0.7,1);

AEE_SETTING_SLIDER(rainGrainMax,"AEE Night Vision","Intensity",0,1,0.4,1);

AEE_SETTING_SLIDER(fogGrainMax,"AEE Night Vision","Intensity",0,1,0.15,2);

// ── Laser target marker ────────────────────────────────────────────────────
// A display aid that marks a laser-designated target through night vision.
// Default OFF: the marker is an operator aid, and this switch is the only
// way to raise it.  It stays inert outside an NVG aircraft, so OFF costs
// nothing and no beam can appear without an explicit action.

// Fade the laser target marker in daylight.  The marker alpha follows the
// engine sunOrMoon factor (1 day, 0 night): alpha 1.2 - sunOrMoon clamped to
// 0..1, so a full-day marker is 0.2.  Default ON because a full-brightness
// marker in a bright scene is not realistic; OFF holds the marker at 1.

// ── Tube imperfections (issue #215) ────────────────────────────────────────
// The BAD artefacts a real image intensifier shows.  Every magnitude is on
// one slider so the operator can dial the whole flaw set, and each flaw has
// its own strength.  nvgVeilingGlare default 0.0213 is the MIL-I-49428
// section 3.6.15.2 value.
AEE_SETTING_CHECKBOX(nvgImperfectionsEnabled,"AEE Night Vision","Imperfections",true);
AEE_SETTING_SLIDER(nvgImperfectionStrength,"AEE Night Vision","Imperfections",0,2,1.0,2);
AEE_SETTING_SLIDER(nvgBlemishStrength,"AEE Night Vision","Imperfections",0,1,0.5,2);
AEE_SETTING_SLIDER(nvgReticulationStrength,"AEE Night Vision","Imperfections",0,1,0.4,2);
AEE_SETTING_SLIDER(nvgAgcBreathing,"AEE Night Vision","Imperfections",0,1,0.4,2);
AEE_SETTING_SLIDER(nvgBlindingStrength,"AEE Night Vision","Imperfections",0,2,1.0,2);
AEE_SETTING_SLIDER(nvgScintillationStrength,"AEE Night Vision","Imperfections",0,2,1.0,2);
AEE_SETTING_SLIDER(nvgEdgeDistortion,"AEE Night Vision","Imperfections",0,1,0.5,2);
AEE_SETTING_SLIDER(nvgVeilingGlare,"AEE Night Vision","Imperfections",0,0.05,0.0213,4);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_nightvision_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Night Vision",false);
