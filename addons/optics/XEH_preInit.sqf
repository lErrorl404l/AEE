#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"
#include "initSettings.inc.sqf"

missionNamespace setVariable [QGVAR(isReady), true];

// Persistent ppEffect handles — Arma 2.22 requires the numeric handle
// from ppEffectCreate (the string-LHS form throws "Type Number,
// expected Number").  Create once here so every FX call uses the handle.
[] call FUNC(ppEffectCreate);

AEE_LOG_INFO("optics module initialised");

ADDON = true;
