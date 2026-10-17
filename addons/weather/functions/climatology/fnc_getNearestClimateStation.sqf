#include "..\..\script_component.hpp"
/*
Climate normals of the WMO 1991-2020 station nearest the world.

For a world with no bound reference station: the nearest station (great
circle) of configFile >> "AEE_ClimateStations" (generated from the NOAA
NCEI archive of WMO 1991-2020 normals by tools/gen_climate_normals.py) to
the world's geographic anchor.  A station that holds no humidity or no
MSLP normal takes that series from the nearest station that does.  The
result is cached for the session.

Return: [mslp hPa, -1, tMax[12], tMin[12], RH[12], precip mm[12]] with the
temperatures at sea level, or [] when the table is not loaded.
Public: No
*/

private _cached = missionNamespace getVariable [QGVAR(nearestClimateStation), []];
if (_cached isNotEqualTo []) exitWith { _cached };

private _root = configFile >> "AEE_ClimateStations";
if !(isClass _root) exitWith { [] };

private _loc = [] call EFUNC(lib,getWorldLocation);
private _lat = _loc select 0;
private _lon = _loc select 2;

private _best = [1e9, configNull];
private _bestRh = [1e9, []];
private _bestP = [1e9, []];
for "_i" from 0 to ((count _root) - 1) do {
    private _c = _root select _i;
    private _sLat = getNumber (_c >> "lat");
    private _sLon = getNumber (_c >> "lon");
    private _cosD = ((sin _lat) * (sin _sLat)) + ((cos _lat) * (cos _sLat) * (cos (_lon - _sLon)));
    private _km = 6371 * (((acos ((_cosD max -1) min 1)) * pi) / 180);
    if (_km < (_best select 0)) then { _best = [_km, _c]; };
    private _rh = getArray (_c >> "rh");
    if ((count _rh) == 12 && {_km < (_bestRh select 0)}) then { _bestRh = [_km, _rh]; };
    private _p = getArray (_c >> "mslp");
    if ((count _p) == 12 && {_km < (_bestP select 0)}) then { _bestP = [_km, _p]; };
};
private _c = _best select 1;
if (isNull _c) exitWith { [] };

private _rh = getArray (_c >> "rh");
if ((count _rh) != 12) then { _rh = _bestRh select 1; };
private _p = getArray (_c >> "mslp");
if ((count _p) != 12) then { _p = _bestP select 1; };
private _pMean = 1013.25;
if ((count _p) == 12) then {
    _pMean = 0;
    { _pMean = _pMean + _x; } forEach _p;
    _pMean = _pMean / 12;
};

private _result = [_pMean, -1, getArray (_c >> "tmax"), getArray (_c >> "tmin"), _rh, getArray (_c >> "prcp")];
missionNamespace setVariable [QGVAR(nearestClimateStation), _result];
missionNamespace setVariable [QGVAR(climateStationName), getText (_c >> "name")];
_result
