// initSettings.inc.sqf - CBA Settings registration for aee_hud
//
// Included from XEH_preInit.sqf after the ADR-032 settings migration.  Each
// setting registers with CBA_fnc_addSetting; the ECOTI HUD and tracker knobs
// moved here from aee_optics and took the aee_hud_* names.  No default changed.

// ── ECOTI environment HUD ──────────────────────────────────────────────────
// A night-vision operator aid: heading, grid, altitude, time and the aee
// environment state over the NVG view.  Default OFF (a HUD is an operator
// choice); the HUD workers gate on this setting each tick, so it toggles live.
AEE_SETTING_CHECKBOX(hudEnabled,"AEE HUD","Displays",false);

// ── Signal-dependent tracker (task 13) ────────────────────────────────────
// Replaces the arcade exact friendly position with each unit's own GPS
// solution, reported over a modelled datalink.  Default OFF; the driver and the draw gate on it each tick.
AEE_SETTING_CHECKBOX(trackerEnabled,"AEE HUD","Tracker",false);

// Suppress the engine friendly map indicators where the engine allows it.
// The suppression is a LOCAL disableMapIndicators call (Arma 3 1.82+) that
// acts only when the difficulty exposes "extended map content".  The tracker
// draws its own fuzzy markers regardless.
AEE_SETTING_CHECKBOX(trackerSuppressIcons,"AEE HUD","Tracker",false);

// Seconds between tracker model updates for the local group.  A longer
// interval is cheaper and ages the tracks more.
AEE_SETTING_SLIDER(trackerInterval,"AEE HUD","Tracker",0.2,5,1.0,1);

// The datalink radio that carries the position reports.  Defaults: the
// L3Harris AN/PRC-152A data sheet (5 W; -116 dBm at 12 dB SINAD, FM
// 30-152 MHz), isotropic antennas, and the radio module's 100 MHz reference.
AEE_SETTING_SLIDER(trackerTxPowerDbm,"AEE HUD","Tracker",24,40,37,0);
AEE_SETTING_SLIDER(trackerAntennaGainDbi,"AEE HUD","Tracker",-20,10,0,1);
AEE_SETTING_SLIDER(trackerRxSensitivityDbm,"AEE HUD","Tracker",-130,-90,-116,0);
AEE_SETTING_SLIDER(trackerFrequencyMHz,"AEE HUD","Tracker",30,512,100,0);

// Self-report intervals, the ATAK Dynamic strategy (ATAK-CIV defaults for an
// unreliable, multicast network): still, slow (1 mph) and fast (30 mph).
AEE_SETTING_SLIDER(trackerReportStationary,"AEE HUD","Tracker",1,600,30,0);
AEE_SETTING_SLIDER(trackerReportSlow,"AEE HUD","Tracker",1,600,20,0);
AEE_SETTING_SLIDER(trackerReportFast,"AEE HUD","Tracker",1,600,2,0);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_hud_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","HUD",false);
