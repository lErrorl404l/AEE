#include "..\..\script_component.hpp"
/*
Resolvability of a thermal selection, in the display band position (issue #215 family).

WHY THIS EXISTS.  fnc_evaluateThermalEdge decides a local-contrast edge and its
own header states that contrast detection is NECESSARY AND NOT SUFFICIENT.
fnc_resolveThermalTarget supplies the missing spatial half.  This function joins
the two into the one number the paint path needs: the fraction of the target's
own contrast the sensor can actually show.  A selection that fails either test
must stop reading as a distinct target and must fall toward its local background.

THE BLEND.  The display paints one scalar per selection: the normalised band
position _b, which fnc_applySelectionThermal maps through fnc_thermalPalette.
This function returns a visibility in 0..1 and the caller blends in that SAME
band-position domain:

    bEffective = bBackground + (bSelection - bBackground) * visibility

That is the physics-honest reading.  A pixel is not painted by the target alone.
The detector integrates over its instantaneous field of view, so an unresolved
target shares its pixel with the background.  The painted value is the
area-weighted mean of the two, which is exactly the linear blend above with
visibility as the resolved area fraction.  A visibility of 1 returns the
selection's own colour.  A visibility of 0 returns the local background colour.

THE CONTRAST TERM.  NETD is the signal-to-noise 1 point and the detection
threshold is a MULTIPLE of it (fnc_calculateSensorThreshold).  The ratio
contrast / threshold is therefore the target's signal-to-noise against the
detection margin.  It is 1 or more when the edge passes and falls toward 0 as
the contrast falls below the margin.  A ratio below 1 denotes a target the
sensor cannot separate from its noise, so it is pulled toward the background.

THE SPATIAL TERM.  Below the Johnson detection level (1.0 line pair, STANAG
4347 Ed. 1) the target is only partly resolved.  The line-pair count over the
1.0 line-pair detection criterion is the resolved fraction.  The sub-pixel
signal-to-noise path in fnc_resolveThermalTarget already returns level 1 when
it detects the target, and that arrival is reported as resolvable, so the term
is 1 whenever the spatial kernel resolves.

Guards, each explicit:
  - A non-positive threshold is not a sensor property.  The caller refuses the
    device and substitutes the documented reference.  This function returns 1
    rather than divide by zero, so a bad threshold can never blank the scene.
  - The contrast ratio and the spatial fraction are clamped to 0..1.  A value
    above 1 is saturation and shows no more detail.

Units on every line: _contrast and _threshold are normalised relative radiance
contrasts on 0..1.  _linePairs is a Johnson line-pair count.  The return is a
dimensionless resolved fraction on 0..1.

Arguments:
  0: _contrast   (NUMBER) the local contrast from fnc_evaluateThermalEdge, 0..1
  1: _threshold  (NUMBER) the sensor threshold from fnc_calculateSensorThreshold
  2: _resolvable (BOOL) the spatial verdict from fnc_resolveThermalTarget
  3: _linePairs  (NUMBER) the Johnson line-pair count from fnc_resolveThermalTarget

Return Value: NUMBER - the resolved fraction, 0..1.
Example: [0.001, 0.004349, true, 5] call aee_thermal_fnc_resolveThermalVisibility
Public: No
*/

params [
    ["_contrast", 0, [0]],
    ["_threshold", 0.004349, [0]],
    ["_resolvable", false, [false]],
    ["_linePairs", 0, [0]]
];

// The contrast against the sensor margin.  A threshold at or below zero is not
// a sensor property, so the target keeps full contrast instead of dividing by
// zero.  The caller substitutes the documented reference in that case.
private _contrastVis = 1;
if (_threshold > 0) then {
    _contrastVis = ((_contrast / _threshold) max 0) min 1;
};

// The spatial fraction.  The Johnson detection level is one line pair, so the
// line-pair count over that criterion is the resolved part of the target.  A
// target the spatial kernel resolved keeps full contrast even if it is a
// sub-pixel source that passed on signal-to-noise.
private _spatialVis = 1;
if (!_resolvable) then {
    _spatialVis = _linePairs max 0 min 1;
};

_contrastVis * _spatialVis
