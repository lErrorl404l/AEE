#include "..\..\script_component.hpp"
/*
 * Fusion field-of-view frame geometry (issue #204, Track B ENVG-B).
 *
 * Returns the on-screen half-extent of the thermal-channel frame as a
 * fraction of safeZoneH.  The frame is a HUD aid, not optics: it shows the
 * operator where the fusion gate is actually bounded.
 *
 * The thermal channel half-angle is an angle about the VIEW AXIS.  The
 * intensified tube in front of it is the NVG device's own field.  The
 * on-screen extent is the ratio of the two tangents:
 *
 *     ratio = tan(thermalHalfAngle) / tan(nvgFieldDeg / 2)
 *
 * That is the pinhole projection of an equal angular half-extent on both
 * axes.  The camera's angular scale here is the NVG device's published field
 * (fnc_getNvgDeviceProperties, fovDeg), because the intensified tube fills
 * the engine's NVG cutout; the engine's own camera FOV command is not used,
 * so no value is invented.  The thermal channel is a CIRCULAR field, so the
 * same angular half-extent maps to a square on screen; the caller draws a
 * square border (a rectangle with equal sides).  For the ENVG-B the declared
 * 20-degree channel equals half of the device's declared 40-degree field, so
 * the ratio is 1 and the frame sides sit at the field edge.  Like the gate
 * itself this is an inference and it is labelled as one.
 *
 * The ratio is clamped to [0, 1]: a thermal field wider than the tube is
 * clipped by the engine's circular cutout anyway, and a non-finite or
 * negative input must not produce a frame that wraps the screen.
 *
 * Pure function: no engine state, no display, no hasInterface.  The P80
 * headless probe and the unit suite execute it directly.
 *
 * tan takes DEGREES on the Arma engine, so no radian conversion is applied.
 *
 * Params:
 *   0: _halfAngleDeg (SCALAR) - the thermal channel half-angle in degrees.
 *   1: _nvgFieldDeg (SCALAR)  - the NVG device full field in degrees.
 *
 * Returns: SCALAR - on-screen half-extent as a fraction of safeZoneH.
 */
params [
    ["_halfAngleDeg", 20, [0]],
    ["_nvgFieldDeg", 40, [0]]
];

private _nvgHalfDeg = (_nvgFieldDeg / 2) max 1;
private _ratio = (tan _halfAngleDeg) / (tan _nvgHalfDeg);
if (!finite _ratio) then { _ratio = 0; };

// Explicit parentheses: max/min are left-associative in SQF, and the clamp
// must not depend on that reading.
(_ratio max 0) min 1
