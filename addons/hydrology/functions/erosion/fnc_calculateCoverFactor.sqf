#include "..\..\script_component.hpp"
/*
Cover-management C factor (RUSLE, issue #21).

C is the ratio of soil loss from a cropped or covered surface to the loss
from the bare fallow unit plot. It is the single largest lever in the
RUSLE: undisturbed forest sheds three orders of magnitude less soil than
bare ground.

Values are the standard RUSLE cover-management factors (Renard et al.
1997, USDA Agriculture Handbook 703, chapter 5; the representative values
in the issue text):

  bare fallow              1.0
  conventional row crop    0.36
  no-till row crop         0.10
  good pasture             0.003
  undisturbed forest       0.001   (range 0.0001-0.001)
  forest, 35-20% canopy    0.006   (range 0.003-0.009)

The caller passes a cover class name; the driver resolves the class from
the map's own surface and the seasonal vegetation density.

Args:
  0: cover class (STRING, default "bare")

Returns C (dimensionless).

Example:
  ["forest"] call aee_hydrology_fnc_calculateCoverFactor -> 0.001
*/

params [["_coverClass", "bare", [""]]];

if !(_coverClass isEqualType "") then { _coverClass = "bare"; };
private _key = toLower _coverClass;

// [cover class, C]. Keys are lowercase for the case-insensitive compare.
private _table = [
    ["bare",       1.0],
    ["barefallow", 1.0],
    ["crop",       0.36],
    ["rowcrop",    0.36],
    ["notill",     0.10],
    ["pasture",    0.003],
    ["forest",     0.001],
    ["forestopen", 0.006]
];

private _c = 1.0;   // bare fallow is the conservative default
private _n = count _table;
for "_i" from 0 to (_n - 1) do {
    if (((_table select _i) select 0) == _key) then {
        _c = (_table select _i) select 1;
    };
};

_c
