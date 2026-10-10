#include "..\..\script_component.hpp"

/*
Lahar (volcanic mudflow) initiation risk (model).

A lahar is a Bingham plastic flow: it moves only when the driving stress from
the sloping, water-saturated deposit exceeds the yield strength.  Rain on
loose pyroclastic deposits is the trigger, so the risk is the product of the
water supply, the available loose material, the activity and the slope.

The rainfall threshold is the rain-triggered lahar threshold measured on the
Pinatubo pyroclastic fans (about 25 mm/h).  The product-of-factors form is a
MODELLING CHOICE anchored on that threshold and the Bingham physics; the
yield strength and bulk density are the lahar rheology constants.

Sources: Pierson, T.C. & Costa, J.E. (1987) "A rheologic classification of
subaerial sediment-water flows", GSA Reviews in Engineering Geology 7:1-12;
Major, J.J. et al. (2005) rain-triggered lahars at Mount Pinatubo; issue #25.

Arguments:
  0: Volcanic activity index (NUMBER, 0..1)
  1: Rainfall intensity (NUMBER, mm/h)
  2: Loose pyroclastic deposit thickness (NUMBER, m)
  3: Slope angle (NUMBER, degrees)

Return Value: HashMap
  risk        0..1 lahar initiation risk
  water       water-supply factor 0..1
  material    loose-material factor 0..1
  slope       slope factor 0..1
Example: [0.8, 40, 2, 20] call aee_atmos_fnc_calculateLaharRisk
Public: No
*/

params [
    ["_activityIndex", 0, [0]],
    ["_rainRateMMH", 0, [0]],
    ["_depositThickness", 0, [0]],
    ["_slopeDeg", 0, [0]]
];

// ─── Water supply — rain-triggered threshold (25 mm/h) ──────────────────────
private _threshold = 25;
private _water = ((_rainRateMMH max 0) / _threshold) min 1;

// ─── Loose material — 1 m of loose pyroclastic debris is the reference ──────
private _material = ((_depositThickness max 0) / 1.0) min 1;

// ─── Slope — the driving stress must beat the yield stress ──────────────────
// Full factor at 15 deg; flat ground cannot run out.
private _slope = ((_slopeDeg max 0) / 15) min 1;

private _activity = (_activityIndex max 0) min 1;

private _risk = (_water * _material * _slope * _activity) max 0 min 1;

createHashMapFromArray [
    ["risk", _risk],
    ["water", _water],
    ["material", _material],
    ["slope", _slope]
]
