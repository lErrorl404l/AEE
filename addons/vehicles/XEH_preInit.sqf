#include "script_component.hpp"

AEE_MODULE_PRE_INIT

ADDON = false;

#include "XEH_PREP.hpp"

// ADR-032 settings migration. The vehicle settings moved here from aee_mobility
// and took the aee_vehicles_* names; copy each set legacy value to its new name
// BEFORE CBA_fnc_addSetting reads it, so a stored value survives the rename.
// The pairs live beside the settings.
[call (compile preprocessFileLineNumbers QPATHTOF(data\settingsMigration.sqf)), "1"] call EFUNC(lib,migrateLegacySettings);

#include "initSettings.inc.sqf"

AEE_LOG_INFO("vehicles module initialised");

ADDON = true;
