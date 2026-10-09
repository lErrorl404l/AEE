#include "..\script_component.hpp"

/*
Runtime module-health report.

Every AEE module sets a preInit flag and a postInit flag through the
AEE_MODULE_PRE_INIT and AEE_MODULE_POST_INIT macros (addons/lib/script_macros.hpp).
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
Example: [] call aee_diagnostics_fnc_reportModuleHealth
*/

// The static module list.  Each name is the component the AEE_MODULE_* macros
// expand against, so the flag names are aee_<component>_preInit and
// aee_<component>_postInit.  A new module with init flags adds its component.
// The compat_* modules are conditionally loaded by their host mod and are
// covered by their own compat probes, so they are excluded here: on a host
// without the mod the engine skips the addon and its flags stay false.
private _components = [
    "actions",
    "ai",
    "armour",
    "atmos",
    "ballistics",
    "core",
    "diagnostics",
    "fx",
    "lighting",
    "maritime",
    "material",
    "mobility",
    "nightvision",
    "optics",
    "persistence",
    "physiology",
    "radio",
    "thermal",
    "weather",
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

missionNamespace setVariable [QEGVAR(core,moduleHealth), _health];

// One INFO line lists every module and both flags.  The WARN names only the
// module that has not initialised, so a healthy mission logs one line.
private _summary = _health apply {
    format ["%1=%2/%3", _x select 0, _x select 1, _x select 2]
};
private _logMsg = format ["module health | %1", _summary joinString " "];
AEE_LOG_INFO(_logMsg);

{
    _x params ["_component", "_preInit", "_postInit"];
    if (!_preInit || {!_postInit}) then {
        private _logMsg = format [
            "module not initialised: %1 (preInit=%2 postInit=%3)",
            _component, _preInit, _postInit
        ];
        AEE_LOG_WARN(_logMsg);
    };
} forEach _health;
