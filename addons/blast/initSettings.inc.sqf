// initSettings.inc.sqf - CBA Settings registration for aee_blast
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// blast stringtable.

// ── Blast injury channel (issue #132) ──────────────────────────────────────
// Kingery-Bulmash overpressure + Bowen pressure-impulse injury, applied
// via the explosion event hook.  Default on; disable for arcade settings.
AEE_SETTING_CHECKBOX(blastInjuryEnabled,"AEE Blast","Events",true);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_blast_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Blast",false);