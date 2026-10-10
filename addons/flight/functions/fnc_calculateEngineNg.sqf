#include "..\script_component.hpp"

/*
Spool the aircraft gas-generator speed toward a wanted value, from scalars.

WHY THIS FUNCTION EXISTS.  The engine exposes no gas-generator speed reader
in the simple flight model.  The kernel commands the engine with
setWantedRPMRTD when the advanced flight model is on, and this helper
computes the spool the kernel publishes.  The helper is PURE ARITHMETIC over
scalars plus one exponential, so the headless harness runs it with no
vehicle.

THE SPOOL.  A gas turbine does not reach a commanded speed at once.  The
speed approaches the commanded value as a first-order lag:

  newNg = wantedNg + (currentNg - wantedNg) * exp (-dt / tau)   [ratio]

At a zero interval the current speed is returned unchanged.  As the interval
grows the exponential falls toward zero and the speed approaches the wanted
value.  tau is the spool time constant in seconds.

THE TIME CONSTANT IS A DECLARED DEFAULT, NOT A MEASUREMENT.  No published
spool time constant for these engine classes was found.  The default is four
seconds, a declared value for a light turboshaft.  The caller may pass a
different constant.

THE RESULT IS CLAMPED.  A gas-generator speed ratio lies in 0..1, so the
return is clamped to that range.

Guards, each explicit:
  - A negative current speed is refused with -1, because a ratio cannot be
    negative.
  - A negative interval is refused with -1, because time does not run
    backward.
  - A non-positive time constant is refused with -1, because the exponent
    divides by it.

Arguments:
  0:  _currentNg   (NUMBER) current gas-generator speed ratio, >= 0
  1:  _wantedNg    (NUMBER) commanded speed ratio, clamped to 0..1
  2:  _deltaTimeS  (NUMBER) elapsed interval, s, >= 0
  3:  _spoolTauS   (NUMBER) declared spool time constant, s, > 0

Return Value: NUMBER - the new speed ratio in 0..1, or -1 when an input is
unusable.
Example: [0.4, 1.0, 1, 4] call aee_flight_fnc_calculateEngineNg
Public: No
*/

params [
    ["_currentNg", 0, [0]],
    ["_wantedNg", 0, [0]],
    ["_deltaTimeS", 0, [0]],
    ["_spoolTauS", 4, [0]]
];

if (_currentNg < 0) exitWith { -1 };
if (_deltaTimeS < 0) exitWith { -1 };
if (_spoolTauS <= 0) exitWith { -1 };

// The commanded speed is a ratio, so it is clamped to the ratio range.
private _target = _wantedNg max 0 min 1;
private _current = _currentNg max 0 min 1;

// First-order lag: the spool closes the gap by the fraction exp(-dt/tau).
private _newNg = _target + ((_current - _target) * exp (-(_deltaTimeS / _spoolTauS)));

_newNg max 0 min 1
