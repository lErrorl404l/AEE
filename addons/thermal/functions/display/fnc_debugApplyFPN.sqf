#include "..\..\script_component.hpp"
/*
In-game FPN material test (issue #204).

Applies the perlinNoise FPN test material (test_fpn_red.rvmat) to the
cursorTarget's first material slot, so the thermal image can be inspected
for the spatial mottle the procedural noise should add over the heat colour.

Usage (debug console):
    [] call aee_thermal_fnc_debugApplyFPN;

Restores the original material after _duration seconds.  If the composite
reads right (heat colour + static mottle) the FPN stage is promoted into
the production rvmat; if the noise kills the colour, perlinNoise is not
a viable detail stage for the Normal shader.
*/
params [["_duration", 30, [0]]];
private _obj = cursorTarget;
if (isNull _obj) exitWith {
    systemChat "AEE FPN test: no cursorTarget";
};

private _oldMats = getObjectMaterials _obj;
private _selection = 0;
_obj setObjectMaterial [_selection, "\z\aee\addons\thermal\data\test_fpn_red.rvmat"];
systemChat format ["AEE FPN test: applied to %1 sel %2 (orig %3)", typeOf _obj, _selection, _oldMats select _selection];

[
    {
        params ["_obj", "_selection", "_oldMats"];
        if (!isNull _obj) then {
            _obj setObjectMaterial [_selection, _oldMats select _selection];
        };
        systemChat "AEE FPN test: restored";
    },
    [_obj, _selection, _oldMats],
    _duration
] call CBA_fnc_waitAndExecute;
