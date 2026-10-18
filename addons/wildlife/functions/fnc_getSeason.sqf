#include "..\script_component.hpp"

/*
Season kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It maps the month and the Koppen code to a season enum and a seasonality
factor, the strength of the seasonal swing for that climate.  AEE publishes
no season scalar and reads no engine season, so the month is the source, as
fnc_updateSeasonalFoliage does with "date select 1".

The four seasons are the WMO meteorological seasons (December-February
winter in the north), six months out of phase south of the equator.

The seasonality is computed, not tabulated: it is the annual swing in day
length at the latitude, as a fraction of the 24 h day.  The sunrise equation
(Meeus, Astronomical Algorithms, ch. 15) gives the half-day angle
H = acos(-tan(lat) tan(dec)), and the solstice declination is +/-23.44 deg
(the obliquity of the ecliptic, IAU 2006), so

  seasonality = (L(+23.44) - L(-23.44)) / 24,   L = (2/15) H hours

which is 0 at the equator, about 0.29 at 45 deg and 1 at the polar circles,
where the swing is the whole day.  The Koppen code is not used for it: the
swing above is the thermal season, and a tropical dry season is a
precipitation season this kernel does not model.

Arguments:
  0: Number - the month, 1 to 12
  1: String - the Koppen biome code
  2: Number - the latitude, degrees (positive north, default 45)

Returns:
  Array - [season, seasonality] with season 0 winter, 1 spring, 2 summer,
          3 autumn; seasonality 0 to 1.
*/

params [
    ["_month", 6, [0]],
    ["_koppen", "", [""]],
    ["_lat", 45, [0]]
];

private _m = (round _month) max 1;
_m = _m min 12;
if (_lat < 0) then { _m = ((_m + 5) mod 12) + 1; };

private _season = 0;
if ((_m >= 3) && (_m <= 5)) then { _season = 1; };
if ((_m >= 6) && (_m <= 8)) then { _season = 2; };
if ((_m >= 9) && (_m <= 11)) then { _season = 3; };

// The annual day-length swing at this latitude (see the header).
private _absLat = abs _lat;
private _fnDayHours = {
    params ["_decDeg"];
    private _c = -((tan _absLat) * (tan _decDeg));
    if (_c <= -1) exitWith { 24 };
    if (_c >= 1) exitWith { 0 };
    (2 / 15) * (acos _c)
};
private _seasonality = ((([23.44] call _fnDayHours) - ([-23.44] call _fnDayHours)) / 24) max 0 min 1;

[_season, _seasonality]
