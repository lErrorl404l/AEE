#include "..\..\script_component.hpp"

/*
UV Index, the WHO/WMO/ISO 17166 erythemal index.

Clear sky, Madronich (2007), "Analytic formula for the clear-sky UV index",
Photochem. Photobiol. 83:1537, fitted to radiative-transfer runs:
  UVI_clear = 12.50 * mu0^2.42 * (ozone / 300 DU)^-1.23
mu0 is the cosine of the solar zenith angle, taken from the astronomical
sun (aee_core_currentSunElevation: date, latitude, longitude), so the season
and the latitude are in the sun angle and no month factor is needed.  The
Earth-Sun distance adds the +/-3.3 % annual term (perihelion early January).

Altitude: +10 % per 1000 m (WHO 2002, Global Solar UV Index: A Practical
Guide, p. 5).  Cloud: the overcast cloud modification factor is 0.2-0.5
for 8 oktas in the measured studies Calbo et al. (2005, Rev. Geophys. 43,
RG2002) review; the midpoint 0.35 is used, linear in cover.

Sun position is published by the lighting tick (fnc_calculateSolarRadiation),
which runs the Meeus solar position for date, latitude and longitude.  Until
that first tick the core value is unset; the fallback is -90 degrees (the
anti-solar point), so the index reads 0 rather than a latitude-free guess.

Stored in GVAR(uvIndex) and EGVAR(core,currentUVIndex).
*/

private _overcast = overcast;

// ─── Solar zenith angle (astronomical sun) ────────────────────────────────
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
if !(_sunElev isEqualType 0) then { _sunElev = -90; };
private _mu0 = (sin _sunElev) max 0;

// ─── Clear-sky index (Madronich 2007) ─────────────────────────────────────
// A mission override of the ozone column is used when present.
private _ozoneDU = missionNamespace getVariable [QGVAR(ozoneDU), 300];
if !(_ozoneDU isEqualType 0) then { _ozoneDU = 300; };
private _uvClear = 0;
if (_mu0 > 0) then {
    _uvClear = 12.50 * (_mu0 ^ 2.42) * ((_ozoneDU max 100) / 300) ^ -1.23;
};

// ─── Earth-Sun distance (1/r^2, eccentricity 0.0167) ──────────────────────
private _date = date;
private _doy = floor (275 * (_date select 1) / 9) - (2 * floor (((_date select 1) + 9) / 12)) + (_date select 2) - 30;
private _distFactor = 1 + 0.033 * cos (360 * (_doy - 3) / 365);

// ─── Altitude bonus: +10 % per 1000 m
private _player = call CBA_fnc_currentUnit;
// The reference altitude the core publishes. A bare EGVAR() use reads an
// undefined variable and returns nil.
private _altitude = missionNamespace getVariable [QEGVAR(core,referenceAltitude), 0];
if !(_altitude isEqualType 0) then { _altitude = 0; };
if (!isNil "_player" && {!isNull _player}) then { _altitude = (getPosASL _player) select 2; };
private _altFactor = 1 + (_altitude / 1000) * 0.1;

// ─── Cloud modification factor (overcast CMF 0.35) ───────────────────────
private _cloudFactor = 1 - _overcast * 0.65;

// ─── Compute (the published index is an integer; it is open-ended) ──────
private _uvIndex = _uvClear * _distFactor * _altFactor * _cloudFactor;
_uvIndex = round (_uvIndex max 0);

missionNamespace setVariable [QGVAR(uvIndex), _uvIndex];
missionNamespace setVariable [QEGVAR(core,currentUVIndex), _uvIndex];

_uvIndex
