#include "script_component.hpp"

AEE_MODULE_POST_INIT

if (hasInterface) then {
    // Eye adaptation: AEE owns the camera aperture and its rate (issue #141).
    [] call FUNC(initEyeAdaptation);
};

// Eye muzzle-flash response (issue #141).  Normal vision has no tube to bloom,
// but the flash still raises the scene luminance for a moment.  The eye model
// runs in normal vision only, so this is independent of the NVG handler in
// aee_optics.
["Fired", {
    params ["_unit", "_weapon", "_muzzle", "_mode", "_ammo", "_magazine", "_projectile"];
    if (_unit != call CBA_fnc_currentUnit) exitWith {};
    if (_weapon == "throw" || _weapon == "put") exitWith {};

    private _visibleFire = getNumber (configFile >> "CfgAmmo" >> _ammo >> "visibleFire");
    if (_visibleFire <= 0) exitWith {};

    private _silencer = (_unit weaponAccessories _weapon) select 0;
    private _flashLux = [_visibleFire, _silencer != ""] call FUNC(eyeFlash);

    missionNamespace setVariable [QGVAR(eyeFlashLux), _flashLux];
    missionNamespace setVariable [QGVAR(eyeFlashUntil), CBA_missionTime + (0.15 + _visibleFire * 0.1)];
}, QGVAR(eyeFlash)] call EFUNC(lib,installPlayerEngineHandler);
