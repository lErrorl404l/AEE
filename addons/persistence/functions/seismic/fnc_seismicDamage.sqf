#include "..\..\script_component.hpp"

/*
Structural damage state from macroseismic intensity.

The damage thresholds follow the Modified Mercalli intensity scale
descriptions:

    MMI VI-VII   light damage
    MMI VIII-IX  moderate damage (partial collapse)
    MMI X+       heavy damage / collapse

Source: the Modified Mercalli intensity scale (Wood, H.O. and Neumann, F.
(1931) "Modified Mercalli intensity scale of 1931", Bulletin of the
Seismological Society of America 21(4):277-283).

The engine ceiling is recorded honestly: Arma exposes no structural-damage
state on map buildings, so this kernel only classifies intensity.  The caller
decides what, if anything, to apply (a damage animation, or marking a
collapsed structure impassable).

Input:  [_mmi] - Modified Mercalli intensity.
Output: [level, impassable] - 0 none, 1 light, 2 moderate, 3 collapse; and
        whether the structure is impassable.
Public: No
*/

params [["_mmi", 1, [0]]];

private _level = 0;
private _impassable = false;
if (_mmi >= 10) then {
    _level = 3;
    _impassable = true;
} else {
    if (_mmi >= 8) then {
        _level = 2;
    } else {
        if (_mmi >= 6) then { _level = 1; };
    };
};

[_level, _impassable]
