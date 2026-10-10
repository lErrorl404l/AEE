#include "..\..\script_component.hpp"

/*
Start or stop a CBRN agent release for the plume model (issue #105).

The plume driver (fnc_updateCbrnPlume) reads the release record this
function publishes.  A release is either a steady source (an emission
rate in mg/s) or an instantaneous burst (a released mass in mg); the
driver runs the Gaussian plume for the former and the Gaussian puff for
the latter.

Arguments:
  0: release position (ARRAY, ASL) - fewer than 3 elements stops the release
  1: agent (STRING, "VX"/"GB"/"GD"/"H"/"CG")
  2: strength (NUMBER) - steady emission mg/s, or burst mass mg
  3: effective height (NUMBER, m) above the source
  4: burst (BOOL) - true = instantaneous puff, false = steady plume

Returns the release record, or [] when stopped.
*/

params [
    ["_position", [], [[]]],
    ["_agent", "GB", [""]],
    ["_strength", 0, [0]],
    ["_altitude", 0, [0]],
    ["_burst", false, [true]]
];

if ((count _position) < 3) exitWith {
    missionNamespace setVariable [QEGVAR(core,cbrnRelease), []];
    missionNamespace setVariable [QEGVAR(core,cbrnPlumeActive), false];
    []
};

private _record = [
    true,
    _position,
    toUpper _agent,
    _strength,
    _altitude,
    _burst,
    diag_tickTime
];

missionNamespace setVariable [QEGVAR(core,cbrnRelease), _record];
missionNamespace setVariable [QEGVAR(core,cbrnPlumeActive), true];

_record
