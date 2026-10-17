#include "..\script_component.hpp"

/*
Magnetic declination at the player, plus the local ferrous deviation.

Declination: the World Magnetic Model WMM2025 (NOAA NCEI / BGS,
fnc_wmmField, generated from data/magnetism/WMM2025.COF and checked against
every NOAA test value), evaluated live at the player's geographic position
(the world position projected through the map's geo anchor,
aee_lib_fnc_worldToMgrs), altitude and the MISSION's own date.  It is
recomputed when the player moves more than ~1 km or the date changes.

WMM2025 is valid 2025.0-2030.0.  Setting aee_magnetism_wmmExtrapolate (on by
default) extrapolates the published secular variation outside it, as the
NOAA software does; off holds the field at the nearer end of the window.

Stored in GVAR(compassDeviation) and EGVAR(core,magneticDeclinationDeg),
degrees, positive east.
*/

params [];

private _unit = call CBA_fnc_currentUnit;
// isNull, not isNil: CBA_fnc_currentUnit returns objNull on a dedicated
// server rather than nil.
if (isNull _unit) exitWith { 0 };

// ─── Mission date as a decimal year ───────────────────────────────────────
date params ["_y", "_mo", "_d", "_hh", "_mi"];
private _doy = floor (275 * _mo / 9) - (2 * floor ((_mo + 9) / 12)) + _d - 30;
private _year = _y + ((_doy - 1) + (_hh + _mi / 60) / 24) / 365.25;
if !(missionNamespace getVariable [QGVAR(wmmExtrapolate), true]) then {
    _year = (_year max 2025.0) min 2030.0;
};

// ─── WMM2025 at the player, cached per ~1 km cell and day ─────────────────
private _posASL = getPosASL _unit;
private _key = format ["%1_%2_%3_%4", worldName, round ((_posASL select 0) / 1000), round ((_posASL select 1) / 1000), floor (_year * 365.25)];
private _cache = missionNamespace getVariable [QGVAR(wmmCache), []];
if !((_cache isEqualType []) && {(count _cache) == 2} && {(_cache select 0) == _key}) then {
    private _geo = [_posASL, call EFUNC(lib,getGeoAnchor), 2] call EFUNC(lib,worldToMgrs);
    private _lat = _geo select 1;
    private _lon = _geo select 2;
    if (!(_lat isEqualType 0) || {(_geo select 0) == ""}) then {
        private _loc = [] call EFUNC(lib,getWorldLocation);
        _lat = _loc select 0;
        _lon = _loc select 2;
    };
    _cache = [_key, [_lat, _lon, ((_posASL select 2) max 0) / 1000, _year] call FUNC(wmmField)];
    missionNamespace setVariable [QGVAR(wmmCache), _cache];
};
private _field = _cache select 1;
private _declination = _field select 0;
private _horizontalNT = (_field select 2) max 1000;

// ─── Local ferrous anomaly (aee_core dipole model) ─────────────────────────
// A nearby engine block or steel structure distorts the local field. The
// core dipole model returns the deviation in nanotesla. The unit's own
// vehicle is the platform, not a local source, so it is excluded.  A
// disturbing field dB across the needle deflects it by atan(dB / H), H the WMM horizontal intensity (the needle
// aligns with the horizontal field, not the total field).  The
// contribution is capped because a compass pressed against steel is
// unreadable, not merely deviated.
private _unitVehicle = vehicle _unit;
private _anomalyNT = 0;
if (missionNamespace getVariable [QGVAR(compassFerrousDeviation), true]) then {
    {
        if (_x != _unitVehicle) then {
            // SQF `call` binds LOOSER than `+`, so the call must be
            // parenthesised, or this reads `(_anomalyNT + [array]) call F`.
            _anomalyNT = _anomalyNT + ([getPosASL _unit, getPosASL _x] call FUNC(calculateMagneticAnomaly));
        };
    } forEach (nearestObjects [_unit, ["LandVehicle"], 50]);
};
private _anomalyDeg = (atan (_anomalyNT / _horizontalNT)) max -10 min 10;
_declination = _declination + _anomalyDeg;
missionNamespace setVariable [QGVAR(compassAnomalyNT), _anomalyNT];

missionNamespace setVariable [QEGVAR(core,magneticDeclinationDeg), _declination];
missionNamespace setVariable [QGVAR(compassDeviation), _declination];

_declination
