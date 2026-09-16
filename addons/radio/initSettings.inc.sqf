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
[
    QGVAR(batteryDeratingEnabled),
    "CHECKBOX",
    [LLSTRING(batteryDeratingEnabled_Name), LLSTRING(batteryDeratingEnabled_Description)],
    ["AEE Radio", "Link"],
    true,
    true,
    {}
] call CBA_fnc_addSetting;

// ── Propagation ────────────────────────────────────────────────────────────
[
    QGVAR(txPower),
    "SLIDER",
    [LLSTRING(txPower_Name), LLSTRING(txPower_Description)],
    ["AEE Radio", "Link"],
    [20, 50, 37, 0],
    true,
    {}
] call CBA_fnc_addSetting;

[
    QGVAR(propagationRange),
    "SLIDER",
    [LLSTRING(propagationRange_Name), LLSTRING(propagationRange_Description)],
    ["AEE Radio", "Link"],
    [0.5, 3, 2.0, 1],
    true,
    {}
] call CBA_fnc_addSetting;

}; // _hasHost
