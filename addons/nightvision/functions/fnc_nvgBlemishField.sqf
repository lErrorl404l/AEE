#include "..\script_component.hpp"

/*
Blemish overlay strength for the tube blemish texture.

The blemish texture carries dark spots, bright emission points and the
fixed-pattern mottle.  Its strength is the ctrlSetFade alpha: a heavier
blemish field means a more opaque overlay.

Arguments:
  0: Number - tier index (0 GEN1 .. 3 PVS31)
  1: Number - tube noise in [0, 1]
  2: Number - overlay strength

Returns:
  Number - overlay strength in [0, 1].
*/

params [
    ["_tierIdx", 0, [0]],
    ["_noise", 0, [0]],
    ["_strength", 0.5, [0]]
];

// Per-tier base alpha, heaviest first (oldest tube).  UNSOURCED: the ORDER
// follows the MIL-I-49428 Table III dark-spot density; the normalised alpha
// is a modelling choice.
private _base = [0.85, 0.55, 0.30, 0.15] select ((_tierIdx max 0) min 3);

// A noisier tube shows its blemishes more.
private _raw = _strength * _base * (0.5 + 0.5 * ((_noise max 0) min 1));

(0 max _raw) min 1
