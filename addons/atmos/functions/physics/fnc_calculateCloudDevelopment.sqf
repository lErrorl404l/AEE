#include "..\..\script_component.hpp"

/*
Cloud development trend for informational use by mission scripts.

Does NOT call setOvercast — overcast is a server-authority engine value.
This function computes a signed trend that tells a mission layer whether
clouds are building or clearing, so it can make its own overcast decisions.

A CAPE (convective available potential energy) proxy adds a buoyancy
term.  The ambient temperature lapse is compared with the dry adiabat
(9.8 °C/km): when the lapse exceeds it, rising parcels stay warmer than
the environment and are buoyant, so convection can build cloud.

  Trend = (RH/100 × 0.4) + (temp > 25°C ? 0.3 : 0)
        + (wind < 3 ? 0.2 : -0.1) + convective CAPE term
  Clamped to [-0.5, 0.5].

  Positive → building clouds
  Negative → clearing

Stored in GVAR(currentCloudTrend)   — float -0.5 to 0.5
Stored in GVAR(currentCloudDescription) — string
Stored in GVAR(capeProxy)           — float, > 0 = convective potential
*/

private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _T  = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];

if (isNil "_RH") then { _RH = 50; };
if (isNil "_T")  then { _T  = 20; };

private _windSpeed = vectorMagnitude wind;

// ─── Temperature lapse (ambient, °C per metre) ──────────────────────────
// The elevation temperature logic applies the standard-atmosphere lapse
// (0.0065 °C/m).  Strong insolation on a hot surface steepens the real
// near-surface lapse toward the dry adiabat (0.0098 °C/m); overcast and
// night-time cooling flatten it.
private _solar = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0];
private _lapseRate = 0.0065 + (_solar * 0.004) - (overcast * 0.0015);

// ─── Parcel buoyancy (CAPE proxy) ───────────────────────────────────────
// Ambient lapse above the dry adiabat → rising parcels are buoyant.
private _buoyancy = _lapseRate - 0.0098;
private _capeProxy = _buoyancy * 1000;

// ─── Convective term — buoyant, moist air builds cloud ──────────────────
private _convective = 0;
if (_capeProxy > 0 && _RH > 60) then {
    _convective = (_capeProxy * 0.15) min 0.3;
};

private _trend = (_RH / 100 * 0.4) + ([0, 0.3] select (_T > 25)) + ([0.2, -0.1] select (_windSpeed >= 3)) + _convective;
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
