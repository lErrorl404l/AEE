#include "..\..\script_component.hpp"

/*
Terrain wind speed-up (issue: the windTerrainInfluence setting).

Wind accelerates over a ridge crest and slows in the lee. The effect is
published and this computes it rather than scaling a curve.

SOURCE (reproductions of the primary papers, which are paywalled):
Taylor, P.A., Walmsley, J.L. & Salmon, J.R. (1983) and Taylor & Lee
(1984), "Simple guidelines for estimating wind speed variations due to
small-scale topographic features", Climatological Bulletin 18(2) 3-32.
The maximum fractional speed-up over a hill crest:

    dS = 2 * (h / L) * sigma

  dS     fractional speed-up, du / u0
  h      hill height above the surrounding terrain, m
  L      hill half-length, the horizontal distance from the crest to the
         half-height point, m
  sigma  a shape factor: about 1 for an ideal two-dimensional ridge and
         about 0.8 for rolling sinusoidal terrain

VALIDITY, as the sources state it: h/L below 0.5 (Taylor & Lee 1984).
Jackson and Hunt (1975) apply a stricter limit, h/L below 0.05, for their
linear theory. The form is used here up to 0.5 and clamped beyond it,
rather than extrapolated.

The Froude number enters the literature as a REGIME parameter (F_L =
U0 / (N L); F_L much greater than one inertial, much less than one
buoyant).  No canonical closed-form Froude correction to the speed-up was
found, so none is applied, and that is recorded rather than approximated.

Args:
  0: position (ARRAY, PositionASL, default [])
  1: strength 0..1 (NUMBER, the user setting, default 0.6)

Returns the wind multiplier (1.0 for flat ground, above 1 at a crest,
below 1 in the lee). The caller multiplies the wind vector by it.
*/

params [["_pos", [], [[]]], ["_strength", 0.6, [0]]];

if (count _pos < 2) exitWith { 1 };
if (_strength <= 0) exitWith { 1 };

// ─── Terrain relief around the position ──────────────────────────────────
// The hill is measured over a 1 km baseline, which is the scale the
// guideline is written for: the half-length of a feature that produces
// speed-up, not a single terrain cell.
private _step = 500;
private _x = _pos select 0;
private _y = _pos select 1;
private _centre = getTerrainHeightASL _pos;
private _upwind = getTerrainHeightASL [_x - _step, _y, 0];
private _downwind = getTerrainHeightASL [_x + _step, _y, 0];
private _side = (getTerrainHeightASL [_x, _y - _step, 0]
    + getTerrainHeightASL [_x, _y + _step, 0]) / 2;

// The height above the surrounding terrain: how far the position stands
// out from its neighbours.  A crest reads positive, a valley negative.
private _relief = _centre - ((_upwind + _downwind + _side) / 3);
private _height = abs _relief;

// The hill half-length: the distance over which the height falls to half
// the crest value.  Sampled by walking outward until that happens.
private _halfLength = _step;
for "_i" from 1 to 4 do {
    private _d = _i * _step;
    private _h = getTerrainHeightASL [_x - _d, _y, 0];
    if ((abs (_centre - _h)) >= _height / 2) exitWith {
        _halfLength = _d;
    };
};

// ─── The published speed-up ──────────────────────────────────────────────
private _ratio = _height / (_halfLength max 1);
// The form is stated for h/L below 0.5; clamp rather than extrapolate.
private _ratioClamped = _ratio min 0.5;

// The shape factor: 1 for an ideal ridge, 0.8 for rolling terrain.  A
// symmetric feature reads nearer 1 and an irregular one nearer 0.8, so
// the asymmetry between the upwind and downwind drop decides it.
private _asymmetry = abs (_upwind - _downwind) / (_height max 1);
private _sigma = 1 - 0.2 * (_asymmetry min 1);

private _speedup = 2 * _ratioClamped * _sigma;

// The sign: on the upwind side the flow is accelerating toward the crest,
// in the lee it has separated and slowed.  The height above the upwind
// point tells which side the position is on.
private _signed = if (_centre >= _upwind) then { _speedup } else { -_speedup * 0.5 };

// The user setting scales the whole effect.
_signed = _signed * (_strength min 1);

// A multiplier cannot be negative: a lee cannot reverse the wind, it only
// slows it.
(1 + _signed) max 0.3
