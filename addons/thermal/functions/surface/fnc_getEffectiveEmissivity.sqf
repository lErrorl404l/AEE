#include "..\..\script_component.hpp"
/*
Effective LWIR emissivity of a surface that may be wet (pure).

A thin water film raises a surface's long-wave emissivity toward the
liquid-water value.  The dry value comes from the material registry
(fnc_getMaterialThermal); this kernel blends it toward the water value by
the surface wetness.

WATER_EPS = 0.96 is the liquid-water LWIR emissivity.  Sources: Incropera
(Fundamentals of Heat and Mass Transfer, water emissivity); Hale and Querry
1973, Applied Optics 12(3):555, DOI 10.1364/AO.12.000555; Downing and
Williams 1975, J. Geophys. Res. 80(12):1656, DOI 10.1029/JC080i012p01656.
A wet film converges toward the water value (Lavielle et al. 2024, Adv.
Funct. Mater., DOI 10.1002/adfm.202403316).

The linear film-coverage blend itself is a declared model and is UNSOURCED;
it is recorded in the per-constant register.  The result is clamped to 0..1,
so a computed emissivity can never exceed unity.

Arguments:
  0: _epsDry  (NUMBER) dry-surface LWIR emissivity, 0..1
  1: _wetness (NUMBER) surface wetness, 0..1

Return Value: NUMBER - effective LWIR emissivity, 0..1.
Public: No
*/

#define WATER_EPS 0.96

params [
    ["_epsDry", 0.92, [0]],
    ["_wetness", 0, [0]]
];

private _w = (_wetness max 0) min 1;
private _eps = _epsDry + ((WATER_EPS - _epsDry) * _w);

(_eps max 0) min 1
