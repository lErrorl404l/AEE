#include "..\script_component.hpp"

/*
UV Index (0–13) after the standard clear-sky model (ISO 17166 / CIE).

Solar elevation drives a sine term.  The ozone column absorbs UV-B by a
Beer-Lambert term, altitude adds about 10 % per 1000 m, and overcast reduces
the index.

Stored in GVAR(uvIndex) and EGVAR(core,currentUVIndex).
*/

private _overcast = overcast;
private _month    = date select 1;

// ─── Solar elevation from daytime
//     Sin wave: peak at noon (dayFraction = 0.5), horizon at 06:00 / 18:00
private _dayFraction    = dayTime / 24;
private _solarElevation = sin ((_dayFraction - 0.25) * 360) * 90 max 0;
private _sinElev        = sin _solarElevation;

// ─── Clear-sky UV index: 12.5 × sin(elevation) for overhead sun
private _uvClear = 12.5 * _sinElev;

// ─── Ozone absorption (Beer-Lambert)
//     300 DU is the mid-latitude column.  The 0.05 coefficient folds the
//     ozone cross-section over the UV-B band.  A mission override is used
//     when present.
private _ozoneDU = missionNamespace getVariable [QGVAR(ozoneDU), 300];
private _ozoneFactor = 0;
if (_sinElev > 0.001) then {
    _ozoneFactor = exp (-0.05 * _ozoneDU / _sinElev);
};

// ─── Altitude bonus: +10 % per 1000 m
private _player = call CBA_fnc_currentUnit;
private _altitude = EGVAR(core,referenceAltitude);
if (isNil "_altitude") then { _altitude = 0; };
if (!isNil "_player") then { _altitude = (getPosASL _player) select 2; };
private _altFactor = 1 + (_altitude / 1000) * 0.1;

// ─── Overcast reduction: full overcast cuts 70 %
private _cloudFactor = 1 - _overcast * 0.7;

// ─── Summer months (northern-hemisphere) boost
private _monthFactor = [1.0, 1.3] select ((_month >= 5) && (_month <= 8));

// ─── Compute
private _uvIndex = _uvClear * _ozoneFactor * _altFactor * _cloudFactor * _monthFactor;
_uvIndex = round (_uvIndex max 0 min 13);

missionNamespace setVariable [QGVAR(uvIndex), _uvIndex];
missionNamespace setVariable [QEGVAR(core,currentUVIndex), _uvIndex];

_uvIndex
