// ── NVG battery drain (issue #36) ──────────────────────────────────────────
// Opt-in: battery drain + temperature derating is hardcore (battery dies
// mid-op), so it defaults OFF.  When enabled, the drain rate is scaled
// by the physiology battery temperature derating.
AEE_SETTING_CHECKBOX(nvgBatteryEnabled,"AEE Night Vision","Intensity",false);

// ── NVG grain maximum (issue #203) ─────────────────────────────────────────
// Grain intensity ceilings by condition.  Moved here from aee_optics so the
// nightvision module is self-contained (standalone-distributable).
AEE_SETTING_SLIDER(nightGrainMax,"AEE Night Vision","Intensity",0,1,0.7,0);

AEE_SETTING_SLIDER(rainGrainMax,"AEE Night Vision","Intensity",0,1,0.4,0);

AEE_SETTING_SLIDER(fogGrainMax,"AEE Night Vision","Intensity",0,1,0.15,0);

// ── Laser target marker ────────────────────────────────────────────────────
// A display aid that marks a laser-designated target through night vision.
// Default OFF: the marker is an operator aid, and this switch is the only
// way to raise it.  It stays inert outside an NVG aircraft, so OFF costs
// nothing and no beam can appear without an explicit action.
AEE_SETTING_CHECKBOX(ltmEnabled,"AEE Night Vision","Display",false);
