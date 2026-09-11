#include "..\script_component.hpp"

/*
UV Index (0–11).

Based on solar elevation (derived from daytime), altitude bonus
(+10 % per 1000 m), overcast reduction, and seasonal month adjustment
(+30 % for summer months May–August).

Stored in GVAR(currentUVIndex).
*/

private _overcast = overcast;
private _month    = date select 1;

// ─── Solar elevation from daytime
//     Sin wave: peak at noon (dayFraction = 0.5), horizon at 06:00 / 18:00
private _dayFraction     = dayTime / 24;
private _solarElevation  = sin ((_dayFraction - 0.25) * 360) * 90 max 0;

// ─── Altitude bonus: +10 % per 1000 m
private _altitude = EGVAR(core,referenceAltitude);
if (isNil "_altitude") then { _altitude = 0; };
private _altBonus = 1 + (_altitude / 1000) * 0.1;

// ─── Overcast reduction: full overcast cuts 70 %
private _cloudFactor = 1 - _overcast * 0.7;

// ─── Summer months (northern-hemisphere) boost
private _monthFactor = [1.0, 1.3] select ((_month >= 5) && (_month <= 8));

// ─── Compute
private _uvIndex = _solarElevation / 90 * 11 * _altBonus * _cloudFactor * _monthFactor;
_uvIndex = round (_uvIndex max 0 min 11);

missionNamespace setVariable [QEGVAR(core,currentUVIndex), _uvIndex];

_uvIndex
