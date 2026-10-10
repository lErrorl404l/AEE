#include "..\script_component.hpp"

/*
Trigger a nuclear EMP event (issue #9).

A mission calls this to detonate an EMP at a ground position.  It sets the
event state that fnc_updateEmp reads each environment tick; the tick computes
the free field at the player, couples it through each system's hardening and
publishes the degradation factors the radio and optics modules consume.

This is the honest trigger for an event the engine has no weapon for: there is
no nuclear weapon in Arma, so a mission script (or a Zeus/EDEN action) starts
the burst.  The state is written to the LOCAL mission namespace.  For a
multiplayer burst a mission must broadcast the four state variables
(aee_core_empActive, empBurstPos, empBurstAltM, empPeakVpm, empStartTime), the
same way any scripted event is networked.

Burst altitude selects the geometry (issue #9):
  >= 30 km  high-altitude burst (HEMP footprint model)
  <  30 km  ground / low burst (SREMP 1/R model)

Arguments:
  0: pos      (ARRAY)  - burst ground zero [x, y] or [x, y, z]
  1: burstAltM (NUMBER) - burst altitude, m (default 400000 = 400 km HEMP)
  2: peakVpm   (NUMBER) - peak free field, V/m (default 50000 = E1 50 kV/m)

Return Value: BOOL - true when the event was set
Example: [[5000, 8000], 400000, 50000] call aee_core_fnc_triggerEmp
Public: Yes
*/

params [
    ["_pos", [0, 0, 0], [[]]],
    ["_burstAltM", 400000, [0]],
    ["_peakVpm", 50000, [0]]
];

if (!GVAR(empEnabled)) exitWith { false };
if ((count _pos) < 2) exitWith { false };

private _type = ["ground", "hemp"] select (_burstAltM >= 30000);

missionNamespace setVariable [QGVAR(empActive), true];
missionNamespace setVariable [QGVAR(empBurstType), _type];
missionNamespace setVariable [QGVAR(empBurstPos), _pos];
missionNamespace setVariable [QGVAR(empBurstAltM), _burstAltM];
missionNamespace setVariable [QGVAR(empPeakVpm), _peakVpm];
missionNamespace setVariable [QGVAR(empStartTime), CBA_missionTime];
missionNamespace setVariable [QGVAR(empCaptured), false];

private _logMsg = format ["EMP triggered: %1 burst, alt %2 m, peak %3 V/m", _type, _burstAltM, _peakVpm];
AEE_LOG_INFO(_logMsg);

true
