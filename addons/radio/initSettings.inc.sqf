// initSettings.inc.sqf - CBA Settings registration for aee_radio
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the
// radio stringtable.

// The radio simulation feeds the ACRE2 and TFAR compat layers — its only
// consumers. Without either host mod the settings and the computed
// propagation index have no consumer, so they must not register.
private _hasHost = isClass (configFile >> "CfgPatches" >> "acre_sys_core")
    || isClass (configFile >> "CfgPatches" >> "task_force_radio");
if (_hasHost) then {

// ── Battery derating (issue #36) ──────────────────────────────────────────
// The txPower derating applies whenever physiology publishes a battery
// temperature derating, independent of any host radio mod.
AEE_SETTING_CHECKBOX(batteryDeratingEnabled,"AEE Radio","Link",true);

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name
// built from the component: aee_<component>_logDebug.  Declaring it here,
// in its own addon, is what makes that name correct.  QGVAR(logDebug)
// resolves to aee_radio_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Radio",false);

}; // _hasHost

// ── Radar detection (issue #104) ──────────────────────────────────────────
// Radar detection is independent of any host radio mod, so it registers
// unconditionally.  Default off: the model is opt-in until a held RCS
// source replaces the issue's class figures, which have
// no published source.
AEE_SETTING_CHECKBOX(radarDetection,"AEE Radio","Radar",false);
