#include "..\..\script_component.hpp"

/*
Local (point and beam) illuminance for the eye model.

The core illuminance model (aee_core_dynamicLux, fnc_calculateIlluminance)
carries the physical local light: lamps, fires, flares, vehicle lights and the
weapon light, computed by inverse-square law from the objects near the player.

The engine getLightingAt term is a second local source.  Its element 3
(dynamicLightBrightness) has no documented unit and is camera-dependent.  At
night it reads an indoor-scale value with no physical meaning, the same render
artifact the ambient gate in fnc_eyeAmbientLux removes.  Left in, it injects an
indoor-scale scene at night, so the eye closes to an indoor aperture and any
movement that changes the engine value moves the aperture target abruptly (the
operator report: the aperture "closed very quickly when moving").

Above the horizon the engine term is a useful brightening, so the larger of the
two is used.  At or below the horizon the physical local light is the truth: a
lamp, fire or vehicle light is already in aee_core_dynamicLux, and a torch or
muzzle flash reaches the eye through its own term.  The engine term is therefore
discarded below the horizon, exactly as fnc_eyeAmbientLux discards the engine
ambient.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - physical local illuminance, lx (aee_core_dynamicLux)
  1: Number - engine dynamic light brightness (getLightingAt element 3), no unit
  2: Number - scale on the engine term (UNSOURCED, operator-tunable)
  3: Number - engine blinding term (apertureParams element 9), no unit
  4: Number - scale on the blinding term (UNSOURCED, operator-tunable)
  5: Number - sun elevation, degrees (0 or below is night)

Returns:
  Number - the local illuminance the eye should use, lx.
*/

params [
    ["_physicalLux", 0, [0]],
    ["_engineLux", 0, [0]],
    ["_engineScale", 1, [0]],
    ["_blinding", 0, [0]],
    ["_blindingScale", 0, [0]],
    ["_sunElevation", -90, [0]]
];

private _engine = (_engineLux * _engineScale) + (_blinding * _blindingScale);
if (_sunElevation > 0) exitWith { _physicalLux max _engine };
_physicalLux
