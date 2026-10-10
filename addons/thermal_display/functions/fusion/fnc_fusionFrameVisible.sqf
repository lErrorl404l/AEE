#include "..\..\script_component.hpp"
/*
 * Fusion frame visibility decision (issue #204, Track B ENVG-B).
 *
 * The thermal-channel frame is a HUD aid, not optics.  It shows where the
 * fused image is bounded, and that is only meaningful when the thermal
 * channel is genuinely NARROWER than the NVG device's field.  At a ratio at
 * or near 1 the four bars sit on the safe-zone edge and read as a border
 * around the whole view instead of an inset (operator report 2026-10-03), so
 * this decision returns false and FUNC(updateFusionFrame) tears the display
 * down.
 *
 * The ratio comes from FUNC(fusionFrameGeometry); this function only applies
 * the threshold, so the two can be pinned separately.  It is pure: no engine
 * state, no display, no hasInterface.  The headless suite executes it.
 *
 * Params:
 *   0: _ratio (SCALAR)    - on-screen half-extent as a fraction of safeZoneH.
 *   1: _minInset (SCALAR) - the smallest ratio that still reads as an inset.
 *
 * Returns: BOOL - true when the frame must be drawn.
 */
params [
    ["_ratio", 1, [0]],
    ["_minInset", 0.97, [0]]
];

if (!(_ratio isEqualType 0)) then { _ratio = 1; };
if (!(_minInset isEqualType 0) || (_minInset <= 0) || (_minInset > 1)) then {
    _minInset = 0.97;
};

(_ratio > 0) && (_ratio < _minInset)
