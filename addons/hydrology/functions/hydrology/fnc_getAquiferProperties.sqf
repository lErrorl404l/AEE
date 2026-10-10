#include "..\..\script_component.hpp"
/*
Aquifer properties for a ground material class (issue #26).

The water table and the spring discharge both need two properties of the
saturated zone: the SPECIFIC YIELD S_y, which converts a volume of stored
water to a rise of the water table, and the SATURATED HYDRAULIC
CONDUCTIVITY K_sat, which sets the spring flow.  Both are properties of the
lithology, so both come from one table keyed by the ground material class
that aee_material_fnc_classifyBySurfaceType returns.  The mod already uses
that class as the lithology key: fnc_calculateGreenAmptInfiltration is called
with the same value.

S_y values are the compilation of Johnson (1967) and the summary in Freeze
and Cherry (1979), Table 2.2.  K_sat values are Freeze and Cherry (1979),
Table 2.2.  The mod's classifier merges gravel into "rock" (free-draining
coarse material), so the rock row uses the gravel values.  A surface class
without a row is treated as clay, the least transmissive lithology, which is
the safe default: it understates the aquifer rather than inventing one.

Source: Johnson, A.I. (1967), "Specific yield - compilation of specific
yields for various materials", USGS Water-Supply Paper 1662-D.  Freeze, R.A.
and Cherry, J.A. (1979), "Groundwater", Prentice-Hall, Table 2.2.

Args:
  0: ground material class (STRING, default "ground")

Returns [specificYield, kSat_mPerDay].
*/

params [["_material", "ground", [""]]];

// [specific yield S_y, saturated conductivity K_sat in m/day]
private _table = createHashMapFromArray [
    ["rock",       [0.23, 1000.0]],   // gravel / fractured rock
    ["ground",     [0.21,   10.0]],   // sand, soil
    ["vegetation", [0.08,    0.1]],   // silt loam root-zone soil
    ["water",      [0.00,    0.0]],   // open water, no vadose zone
    ["concrete",   [0.03,    0.001]], // clay substrate under impervious cover
    ["asphalt",    [0.03,    0.001]],
    ["metal",      [0.03,    0.001]],
    ["glass",      [0.03,    0.001]],
    ["wood",       [0.03,    0.001]]
];

// An unknown class falls to clay, the least transmissive lithology.
_table getOrDefault [_material, [0.03, 0.001]]
