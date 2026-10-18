#include "..\script_component.hpp"
/*
 * aee_lib_fnc_seasonalMonth
 *
 * The month on the northern-hemisphere seasonal calendar: south of the
 * equator the seasons are six months out of phase (the solstices and
 * equinoxes swap), so a southern month is shifted six months.  Tables
 * written for the northern hemisphere index with the result.
 *
 * Arguments:
 *   0: Number - calendar month, 1 to 12 (default: the mission date)
 *   1: Number - latitude, degrees (default: the world's)
 * Return: Number - seasonal month, 1 to 12
 */
params [["_month", date select 1, [0]], ["_lat", 999, [0]]];
if (_lat > 900) then { _lat = ([] call FUNC(getWorldLocation)) param [0, 45]; };
private _m = ((round _month) max 1) min 12;
if (_lat < 0) then { _m = ((_m + 5) mod 12) + 1; };
_m
