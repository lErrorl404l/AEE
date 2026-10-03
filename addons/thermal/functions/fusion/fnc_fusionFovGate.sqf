#include "..\..\script_component.hpp"
/*
 * Fusion thermal-channel field gate (issue #204, Track B ENVG-B).
 *
 * The overlay is bounded by the DEVICE's thermal field, not by the screen.
 * A target whose bearing from the view axis exceeds the thermal channel's
 * half-angle is outside the fused image, so it receives no emissive
 * material and keeps its own.
 *
 * The bound is an inference from published figures: the BNVD-FUSED states
 * 34 degrees diagonal and the intensified side 40, which makes the thermal
 * geometrically NARROWER, but no source describes a bounded window.  The
 * half-angle is passed in by the caller, which labels its own source.
 *
 * Pure function: no engine state, no player, no hasInterface.  The P80
 * headless probe calls it directly, and fnc_applyFusionOverlay calls it per
 * object.  acos is used, NOT acosDeg: the dedicated-server binary carries
 * acos and a bare absent token is a parse error that aborts the whole file.
 * The dot product is clamped to [-1, 1] because a rounded normalised pair
 * can exceed 1, and acos above 1 is NaN, which would make every comparison
 * false and paint the whole screen.
 *
 * Params:
 *   0: _eye (ARRAY position ASL) - the camera eye.
 *   1: _viewDir (ARRAY unit vector) - the camera look vector.
 *   2: _objPos (ARRAY position ASL) - the object centre.
 *   3: _halfAngleDeg (SCALAR) - the thermal channel half-angle in degrees.
 *
 * Returns: BOOL - true when the object is inside the field.
 */
params [
    ["_eye", [0, 0, 0], [[]], 3],
    ["_viewDir", [0, 1, 0], [[]], 3],
    ["_objPos", [0, 0, 0], [[]], 3],
    ["_halfAngleDeg", 20, [0]]
];

if (_halfAngleDeg >= 180) exitWith { true };

private _toObj = _objPos vectorDiff _eye;
private _range = vectorMagnitude _toObj;
if (_range <= 0.01) exitWith { true };

private _viewN = vectorNormalized _viewDir;
if ((vectorMagnitude _viewN) <= 0.01) exitWith { true };

private _cosOffset = ((vectorNormalized _toObj) vectorDotProduct _viewN) max -1 min 1;
// acos returns DEGREES on the Arma engine, so there is no radian conversion
// here.  Multiplying by 57.2957795 (a radians-to-degrees constant) scales
// every result past the half-angle and refuses the whole field, which the
// P80 probe measured directly.
private _offsetDeg = acos _cosOffset;

_offsetDeg <= _halfAngleDeg
