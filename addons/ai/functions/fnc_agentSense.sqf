#include "..\script_component.hpp"

/*
Agent sense kernel (reusable AI substrate).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Stage 1 of
the four-stage model.  Reads the local stimuli into the state array the
decide stage consumes: the disturbance magnitude at the agent, the proximity
of the nearest player as 1 at the sense range and 0 beyond it, and the
agent's own need pressure.

Arguments:
  0: Number - disturbance magnitude at the agent, 0 to 1
  1: Number - distance to the nearest player, metres
  2: Number - the agent's own need pressure, 0 to 1
  3: Array  - the senses, index 0 is the sense range in metres

Returns:
  Array - [disturbance, proximity, needPressure]
*/

params [
    ["_disturbance", 0, [0]],
    ["_playerDistance", 1e10, [0]],
    ["_needPressure", 0, [0]],
    ["_senses", [], [[]]]
];

private _range = 1e10;
if ((count _senses) > 0) then {
    _range = _senses select 0;
};

private _proximity = 1 - ((_playerDistance min _range) / (_range max 0.000001));

[_disturbance, ((_proximity max 0) min 1), _needPressure]
