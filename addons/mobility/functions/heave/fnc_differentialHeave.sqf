#include "..\..\script_component.hpp"

/*
Differential frost heave between two moisture states (issue #20).

A road drains and a field holds water, so the two surfaces carry different
volumetric water contents over the same frost depth.  The heave of each is the
two-term value of fnc_calculateFrostHeave; the differential is their
difference, and it is the quantity that cracks roads and tilts foundations.

    H(theta) = (rho_w / rho_i - 1) * theta * z
             + (rho_w / rho_i) * SP * grad T * t
    dH       = |H(theta_field) - H(theta_road)|

The moisture contents are supplied by the caller: AEE holds no sourced
per-surface moisture table, so the model does not invent one.  Sources for the
form: TM 5-852-6 / AFR 88-19 Vol 6 (1988); Konrad and Morgenstern (1981).

Args:
  0: material class (STRING, default "ground") - sets the segregation potential
  1: frost depth z (NUMBER, metres, default 0)
  2: temperature gradient across the frozen soil (NUMBER, degC/m, default 0)
  3: freezing duration t (NUMBER, seconds, default 0)
  4: field volumetric water content theta (NUMBER, default 0)
  5: road volumetric water content theta (NUMBER, default 0)
  6: heave multiplier (NUMBER, default 1)

Returns [dH, H_field, H_road] in metres.
Public: No
*/

params [
    ["_soil", "ground", [""]],
    ["_frostDepthM", 0, [0]],
    ["_gradientCPerM", 0, [0]],
    ["_durationS", 0, [0]],
    ["_thetaField", 0, [0]],
    ["_thetaRoad", 0, [0]],
    ["_multiplier", 1, [0]]
];

if (_frostDepthM <= 0) exitWith { [0, 0, 0] };

// The segregation potential for the soil class; the one sourced value (Devon
// silt, Konrad and Morgenstern 1981) applies to the silt-bearing classes.
private _soilLower = toLower _soil;
private _sp = 1.0e-9;
if ((_soilLower == "rock") || (_soilLower == "gravel") || (_soilLower == "vegetation") || (_soilLower == "water")) then {
    _sp = 0;
};

private _ratio = 999.84 / 916.8;
private _expansion = _ratio - 1;
private _segUnit = 0;
if (_sp > 0 && _gradientCPerM > 0 && _durationS > 0) then {
    _segUnit = _ratio * _sp * _gradientCPerM * _durationS;
};

private _hField = ((_expansion * _thetaField * _frostDepthM) + _segUnit) * _multiplier;
private _hRoad  = ((_expansion * _thetaRoad  * _frostDepthM) + _segUnit) * _multiplier;

[abs (_hField - _hRoad), (_hField max 0), (_hRoad max 0)]
