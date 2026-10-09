#include "..\..\script_component.hpp"

/*
Ambient (sky) illuminance for the eye model.

The core illuminance model (aee_core_ambientLux, fnc_calculateIlluminance)
carries the night sky: the starlight floor, the moonlight, the twilight glow
and the aurora.  It has NO daylight term, so above the horizon its value falls
to the starlight floor (0.001 lx) and the engine ambient brightness supplies
the daylight.  The engine value is lux-scale: BIKI getLightingAt returns
[ambientLightColor, ambientLightBrightness, dynamicLightColor,
dynamicLightBrightness], and a live docker probe reads the ambient brightness
84987 at day.  Its NIGHT value is a render artifact at an indoor scale (~51 lx
in the operator report), two orders of magnitude above the real night sky, so
it must not override the physical sky at or below the horizon, or the eye
closes to an indoor aperture at night and the already-dark scene darkens (the
operator report: night too dim, local lights imperceptible).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - physical sky illuminance, lx (starlight + moon + twilight + aurora)
  1: Number - engine ambient brightness (getLightingAt element 1), no unit
  2: Number - scale on the engine term (UNSOURCED, operator-tunable)
  3: Number - sun elevation, degrees (0 or below is night)

Returns:
  Number - the ambient illuminance the eye should use, lx.
*/

params [
    ["_physicalLux", 0.001, [0]],
    ["_engineBrightness", 0, [0]],
    ["_engineScale", 1, [0]],
    ["_sunElevation", -90, [0]]
];

private _engine = _engineBrightness * _engineScale;
if (_sunElevation > 0) exitWith { _physicalLux max _engine };
_physicalLux
