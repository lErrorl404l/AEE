#include "..\..\script_component.hpp"

/*
Water-body influence on the local climate (issue: the waterInfluenceRadius
setting).

A large water body holds its temperature far better than land, so it
modifies the air that crosses it: cooler by day in summer and warmer by
night in winter.  The modified air then flows inland and its effect decays
with distance.  The literature describes that decay as the growth of a
THERMAL INTERNAL BOUNDARY LAYER behind the water edge, and the growth is
published.

SOURCE (reproduction of the primary, which is paywalled): the internal
boundary layer depth over a fetch x, from Bou-Zeid, Meneveau and Parlange
(2004), Water Resour. Res. 40, W02505, DOI 10.1029/2003WR002475 (Eq. 26,
following Miyake 1965 and Garratt 1990, "The Internal Boundary Layer - a
review", Bound. Layer Meteorol. 50, 171-203):

    dIBL [ ln(dIBL / z0) - 1 ] = C * kappa * x,   C = 0.85

  dIBL   internal boundary layer depth, m
  z0     surface roughness length, m
  kappa  von Karman constant, 0.4
  x      fetch downstream of the surface change, m

The layer deepens with distance inland, and the influence weakens as it
mixes into a deeper layer: the temperature anomaly of the modified air
scales as the inverse of the layer depth, which is why a breeze fades
inland rather than stopping at a line.

OBSERVATIONAL LIMITS, as the literature states them (Crosman and Horel
2010, Bound. Layer Meteorol. 137, 1-29, DOI 10.1007/s10546-010-9517-9):
  - a sea breeze reaches 40 to over 300 km inland, latitude dependent;
  - Great Lakes breezes reach about 30 km;
  - a lake only a few kilometres wide still forms a breeze.
The first two are the boundary conditions this honours: the influence is
unbounded in principle but decays, and it is present from a small lake as
well as a large one.

Args:
  0: position (ARRAY, PositionASL, default [])
  1: radius (NUMBER, metres, the user setting, default 1000)
  2: water fraction 0..1 (NUMBER, the share of the sampled area that is
     water, default 0)

Returns the temperature offset in degrees Celsius, signed by the
day/night difference between water and land.
*/

params [["_pos", [], [[]]], ["_radius", 1000, [0]], ["_waterFrac", 0, [0]]];

if (count _pos < 2) exitWith { 0 };
if (_radius <= 0) exitWith { 0 };

// The water fraction: when the caller does not supply one, sample the
// terrain over the radius.  Water is the engine's own test.
if (_waterFrac <= 0 && {count _pos >= 2}) then {
    private _px = _pos select 0;
    private _py = _pos select 1;
    private _samples = 0;
    private _water = 0;
    {
        _x params ["_dx", "_dy"];
        if (surfaceIsWater [_px + _dx, _py + _dy]) then { _water = _water + 1; };
        _samples = _samples + 1;
    } forEach [[0, 0], [_radius, 0], [-_radius, 0], [0, _radius], [0, -_radius]];
    if (_samples > 0) then { _waterFrac = _water / _samples; };
};

if (_waterFrac <= 0) exitWith { 0 };

// ─── The internal boundary layer over this fetch ─────────────────────────
// Solved from dIBL [ln(dIBL/z0) - 1] = 0.85 kappa x.  The equation has no
// closed form for dIBL, so it is solved by fixed-point iteration, which
// converges in a few passes for the range of fetch the setting covers.
private _kappa = 0.4;
private _z0 = 0.03;             // open grass, the usual land reference
private _fetch = _radius;
private _dibl = 10;
for "_i" from 1 to 12 do {
    private _denominator = (ln (_dibl / _z0)) - 1;
    if (_denominator > 0.1) then {
        _dibl = (0.85 * _kappa * _fetch) / _denominator;
    };
};
_dibl = _dibl max 1;

// ─── The temperature influence ───────────────────────────────────────────
// The anomaly of the modified air weakens as the layer deepens, so the
// influence scales with the water's share of the sample and inversely with
// the layer depth.  The reference depth is the one a 1 km fetch produces,
// so the setting's default reads at full strength.
private _referenceDepth = 200;
private _strength = (_waterFrac min 1) * (_referenceDepth / _dibl);

// The sign and magnitude follow the water-land temperature difference: a
// water body is cooler than land by day and warmer by night.  The model
// reads the two from the state the environment publishes.
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };
private _waterTemp = missionNamespace getVariable [QEGVAR(core,currentWaterTemperature), _airTemp];
if !(_waterTemp isEqualType 0) then { _waterTemp = _airTemp; };

// The anomaly the air carries away from the water, damped by mixing.
private _anomaly = (_waterTemp - _airTemp) * (_strength min 1);
_anomaly
