// initSettings.inc.sqf - CBA Settings registration for aee_ltm
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// ltm stringtable.

// ── Laser target marker ────────────────────────────────────────────────────
// A display aid that marks a laser-designated target through night vision.
// Default OFF: the marker is an operator aid, and this switch is the only
// way to raise it.  It stays inert outside an NVG aircraft, so OFF costs
// nothing and no beam can appear without an explicit action.
AEE_SETTING_CHECKBOX(ltmEnabled,"AEE HUD","Displays",false);

// Fade the laser target marker in daylight.  The marker alpha follows the
// engine sunOrMoon factor (1 day, 0 night): alpha 1.2 - sunOrMoon clamped to
// 0..1, so a full-day marker is 0.2.  Default ON because a full-brightness
// marker in a bright scene is not realistic; OFF holds the marker at 1.
AEE_SETTING_CHECKBOX(ltmDaylightFade,"AEE HUD","Displays",true);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_ltm_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","LTM",false);