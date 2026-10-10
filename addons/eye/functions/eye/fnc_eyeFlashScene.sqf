#include "..\..\script_component.hpp"

/*
Split the eye scene into the published scene and the adaptation scene.

The eye samples the steady scene: the physical sky (fnc_eyeAmbientLux) plus the
core local light (fnc_eyeLocalLux).  A muzzle flash adds a short transient
(aee_optics_eyeFlashLux, stamped by the Fired handler).  The transient raises
the luminance the eye ADAPTS to, but the core illuminance model
(aee_core_illuminanceLux) carries no muzzle flash, so the transient must NOT
enter the published scene.  The cross-module invariant INV-1
(night_scene_agreement) compares the published scene against the core
illuminance and expects the physical-sky value.  A shot that reached the
published scene raised a false INV-1 warning: the operator RPT of 2026-10-08
recorded drift 4499.97 at a published scene of 4500.5 lx (a 5.56 muzzle flash
of 3.0 visibleFire units at the 1500 lx/unit scale), while the core stayed at
0.53 lx.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - steady scene illuminance, lx (sample plus the force hooks)
  1: Number - muzzle-flash illuminance, lx
  2: Number - flash window end, mission time (s)
  3: Number - current mission time (s)

Returns:
  Array - [publishedSceneLux, adaptationSceneLux].  The published scene is the
          steady scene.  The adaptation scene adds the flash while the window
          is open.
*/

params [
    ["_steadyLux", 0, [0]],
    ["_flashLux", 0, [0]],
    ["_flashUntil", 0, [0]],
    ["_missionTime", 0, [0]]
];

private _adaptLux = _steadyLux;
if ((_flashUntil isEqualType 0) && _missionTime < _flashUntil && _flashLux isEqualType 0) then {
    _adaptLux = _steadyLux + _flashLux;
};

[_steadyLux, _adaptLux]
