#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

// The radio simulation feeds the ACRE2 and TFAR compat layers — its only
// consumers. Without either host mod, the radio settings and the computed
// propagation index have no effect, so the settings must not register
// (the same visibility rule as the compat addons themselves).
private _hasHost = isClass (configFile >> "CfgPatches" >> "acre_sys_core")
    || isClass (configFile >> "CfgPatches" >> "task_force_radio");
if (_hasHost) then {
    #include "initSettings.inc.sqf"
};

AEE_LOG("radio module initialised");

ADDON = true;
