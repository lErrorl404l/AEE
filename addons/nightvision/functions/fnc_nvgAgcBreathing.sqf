#include "..\script_component.hpp"

/*
AGC breathing factor.

The AGC hunts around its target gain.  MIL-I-49428 section 3.6.6 bounds the
fluctuation at +/-10 percent and the drift at +/-15 percent over two
minutes.  This kernel returns a small brightness factor the parent applies
to the AGC output.

Arguments:
  0: Number - current gain
  1: Number - target gain
  2: Number - mission time, seconds
  3: Number - strength in [0, 1]

Returns:
  Number - brightness factor in [-0.15, 0.15].
*/

params [
    ["_gain", 0, [0]],
    ["_gainTarget", 1, [0]],
    ["_timeSec", 0, [0]],
    ["_strength", 0, [0]]
];

private _err = (abs (_gainTarget - _gain)) / ((abs _gainTarget) max 1);
// The 3.0 rad/s oscillation frequency is UNSOURCED: the section 3.6.6
// tolerance bounds the amplitude, not the frequency.  The 0.10 amplitude is
// the section 3.6.6 fluctuation envelope, and the 0.15 clamp is the drift
// envelope.
private _osc = sin (_timeSec * 3.0);
private _raw = _strength * 0.10 * _osc * (_err min 1);

// Clamp written as (max lower) then (min upper): a leading negative literal
// in `-0.15 max _raw` is parsed as a unary minus over the whole right side.
(_raw max -0.15) min 0.15
