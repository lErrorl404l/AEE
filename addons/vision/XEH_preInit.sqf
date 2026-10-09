#include "script_component.hpp"

AEE_MODULE_PRE_INIT

ADDON = false;

#include "XEH_PREP.hpp"

// ADR-032 settings migration. The post-process, base-grade, human-vision and
// shadow settings moved here from aee_optics and took the aee_vision_* names;
// copy each set legacy value to its new name BEFORE CBA_fnc_addSetting reads
// it, so a stored value survives the rename. The pairs live beside the
// settings.
[call (compile preprocessFileLineNumbers QPATHTOF(data\settingsMigration.sqf)), "1"] call EFUNC(lib,migrateLegacySettings);

#include "initSettings.inc.sqf"

missionNamespace setVariable [QGVAR(isReady), true];

// Persistent ppEffect handles - Arma 2.22 requires the numeric handle from
// ppEffectCreate (the string-LHS form throws "Type Number, expected Number").
// Create once here so every FX call uses the handle.
[] call FUNC(ppEffectCreate);

// The base effects are created once and adjusted thereafter, never rebuilt per
// tick.  Before the shared registry they had no destroy path on any code path,
// so a stacked second set from a repeat init stayed live for the rest of the
// session.  Registered under the "optics" scope, so this one call frees all
// four and resets their mirrored legacy names to -1.
addMissionEventHandler ["Ended", {
    call FUNC(destroyBasePostProcess);
    call FUNC(teardownBaseGrade);
}];

AEE_LOG_INFO("vision module initialised");

ADDON = true;
