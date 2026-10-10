#include "..\..\script_component.hpp"
/*
Soil erodibility K factor (RUSLE, issue #21).

K is the soil's inherent susceptibility to detachment and transport. The
RUSLE predicts it from the particle-size distribution with the nomograph
(Renard et al. 1997, USDA Agriculture Handbook 703, equation 3-2):

  K = [2.1e-4 * M^1.14 * (12 - a) + 3.25 * (b - 2) + 2.5 * (c - 3)] / 100
  M = (%silt + %very fine sand) * (100 - %clay)

with a = % organic matter, b = structure code (1..4), c = permeability
class (1..6). Where the full particle-size data are not held, the standard
texture-class values at average organic matter are used, from Wall, Coote,
Pringle and Shelton (1997) OMAFRA Factsheet 23-005 (formerly 97-005),
Table 2.

The caller passes a USDA texture class name. The value returned is K in
t*ha*h/(ha*MJ*mm), the RUSLE K unit.

Args:
  0: USDA texture class (STRING, default "loam")

Returns K.

Example:
  ["silt loam"] call aee_hydrology_fnc_calculateSoilErodibility -> 0.38
*/

params [["_texture", "loam", [""]]];

if !(_texture isEqualType "") then { _texture = "loam"; };
private _key = toLower _texture;

// OMAFRA 23-005 Table 2, average organic matter. [texture, K].
private _table = [
    ["clay",            0.22],
    ["clay loam",       0.30],
    ["loam",            0.30],
    ["silt loam",       0.38],
    ["silty clay",      0.26],
    ["silty clay loam", 0.32],
    ["sandy loam",      0.13],
    ["loamy sand",      0.04],
    ["sand",            0.02],
    ["fine sandy loam", 0.18],
    ["very fine sand",  0.43],
    ["heavy clay",      0.17]
];

private _k = 0.30;   // loam is the mid-range default for an unknown texture
private _n = count _table;
for "_i" from 0 to (_n - 1) do {
    if (((_table select _i) select 0) == _key) then {
        _k = (_table select _i) select 1;
    };
};

_k
