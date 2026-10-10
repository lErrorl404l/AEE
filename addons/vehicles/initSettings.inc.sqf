// initSettings.inc.sqf - CBA Settings registration for aee_vehicles
//
// Included from XEH_preInit.sqf. Each setting registers with
// CBA_fnc_addSetting; titles and descriptions come from the vehicles
// stringtable.

// ── Vehicle Performance ─────────────────────────────────────────────────────
AEE_SETTING_SLIDER(minEnginePower,"AEE Vehicles","Traction",0.1,0.8,0.3,1);

// ── Runtime vehicle coupling ──────────────────────────────────────────────
// Applies the surface accretion load with setMass and the wet/ice grip loss
// with a force. Both run on the machine that owns the vehicle. The setting
// lives with the vehicle kernels and the mobility coupling loop reads it
// through EGVAR(vehicles,vehicleCouplingEnabled).
AEE_SETTING_CHECKBOX(vehicleCouplingEnabled,"AEE Vehicles","Vehicle",true);

// ── Vehicle Mass Estimate ──────────────────────────────────────────────────
// The estimate is modelled, not documented. A sourced catalogue weight always
// takes precedence. The switch stays off until the model passes calibration
// and a human approves mass_model.json.
[
    QGVAR(estimateVehicleMassEnabled),
    "CHECKBOX",
    [LLSTRING(estimateVehicleMassEnabled_Name), LLSTRING(estimateVehicleMassEnabled_Description)],
    ["AEE Vehicles", "Vehicle"],
    false,  // default: disabled until calibration and approval pass
    true,   // global, so the estimate is the same on every machine
    {}
] call CBA_fnc_addSetting;

// ── Diagnostics ───────────────────────────────────────────────────────────
// The per-module trace switch.  The AEE_LOG_DEBUG macro reads the name built
// from the component: aee_vehicles_logDebug.  Declaring it here, in its own
// addon, is what makes that name correct.  QGVAR(logDebug) resolves to
// aee_vehicles_logDebug.
AEE_SETTING_CHECKBOX(logDebug,"AEE Debug","Vehicles",false);
