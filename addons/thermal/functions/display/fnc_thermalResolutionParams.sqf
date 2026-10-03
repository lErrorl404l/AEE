#include "..\..\script_component.hpp"
/*
Resolution (sensor pixelation) parameter builder for the thermal display.

A thermal sensor resolves a fixed number of detector pixels.  A 320x240
microbolometer shows visible pixel blocks on a 1080p display, while a
1280x1024 cooled array is finer than the display and shows none.  The engine's
Resolution post-process reproduces that.  ppEffectAdjust takes ONE integer,
the render's vertical resolution (Bohemia Interactive Community wiki, Post
Process Effects, Resolution: "verticalResolution - define the render's
vertical resolution.  If the value is negative, the resolution goes back to
normal.  If the value is greater than the final render's vertical resolution,
it gets clamped to it.").  The engine clamps and disables, so no figure is
invented here.

Mechanism: MKK thermal_improvement (workshop 3753145363)
functions/fnc_applyVisionEffects.sqf:118-129.  MKK also drives the engine's
global TI MaxResolution through setTIParameter, which is engine-global across
every TI device and must be saved and restored (MKK
functions/fnc_cleanupVisionEffects.sqf:14-17).  AEE does NOT touch that
engine-global parameter.  AEE keeps the per-effect Resolution form only, so
the pixelation is scoped to the operator's own display.

The figure is the device's own vertical resolution from
EFUNC(thermal,getThermalDeviceProperties) - never invented.

Arguments:
  0: detector width in pixels (NUMBER) - part of the device contract
  1: detector height in pixels (NUMBER)

Return Value:
  ARRAY - [] when the height is not positive, else [verticalResolution].
*/
params [
    ["_resX", 0, [0]],
    ["_resY", 0, [0]]
];

if !(_resX isEqualType 0) then { _resX = 0; };
if !(_resY isEqualType 0) then { _resY = 0; };
if (_resY <= 0) exitWith { [] };

[round _resY]
