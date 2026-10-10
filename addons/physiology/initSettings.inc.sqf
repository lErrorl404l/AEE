// initSettings.inc.sqf - CBA Settings registration for aee_physiology
//
// Included from XEH_preInit.sqf.  Only the shared physiology settings stay
// here: the heat-stress HUD warning and the module trace switch.  The
// strain, altitude, dive and clothing settings moved to their own addons
// and took the aee_<module>_* names (ADR-032).

// ── Heat Stress HUD ────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(HUDWarningThreshold,"AEE HUD","Displays",0,1,0.3,1);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_physiology_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Physiology",false);
