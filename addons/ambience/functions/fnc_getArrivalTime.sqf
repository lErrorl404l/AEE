#include "..\script_component.hpp"

/*
Sound arrival time at a listening post (acoustic propagation, sound ranging).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It returns the arrival time of a sound at one listener from the shot time, the
path length and the air temperature.  Sound ranging triangulates from the
arrival TIME at several posts; this kernel deliberately returns a time and
never a source position, so counter-battery stays honest.

The speed of sound in dry air follows the ideal-gas law, c = sqrt(gamma R T):
gamma = 1.4 (diatomic air), the specific gas constant R = 287.05 J/(kg K), T
in kelvin.  SOURCED.  At 20 C that is 343.2 m/s, the issue #80 reference.  A
wind component along the path adds to the speed (downwind is faster); the
caller supplies it, and the wind correction is per listening post.

Arguments:
  0: Number - the shot time, seconds
  1: Number - the path length, metres
  2: Number - the air temperature, degrees Celsius (default 15)
  3: Number - the wind component along the path, m/s, positive downwind (default 0)

Returns:
  Number - the arrival time, seconds

Example:
  [0, 3432, 20] call aee_ambience_fnc_getArrivalTime   // about 10 s
Public: Yes
*/

params [
    ["_shotTime", 0, [0]],
    ["_distance", 0, [0]],
    ["_temperatureC", 15, [0]],
    ["_windAlongMps", 0, [0]]
];

private _c = sqrt (1.4 * 287.05 * (_temperatureC + 273.15));
private _cEffective = (_c + _windAlongMps) max 1;

_shotTime + (_distance / _cEffective)
