#include "..\..\script_component.hpp"
/*
Green-Ampt infiltration from the Rawls et al. 1983 parameters (issue #24).

The Curve Number predicts runoff directly. Green-Ampt gives the infiltration
physics: how fast the wetting front moves into the soil, and how much water
the soil has taken. The mod's model stack puts Green-Ampt over Horton because
it reuses the soil state the mod already keeps. The cumulative infiltration F
IS that state, so the model needs no extra clock.

The paper's integrated form, with the front at the surface at t = 0:

  f = K * (1 + psi * dTheta / F)                      rate, mm/h
  t = (F - psi*dTheta * ln(1 + F/(psi*dTheta))) / K   time to reach F, hours

F is the cumulative infiltration in mm. dTheta is the EFFECTIVE porosity minus
the initial water content:

  dTheta = theta_e - theta_i

theta_e is the table's effective porosity, NOT the total porosity. The
difference is measurable: for sand, F = 50 mm gives t = 0.2089 h with
theta_e = 0.417, but t = 0.2046 h with the total porosity 0.437. This
function uses theta_e.

Source: Rawls, Brakensiek and Miller (1983), "Green-Ampt infiltration
parameters from soils data", J. Hydraulic Eng. 109(1):62-70, Table 2. The
issue converted psi from cm to mm (x10) and K from cm/h to mm/h (x10).
TUFLOW's copy of the same table swaps the loam and silt-loam K values and is
the one that is wrong. These are the Rawls values.

The soil is named by a texture class, or by the material class that
aee_material_fnc_classifyBySurfaceType returns. A caller that has already
resolved the surface passes that class and needs no second lookup.

Args:
  0: cumulative infiltration F (NUMBER, mm, default 0)
  1: soil texture or material class (STRING, default "loam")
  2: initial water content theta_i (NUMBER, 0..1, default 0)

Returns [rate_mmPerH, F_mm, t_h].
*/

params [["_F", 0, [0]], ["_soil", "loam", [""]], ["_thetaI", 0, [0]]];

// Rawls, Brakensiek and Miller 1983, Table 2. [theta_e, psi_mm, K_mm_per_h].
private _TEXTURE = createHashMapFromArray [
    ["sand",            [0.417,  49.5, 117.8]],
    ["loamy sand",      [0.401,  61.3,  29.9]],
    ["sandy loam",      [0.412, 110.1,  10.9]],
    ["loam",            [0.434,  88.9,   3.4]],
    ["silt loam",       [0.486, 166.8,   6.5]],
    ["sandy clay loam", [0.330, 218.5,   1.5]],
    ["clay loam",       [0.309, 208.8,   1.0]],
    ["silty clay loam", [0.432, 273.0,   1.0]],
    ["sandy clay",      [0.321, 239.0,   0.6]],
    ["silty clay",      [0.423, 292.2,   0.5]],
    ["clay",            [0.385, 316.3,   0.3]]
];

// Material class -> nearest texture class. The material classifier is the
// hydrology's own surface source, so a caller can pass its result directly.
// Rock and the paved covers are near-impervious and take the lowest-K soil.
// Vegetation litter holds more water than mineral soil.
private _MATERIAL = createHashMapFromArray [
    ["ground",     "loam"],
    ["rock",       "clay"],
    ["gravel",     "sandy loam"],
    ["vegetation", "silt loam"],
    ["concrete",   "clay"],
    ["asphalt",    "clay"],
    ["metal",      "clay"],
    ["water",      "silty clay"]
];

if !(_F isEqualType 0) then { _F = 0; };
if !(_thetaI isEqualType 0) then { _thetaI = 0; };
if !(_soil isEqualType "") then { _soil = "loam"; };

private _key = toLower _soil;
if (!(_key in _TEXTURE) && {_key in _MATERIAL}) then {
    _key = _MATERIAL get _key;
};
private _props = _TEXTURE getOrDefault [_key, _TEXTURE get "loam"];
_props params ["_thetaE", "_psi", "_k"];

_F = _F max 0;
// The initial content cannot exceed the pore space the front can fill.
_thetaI = _thetaI max 0 min _thetaE;
private _dTheta = (_thetaE - _thetaI) max 1e-6;
private _psiDtheta = _psi * _dTheta;

// The rate is singular as F -> 0: the front starts at the surface and the
// head gradient is unbounded. A floor keeps the division finite. The floor
// is small enough that f(F -> 0+) stays far above K, which is the behaviour
// the model must show.
private _fF = _F max 1e-6;
private _rate = _k * (1 + (_psiDtheta / _fF));
private _t = (_F - (_psiDtheta * ln (1 + (_F / _psiDtheta)))) / _k;

[_rate, _F, _t]
