#include "..\..\script_component.hpp"

/*
Cloud development trend for informational use by mission scripts.

Does NOT call setOvercast — overcast is a server-authority engine value.
This function computes a signed trend that tells a mission layer whether
clouds are building or clearing, so it can make its own overcast decisions.

The convective potential is the parcel CAPE (fnc_calculateParcelCape:
parcel theory, Bolton 1980 LCL, the moist pseudo-adiabat, the ICAO standard
atmosphere as the environment), in J/kg.  The signed trend is an
INFORMATIONAL heuristic for mission scripts (no measured cloud-trend law
exists); its weights are display choices:

  Trend = (RH/100 x 0.4) + (temp > 25 C ? 0.3 : 0)
        + (wind < 3 ? 0.2 : -0.1) + 0.3 when CAPE > 0 and RH > 60
  Clamped to [-0.5, 0.5].

  Positive → building clouds
  Negative → clearing

Stored in GVAR(currentCloudTrend)   — float -0.5 to 0.5
Stored in GVAR(currentCloudDescription) — string
Stored in GVAR(capeProxy)           — CAPE, J/kg (> 0 = convective potential)
Stored in GVAR(updraftMax)          — parcel-theory updraft, m/s (an upper bound)
*/

private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _T  = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];

if (isNil "_RH") then { _RH = 50; };
if (isNil "_T")  then { _T  = 20; };

private _windSpeed = vectorMagnitude wind;

// ─── Parcel CAPE (J/kg) ───────────────────────────────────────────────────
private _p = missionNamespace getVariable [QEGVAR(core,currentPressure), 1013.25];
if !(_p isEqualType 0) then { _p = 1013.25; };
private _parcel = [_T, _RH, _p] call FUNC(calculateParcelCape);
private _capeProxy = _parcel select 0;

// ─── Convective term — buoyant, moist air builds cloud ──────────────────
private _convective = [0, 0.3] select (_capeProxy > 0 && _RH > 60);

private _trend = (_RH / 100 * 0.4) + ([0, 0.3] select (_T > 25)) + ([0.2, -0.1] select (_windSpeed >= 3)) + _convective;

// Weather front (issue #15): a front forces the trend — cloud builds ahead of
// it and clears behind it.  fnc_updateWeatherFront publishes the signed term,
// already scaled by the phase factor.  Folding the forcing here keeps ONE
// cloud model; the front does not recompute the convective physics.
private _frontTerm = missionNamespace getVariable [QGVAR(frontCloudTerm), 0];
if !(_frontTerm isEqualType 0) then { _frontTerm = 0; };
_trend = _trend + _frontTerm;
_trend = (_trend max -0.5) min 0.5;

private _description = switch (true) do {
    case (_capeProxy > 0 && _RH > 70):        { "Convective" };
    case (_trend > 0.2 && overcast > 0.6):    { "Convective" };
    case (_trend > 0.2):                      { "Building" };
    case (_trend >= -0.2):                    { "Stable" };
    default                                   { "Clearing" };
};

missionNamespace setVariable [QGVAR(currentCloudTrend), _trend];
missionNamespace setVariable [QGVAR(currentCloudDescription), _description];
missionNamespace setVariable [QGVAR(capeProxy), _capeProxy];
missionNamespace setVariable [QGVAR(updraftMax), _parcel select 2];
missionNamespace setVariable [QGVAR(lclHeight), _parcel select 1];
