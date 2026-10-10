#include "..\script_component.hpp"

/*
Survival action kernel (will to live).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Maps the
survival pressure to the action band the issue calibrates:

  0.0-0.3  normal combat behaviour
  0.3-0.6  seek cover, careful movement, call for resupply
  0.6-0.8  break contact, seek shelter, water or rest
  0.8-1.0  abandon the objective, route to survival

The lower edge of a band is inclusive, so 0.3 is band 1 and 0.8 is band 3.

Arguments:
  0: Number - the survival pressure, 0 to 1

Returns:
  Number - the action band: 0 normal, 1 cover, 2 break contact, 3 survival
*/

params [["_pressure", 0, [0]]];

private _p = (_pressure max 0) min 1;
private _action = 0;
if (_p >= 0.8) then {
    _action = 3;
} else {
    if (_p >= 0.6) then {
        _action = 2;
    } else {
        if (_p >= 0.3) then {
            _action = 1;
        };
    };
};

_action
