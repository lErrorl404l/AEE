#include "..\script_component.hpp"
/*
Coolant power derate and fan state from the coolant temperature (issue #111).

The brief states the coolant bands:

  normal    85-100 C   no derate, fan off
  hot      100-115 C   fan on, power limit
  overheat  >115 C     derate to 50 percent
  critical  >130 C     engine protection

So the derate is 1.0 up to the normal maximum, falls linearly from 1.0 to the
overheat floor across the hot band, holds the floor to the critical
temperature, and falls to zero above it.  The fan switches on at the normal
maximum.

THE BANDS ARE ARGUMENTS.  The thresholds are the caller's, read from the fuel
constant table, so this kernel carries no magic number of its own.

Guards, each explicit:
  - A hot maximum at or below the normal maximum is refused with [1, 0]: an
    inverted band interpolates backwards.
  - A critical temperature at or below the hot maximum is refused with [1, 0]:
    the same.

Arguments:
  0: _tCoolantC      (NUMBER) coolant temperature, C
  1: _normalMaxC     (NUMBER) top of the normal band, C
  2: _hotMaxC        (NUMBER) top of the hot band, C, > _normalMaxC
  3: _criticalC      (NUMBER) critical temperature, C, > _hotMaxC
  4: _overheatDerate (NUMBER) derate floor in 0..1

Return Value: ARRAY - [derateFraction, fanOn], fanOn 1 when the fan runs.
Example: [118, 100, 115, 130, 0.5] call aee_vehicles_fnc_calculateCoolantDerate
Public: No
*/

params [
    ["_tCoolantC", 0, [0]],
    ["_normalMaxC", 100, [0]],
    ["_hotMaxC", 115, [0]],
    ["_criticalC", 130, [0]],
    ["_overheatDerate", 0.5, [0]]
];

if (_hotMaxC <= _normalMaxC) exitWith { [1, 0] };
if (_criticalC <= _hotMaxC) exitWith { [1, 0] };

private _floor = _overheatDerate max 0 min 1;

private _derate = 1;
private _fanOn = 0;

if (_tCoolantC > _normalMaxC) then {
    _fanOn = 1;
    if (_tCoolantC <= _hotMaxC) then {
        // Linear from 1.0 at the normal maximum to the floor at the hot maximum.
        _derate = linearConversion [_normalMaxC, _hotMaxC, _tCoolantC, 1, _floor, true];
    } else {
        _derate = _floor;
        if (_tCoolantC > _criticalC) then { _derate = 0; };
    };
};

[_derate, _fanOn]
