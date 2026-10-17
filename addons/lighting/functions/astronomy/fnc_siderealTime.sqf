#include "..\..\script_component.hpp"
/*
Local sidereal time (degrees) at the world, for the mission date and the
CURRENT game clock.

Shared by the star catalogue, the Milky Way and the meteor radiants so they
cannot drift.  The clock is local apparent solar time (the engine's
convention, aee_lib_fnc_gameClockToUT); the sidereal time is GMST (Meeus
eq. 12.4) plus the world longitude, from aee_lib_fnc_astroPosition.  (The
previous kernel used `time`, the seconds since the mission STARTED, as the
time of day, and no longitude, so the sky was drawn for 00:00 UT whatever
the clock said.)

Argument:
  0: Array - mission date [year, month, day, ...] (default date)
Returns:
  Number - local sidereal time in degrees, [0, 360).
*/
params [["_date", date, [[]]]];
private _loc = [] call EFUNC(lib,getWorldLocation);
private _ut = [_date, dayTime, _loc select 2] call EFUNC(lib,gameClockToUT);
([_ut select 0, _ut select 1, _loc select 0, _loc select 2] call EFUNC(lib,astroPosition)) select 0
