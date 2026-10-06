#include "script_component.hpp"

AEE_MODULE_PRE_INIT

ADDON = false;

#include "XEH_PREP.hpp"
#include "initSettings.inc.sqf"

// Exposure pin test (issue #196 prototype).  The operator sets
// aee_thermal_agcPinned = true from the debug console to suspend the AGC
// window writers and pin the engine window by hand.  Seeded here so the
// variable exists from the first frame.
missionNamespace setVariable [QGVAR(agcPinned), false];

AEE_LOG_INFO("thermal module initialised");

ADDON = true;
