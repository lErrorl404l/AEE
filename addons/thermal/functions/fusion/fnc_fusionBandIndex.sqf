#include "..\..\script_component.hpp"
/*
 * Fusion display band index (issue #204, Track B ENVG-B).
 *
 * The fusion channel is its own 8-bit grey display: the AGC-normalised
 * brightness b in 0..1 is quantised to one of the 256 emissive rvmats.
 * This is NOT the 32-step thermal palette quantiser.  A real microbolometer
 * display is 8-bit grey, the modelled detectors are 320x240 and 640x480,
 * and the ladder is the fusion channel's own display.
 *
 * Pure function: no engine state, no player, no hasInterface.  The P80
 * headless probe calls it directly, and fnc_applyFusionOverlay calls it
 * per selection so the two cannot disagree on the quantiser.
 *
 * A non-finite input returns 0.  SQF min/max and comparisons are false on
 * NaN, so a NaN that reached round() would be non-deterministic.  A bad
 * input maps to the darkest band, which is the safe reading.
 *
 * Params:
 *   0: _b (SCALAR) - AGC-normalised brightness, nominally 0..1.
 *
 * Returns: SCALAR - band index 0..255.
 */
params [["_b", 0, [0]]];

if !(finite _b) exitWith { 0 };

_b = _b max 0 min 1;
round (_b * 255)
