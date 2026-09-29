#include "script_component.hpp"

AEE_MODULE_PRE_INIT

ADDON = false;

#include "XEH_PREP.hpp"
#include "initSettings.inc.sqf"

missionNamespace setVariable [QGVAR(isReady), true];

// Persistent ppEffect handles — Arma 2.22 requires the numeric handle
// from ppEffectCreate (the string-LHS form throws "Type Number,
// expected Number").  Create once here so every FX call uses the handle.
[] call FUNC(ppEffectCreate);

// The base effects are created once and adjusted thereafter, never rebuilt per
// tick.  Before the shared registry they had no destroy path on any code path,
// so a stacked second set from a repeat init stayed live for the rest of the
// session.  Registered under the "optics" scope, so this one call frees all
// four and resets their mirrored legacy names to -1.
addMissionEventHandler ["Ended", {
    call FUNC(destroyBasePostProcess);
}];

AEE_LOG_INFO("optics module initialised");

ADDON = true;
