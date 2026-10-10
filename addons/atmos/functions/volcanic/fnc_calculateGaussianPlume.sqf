#include "..\..\script_component.hpp"

/*
Steady-state Gaussian plume dispersion (kernel).

Concentration from a continuous elevated point source.  Briggs (1973)
open-country dispersion coefficients give sigma_y and sigma_z from the
downwind distance and the Pasquill stability class.

  C = Q / (2*pi*u*sy*sz)
      * exp(-y^2 / (2*sy^2))
      * [ exp(-(z-H)^2 / (2*sz^2)) + exp(-(z+H)^2 / (2*sz^2)) ]

Sources: Briggs, G.A. (1973) USAEC Report ATDL-106; Pasquill, F. (1961)
Meteor. Mag. 90:33-49; Gifford, F.A. (1961) Nucl. Safety 2:56-59.

Arguments:
  0: Source strength Q (NUMBER, per second; return carries the same mass unit)
  1: Wind speed u (NUMBER, m/s)
  2: Pasquill stability class (STRING, "A".."F", default "D")
  3: Effective release height H (NUMBER, m above ground)
  4: Downwind distance x (NUMBER, m)
  5: Crosswind distance y (NUMBER, m)
  6: Receptor height z (NUMBER, m)

Return Value: NUMBER: concentration C (per m3, same mass unit as Q)
Example: [1, 5, "D", 100, 1000, 0, 0] call aee_atmos_fnc_calculateGaussianPlume
Public: No
*/

params [
    ["_emissionRate", 0, [0]],
    ["_windSpeed", 5, [0]],
    ["_stability", "D", [""]],
    ["_sourceHeight", 0, [0]],
    ["_downwind", 0, [0]],
    ["_crosswind", 0, [0]],
    ["_height", 0, [0]]
];

if (_emissionRate <= 0 || _windSpeed <= 0 || _downwind <= 0) exitWith { 0 };

// ─── Briggs open-country dispersion coefficients (x and sigma in metres) ────
private _x = _downwind;
private _syC = 0.08;     // class D defaults
private _szC = 0.06;
private _szD = 0.0015;
private _szExp = -0.5;
switch (_stability) do {
    case "A": { _syC = 0.22; _szC = 0.20;  _szD = 0;      _szExp = -0.5; };
    case "B": { _syC = 0.16; _szC = 0.12;  _szD = 0;      _szExp = -0.5; };
    case "C": { _syC = 0.11; _szC = 0.08;  _szD = 0.0002; _szExp = -0.5; };
    case "E": { _syC = 0.06; _szC = 0.03;  _szD = 0.0003; _szExp = -1;   };
    case "F": { _syC = 0.04; _szC = 0.016; _szD = 0.0003; _szExp = -1;   };
    default   { _syC = 0.08; _szC = 0.06;  _szD = 0.0015; _szExp = -0.5; };
};

private _sy = _syC * _x * ((1 + 0.0001 * _x) ^ -0.5);
private _sz = _szC * _x * ((1 + _szD * _x) ^ _szExp);
if (_sy <= 0 || _sz <= 0) exitWith { 0 };

// ─── Gaussian concentration with ground reflection ──────────────────────────
private _H = _sourceHeight;
private _z = _height;
private _lateral = exp(-(_crosswind * _crosswind) / (2 * _sy * _sy));
private _vertical = exp(-((_z - _H) ^ 2) / (2 * _sz * _sz))
                  + exp(-((_z + _H) ^ 2) / (2 * _sz * _sz));

(_emissionRate / (2 * pi * _windSpeed * _sy * _sz)) * _lateral * _vertical
