#include "..\..\script_component.hpp"
/*
Soil loss to vertical lowering (issue #21).

The RUSLE gives soil loss in tonnes per hectare per year. The observable
change is how fast the surface drops. For a soil of bulk density BD
(g/cm3), one hectare of soil one millimetre deep is

  1 ha = 10000 m2,  1 mm = 0.001 m,  volume = 10 m3
  mass = 10 m3 * BD (g/cm3) * 1000 (kg/m3 per g/cm3) = 10 * BD * 1000 kg
       = 10 * BD tonnes

so 10 * BD tonnes per hectare is 1 mm. Inverting:

  mm/yr = (t/ha/yr) / (10 * BD)

A typical mineral soil is BD = 1.3 g/cm3, so 10 t/ha/yr lowers the surface
by 0.77 mm/yr. Source: the unit conversion is the standard RUSLE
depth-of-soil-loss relation (Renard et al. 1997, USDA AH-703).

Args:
  0: soil loss (NUMBER, t/ha/yr, default 0)
  1: bulk density (NUMBER, g/cm3, default 1.3)

Returns the vertical lowering in mm/yr.

Example:
  [10, 1.3] call aee_hydrology_fnc_calculateErosionDepth -> 0.769
*/

params [["_soilLoss", 0, [0]], ["_bulkDensity", 1.3, [0]]];

if !(_soilLoss isEqualType 0) then { _soilLoss = 0; };
if !(_bulkDensity isEqualType 0) then { _bulkDensity = 1.3; };
_bulkDensity = _bulkDensity max 0.1;

(_soilLoss max 0) / (10 * _bulkDensity)
