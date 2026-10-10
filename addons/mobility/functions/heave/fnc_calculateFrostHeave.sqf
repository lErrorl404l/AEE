#include "..\..\script_component.hpp"

/*
Frost heave magnitude (issue #20).

Two sourced mechanisms raise the ground when soil freezes.

1. IN-SITU (closed-system) heave.  The water already in the pores expands
   about 9 per cent on freezing and lifts the surface:

       H_in = (rho_w / rho_i - 1) * theta * z

   rho_w 999.84 kg/m3 at 0 C (IAPWS R6-95; Tanaka et al. 2001), rho_i 916.8
   kg/m3 at 0 C (CRC Handbook).  The ratio 999.84 / 916.8 - 1 = 0.0906.  The
   same 9 per cent is in TM 5-852-6 / AFR 88-19 Vol 6 (1988), para 2-2d, from
   62.4 / 57.2 lb/ft3.  theta is the volumetric water content and z the frost
   depth.

2. SEGREGATION (open-system) heave.  Water migrates to the freezing front and
   grows ice lenses; this is the dominant mechanism and the one that produces
   the metre-scale heave of frost-susceptible soils.  The segregation
   potential SP (Konrad and Morgenstern 1981, Can. Geotech. J. 18(4):482-491,
   DOI 10.1139/t81-059) gives the water-intake velocity

       v = SP * grad T

   over the temperature gradient across the frozen fringe.  Each unit volume
   of imported water becomes (rho_w / rho_i) of ice, so over a freezing
   duration t

       H_seg = (rho_w / rho_i) * SP * grad T * t

   Total: H = (H_in + H_seg) * multiplier, never negative.

theta is the same per-soil value the Stefan coefficient holds (#11 research:
de Vries 1963, Physics of Plant Environment; Incropera and DeWitt, Table A.3),
so the two models share one water-content source.  A paved or metal surface is
a cover over soil, not a soil itself, and takes the soil beneath, as the
Stefan coefficient does.

CEILING, recorded honestly: a general per-soil segregation-potential table
could NOT be sourced.  AEE ships the ONE measured value, the Devon silt range
6e-10 to 1.4e-9 m2/(s.degC) (Konrad and Morgenstern 1981, tables 1 and 2).  The
silt-bearing classes ("ground", and the soil beneath concrete, asphalt and
metal) take its lower bound; every other class carries SP 0 and its heave
reduces to the in-situ term.  So the open-system heave that dominates in
reality is reachable only where a soil's segregation potential is known, and
the issue's 5-30 cm open-system range is met only for those soils.

Sources: TM 5-852-6 / AFR 88-19 Vol 6 (1988); IAPWS R6-95; CRC Handbook;
Konrad and Morgenstern (1981); de Vries (1963); Incropera and DeWitt (2007).

Args:
  0: material class (STRING, default "ground") - the class
     aee_material_fnc_classifyBySurfaceType returns
  1: frost depth z (NUMBER, metres, default 0)
  2: temperature gradient across the frozen soil (NUMBER, degC/m, default 0)
  3: freezing duration t (NUMBER, seconds, default 0)
  4: heave multiplier (NUMBER, default 1)

Returns [H_total, H_in, H_seg] in metres.
Public: No
*/

params [
    ["_soil", "ground", [""]],
    ["_frostDepthM", 0, [0]],
    ["_gradientCPerM", 0, [0]],
    ["_durationS", 0, [0]],
    ["_multiplier", 1, [0]]
];

if (_frostDepthM <= 0) exitWith { [0, 0, 0] };

// Per-soil volumetric water content theta and segregation potential SP
// m2/(s.degC).  theta is the Stefan coefficient's own table; SP carries the
// one sourced value, the Devon silt lower bound.  A paved or metal surface
// takes the soil beneath, so it keeps the ground defaults.
private _soilLower = toLower _soil;
private _theta = 0.25;      // silt loam, the reference soil
private _sp = 1.0e-9;       // Devon silt (Konrad and Morgenstern 1981)
if ((_soilLower == "rock") || (_soilLower == "gravel")) then { _theta = 0.10; _sp = 0; };
if (_soilLower == "vegetation") then { _theta = 0.35; _sp = 0; };
if (_soilLower == "water") then { _theta = 1.00; _sp = 0; };

private _ratio = 999.84 / 916.8;          // rho_w / rho_i
private _expansion = _ratio - 1;          // 0.0906

private _inSitu = _expansion * _theta * _frostDepthM;
private _segregated = 0;
if (_sp > 0 && _gradientCPerM > 0 && _durationS > 0) then {
    _segregated = _ratio * _sp * _gradientCPerM * _durationS;
};

private _total = ((_inSitu + _segregated) * _multiplier) max 0;

[_total, _inSitu, _segregated]
