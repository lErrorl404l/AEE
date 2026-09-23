#include "..\..\script_component.hpp"
/*
Depression storage, the bucket fill-spill model (issue #24).

Water arriving at the surface does not run off at once. It fills the
micro-depressions first, and only the excess spills downhill. The bucket
model is the standard operational treatment: a store of capacity D_s
takes water until it is full, then passes everything beyond it.

  filled = min(D_s, stored + input)
  spill  = (stored + input) - filled

The representation is deliberate: depression storage is a STATE, not a
one-shot subtraction, so a second rain event on already-filled hollows
spills almost all of it. That is the behaviour a road shows after the
first shower.

Source: Chu et al. 2013, Water Resour. Res. 49; McDonnell 2021, WRR 57.
The fill-spill formulation is standard; the capacity is a setting because
it is a land-cover property, not a map property.

Args:
  0: current stored depth (NUMBER, mm, default 0)
  1: input (NUMBER, mm, default 0)
  2: capacity D_s (NUMBER, mm, default 5)

Returns [newStoredDepth_mm, spill_mm].
*/

params [["_stored", 0, [0]], ["_input", 0, [0]], ["_capacity", 5, [0]]];

if !(_stored isEqualType 0) then { _stored = 0; };
if !(_input isEqualType 0) then { _input = 0; };
if !(_capacity isEqualType 0) then { _capacity = 5; };
_stored = _stored max 0;
_capacity = _capacity max 0;

private _filled = (_stored + _input) min _capacity;
private _spill = ((_stored + _input) - _filled) max 0;

[_filled, _spill]
