#include "..\script_component.hpp"

/*
Runtime module-health report.

Every AEE module sets a preInit flag and a postInit flag through the
AEE_MODULE_PRE_INIT and AEE_MODULE_POST_INIT macros (addons/main/script_macros.hpp).
A module whose init phase never ran keeps a false flag, so one read of every
flag after a grace period is enough to name a module that did not come up.

The module list is a static array: a module that is not listed cannot be
hidden by a missing flag, and a module that is listed and never runs shows as
false rather than absent.  The report reads the flags only.  It writes one
variable, aee_core_moduleHealth, and it changes no other module's state.

Called once, 10 s after core postInit, from addons/core/XEH_postInit.sqf.

Arguments: none.

Return Value: Nothing.
Public: No
Example: [] call aee_core_fnc_reportModuleHealth
*/

// The static module list.  Each name is the component the AEE_MODULE_* macros
// expand against, so the flag names are aee_<component>_preInit and
// aee_<component>_postInit.  A new module with init flags adds its component.
private _components = [
    "actions",
    "ai",
    "armour",
    "atmos",
    "ballistics",
    "compat_ace3",
    "compat_realweather",
    "core",
    "environmental",
    "fx",
    "maritime",
    "material",
    "mobility",
    "nightvision",
    "optics",
    "physiology",
    "radio",
    "thermal",
    "wildlife"
];

private _health = [];
{
    private _preInit = missionNamespace getVariable [format ["aee_%1_preInit", _x], false];
    if !(_preInit isEqualType false) then { _preInit = false; };
    private _postInit = missionNamespace getVariable [format ["aee_%1_postInit", _x], false];
    if !(_postInit isEqualType false) then { _postInit = false; };
    _health pushBack [_x, _preInit, _postInit];
} forEach _components;

missionNamespace setVariable [QGVAR(moduleHealth), _health];

// One INFO line lists every module and both flags.  The WARN names only the
// module that has not initialised, so a healthy mission logs one line.
private _summary = _health apply {
    format ["%1=%2/%3", _x select 0, _x select 1, _x select 2]
};
AEE_LOG_INFO(format ["module health | %1", _summary joinString " "]);

{
    _x params ["_component", "_preInit", "_postInit"];
    if (!_preInit || {!_postInit}) then {
        AEE_LOG_WARN(format [
            "module not initialised: %1 (preInit=%2 postInit=%3)",
            _component, _preInit, _postInit
        ]);
    };
} forEach _health;
