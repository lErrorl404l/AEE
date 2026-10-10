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

// ── Propagation ────────────────────────────────────────────────────────────
AEE_SETTING_SLIDER(txPower,"AEE Radio","Link",20,50,37,0);

AEE_SETTING_SLIDER(propagationRange,"AEE Radio","Link",0.5,3,2.0,1);

// ── 3D EM propagation (issue #13) ──────────────────────────────────────────
// Two-ray ground bounce, terrain diffraction (Deygout) and valley waveguide.
AEE_SETTING_CHECKBOX(emPropagationEnabled,"AEE Radio","Link",true);
AEE_SETTING_SLIDER(txAntennaHeight,"AEE Radio","Link",0.5,30,2,1);
AEE_SETTING_SLIDER(rxAntennaHeight,"AEE Radio","Link",0.5,30,1.5,1);
AEE_SETTING_SLIDER(groundReflectivity,"AEE Radio","Link",0,1,0.5,2);
AEE_SETTING_SLIDER(emLinkBearing,"AEE Radio","Link",0,359,0,0);

}; // _hasHost
