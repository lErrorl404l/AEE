// initSettings.inc.sqf - CBA Settings registration for aee_maritime
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// maritime stringtable.

// ── Tide ───────────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(tideAmplitude,"AEE Maritime","Sea",0.5,5,2.0,1);

// ── Sea state ──────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(seaStateResponse,"AEE Maritime","Sea",0.1,0.9,0.3,2);

// ── Sea-surface temperature (issue #37) ────────────────────────────────────
// Coupling weight between the air temperature and the latitude-seasonal
// climatology.  Low = high thermal inertia (sea stays near its climate
// baseline); high = the sea follows the air quickly.
AEE_SETTING_SLIDER(seaCouplingWeight,"AEE Maritime","Sea",0,1,0.5,2);
