#include "..\..\script_component.hpp"

/*
Front phase factor from the signed distance.

The issue's in-game representation maps the signed distance to the front onto
a phase factor in [-1, +1]:

  f = clamp(distanceKm / zoneHalfWidthKm, -1, 1)

The factor is +1 well ahead of the front, 0 on the front line and -1 well
behind it.  The gradient zone is the half-width over which the front's
influence fades: 50-100 km for a cold front, 200-300 km for a warm front
(FAA AC 00-6B; WW2010).  The consumer applies the same factor to the
temperature contrast step, the pressure trough, the cloud trend and the wind
veer, so one number drives the whole passage signature.

Arguments:
  0: signed distance to the front line, km (Number)
  1: gradient-zone half-width, km (Number)

Return Value: NUMBER in [-1, 1]
Example: [25, 50] call aee_atmos_fnc_calculateFrontPhase
Public: No
*/

params [["_distanceKm", 0, [0]], ["_zoneHalfWidthKm", 1, [0]]];

if !(_distanceKm isEqualType 0) then { _distanceKm = 0; };
if !(_zoneHalfWidthKm isEqualType 0) then { _zoneHalfWidthKm = 1; };

// A non-positive half-width has no gradient zone.
if (_zoneHalfWidthKm <= 0) exitWith { 0 };

private _factor = _distanceKm / _zoneHalfWidthKm;
(_factor max -1) min 1
