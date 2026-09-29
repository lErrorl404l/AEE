#include "..\script_component.hpp"

/*
 * Destroy the NVG objective-focus (DepthOfField) handle.
 *
 * Optics calls this when the operator enters thermal (vision mode 2): the
 * tube model's last focus value must not leak into the thermal view as a
 * fixed focus blur.  The handle belongs to this addon, so the module that
 * owns it destroys it; optics never reaches into the nightvision namespace.
 *
 * Params: none.
 * Returns: <NUMBER> 1 when a handle was destroyed, 0 when none was live.
 */

private _h = missionNamespace getVariable [QGVAR(ppHandle_NVG_DoF), -1];
if (_h < 0) exitWith { 0 };

ppEffectDestroy _h;
missionNamespace setVariable [QGVAR(ppHandle_NVG_DoF), -1];
private _logMsg = format ["NVG DoF torn down (was %1)", _h];
AEE_LOG_DEBUG(_logMsg);

1
