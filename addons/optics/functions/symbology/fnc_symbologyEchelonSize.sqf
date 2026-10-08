#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyEchelonSize
 *
 * Pure echelon-overlay size kernel.  PURE: the frame half-width arrives as an
 * argument, so the kernel reads no marker and no world.
 *
 * The engine STRETCHES a marker texture into its box and does not keep the
 * texture aspect (feedback T170754), so the 64 x 128 echelon texture must be
 * drawn in a 1:2 box to render 2:1 tall.  A square box squashes it and the
 * ticks land inside the frame; a 1:2 box puts the ticks ABOVE the frame, per
 * APP-6 field B.  The two boxes share the frame's half-width so they align.
 *
 * Arguments:
 *   0: _halfWidth <NUMBER> the frame marker's a-axis half-width
 *
 * Return: <ARRAY> [a-axis, b-axis] for setMarkerSize, the b-axis twice the a.
 */
params [
    ["_halfWidth", 1, [0]]
];

if (_halfWidth <= 0) then { _halfWidth = 1; };

[_halfWidth, _halfWidth * 2]
