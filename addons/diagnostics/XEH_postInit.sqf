#include "script_component.hpp"

AEE_MODULE_POST_INIT

AEE_LOG_INFO("diagnostics module postInit");

// CBA-familiar public name for the component test runner (CBA_fnc_test).
// The runner uses AEE's mount root (\z\aee\addons\<component>\test.sqf).
missionNamespace setVariable ["AEE_fnc_test", FUNC(test)];
