#include "..\..\script_component.hpp"
/*
Wet-distortion parameter builder for the thermal display (rain on the lens).

A real FLIR objective lens collects a water film in rain.  The film refracts
the incoming LWIR wavefront, so the image crawls and smears.  The engine's
WetDistortion post-process models that lens film.  AEE drives it from its own
weather state: a dry scene gives a neutral vector (the effect is disabled),
and the amplitude rises with the rain and fog the environment model publishes.

Mechanism and parameter vector: MKK thermal_improvement (workshop 3753145363)
functions/fnc_applyVisionEffects.sqf:158-166.  MKK creates WetDistortion with
[wetDistortion, wetDistortion, wetDistortion, 4.10, 3.70, 2.50, 1.85, 0.0054,
0.0041, 0.0090, 0.0070, 0.5, 0.3, 10, 6] when the preset value is above zero.
The fixed coefficients are the engine defaults (Bohemia Interactive Community
wiki, Post Process Effects, WetDistortion: "Defaults [1, 1, 1, 4.10, 3.70,
2.50, 1.85, 0.0054, 0.0041, 0.0090, 0.0070, 0.5, 0.3, 10.0, 6.0]").  The first
three elements are the lens blurriness (value, top, bottom); the wiki range
is 0..1.  AEE scales those three by the wet state instead of fixing them to
the MKK preset value.

Pure kernel: no engine calls.  fnc_applyThermalVision computes the wet state
from the rain and fog it already reads and calls this.

Arguments:
  0: wet state (NUMBER, 0..1) - 0 dry, 1 fully wet
  1: maximum amplitude (NUMBER, optional) - the lens blurriness at full wet

Return Value:
  ARRAY - the 15-element WetDistortion vector.  The first three elements are
          zero when dry, so the caller disables the effect.
*/
params [
    ["_wetness", 0, [0]],
    ["_maxAmp", 0.08, [0]]
];

if !(_wetness isEqualType 0) then { _wetness = 0; };
if !(_maxAmp isEqualType 0) then { _maxAmp = 0; };
_wetness = (_wetness max 0) min 1;
private _amp = (_maxAmp max 0) * _wetness;

[
    _amp, _amp, _amp,
    4.10, 3.70, 2.50, 1.85,
    0.0054, 0.0041, 0.0090, 0.0070,
    0.5, 0.3, 10, 6
]
