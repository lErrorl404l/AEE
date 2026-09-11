#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

missionNamespace setVariable [QGVAR(isReady), true];

AEE_LOG("optics module initialised");

ADDON = true;
