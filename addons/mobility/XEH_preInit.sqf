#include "script_component.hpp"

AEE_MODULE_PRE_INIT

ADDON = false;

#include "XEH_PREP.hpp"
#include "initSettings.inc.sqf"

missionNamespace setVariable [QGVAR(isReady), true];

AEE_LOG_INFO("mobility module initialised");

ADDON = true;
