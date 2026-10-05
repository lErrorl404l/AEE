#include "..\..\script_component.hpp"

/*
Shadow target distance (aee-workshop-copy item 6, part 2).

Re-derived from fn_calculatetarget.sqf in Adaptive Shadows (Workshop
3792830104).  The mod publishes no licence, so this is a re-derived numeric
kernel, not copied code.  No mod content is copied.  The protection scale 0.25
for an enclosed scene and the margin roles are the mod's own tuning and are
UNSOURCED.

The kernel is pure: no missionNamespace, no GVAR or EGVAR, no engine command.
The driver supplies the speed, the optics flag and the margins.

Margin array (from the driver's settings):
  0: base safety margin in metres
  1: movement protection, metres per (m/s)
  2: vehicle protection, metres per (m/s)
  3: camera-turn protection, metres at full turn
  4: optics protection, metres in optics

Arguments:
  0: Number  - classified depth in metres
  1: Number  - effective minimum in metres
  2: Number  - effective maximum in metres
  3: Number  - camera turn level 0..1
  4: String  - scene state, ENCLOSED scales the margins by 0.25
  5: Number  - speed in m/s
  6: Boolean - in a vehicle
  7: Boolean - in optics
  8: Array   - margin array above

Returns:
  Number - clamped target depth in metres
*/

params [
    ["_depth", 0, [0]],
    ["_effectiveMin", 0, [0]],
    ["_effectiveMax", 0, [0]],
    ["_turnLevel", 0, [0]],
    ["_sceneState", "OUTSIDE", [""]],
    ["_speed", 0, [0]],
    ["_inVehicle", false, [true]],
    ["_optics", false, [true]],
    ["_margins", [12, 0.6, 1.25, 0, 0], [[]]]
];

private _baseMargin = (_margins select 0) max 0;
private _movementProtection = (_margins select 1) max 0;
private _vehicleProtection = (_margins select 2) max 0;
private _cameraTurnProtection = (_margins select 3) max 0;
private _opticsProtection = (_margins select 4) max 0;

private _protectionScale = [1, 0.25] select (_sceneState isEqualTo "ENCLOSED");
private _movementMargin = _speed * _movementProtection * _protectionScale;

private _vehicleMargin = 0;
if (_inVehicle) then {
    _vehicleMargin = _speed * _vehicleProtection * _protectionScale;
};

private _turnMargin = _cameraTurnProtection * ((_turnLevel max 0) min 1) * _protectionScale;

private _opticsMargin = 0;
if (_optics) then {
    _opticsMargin = _opticsProtection * _protectionScale;
};

private _margin = _baseMargin + _movementMargin + _vehicleMargin + _turnMargin + _opticsMargin;

if (_effectiveMax <= 0) exitWith {0};

((_depth + _margin) max _effectiveMin) min _effectiveMax
