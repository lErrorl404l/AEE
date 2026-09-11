#include "..\script_component.hpp"

/*
Cloud development trend for informational use by mission scripts.

Does NOT call setOvercast — overcast is a server-authority engine value.
This function computes a signed trend that tells a mission layer whether
clouds are building or clearing, so it can make its own overcast decisions.

  Trend = (RH/100 × 0.4) + (temp > 25°C ? 0.3 : 0) + (wind < 3 ? 0.2 : -0.1)
  Clamped to [-0.5, 0.5].

  Positive → building clouds
  Negative → clearing

Stored in GVAR(currentCloudTrend)        — float -0.5 to 0.5
Stored in GVAR(currentCloudDescription)  — string
*/

private _RH = EGVAR(core,currentHumidity);
private _T  = EGVAR(core,currentTemperature);

if (isNil "_RH") then { _RH = 50; };
if (isNil "_T")  then { _T  = 20; };

private _windSpeed = vectorMagnitude wind;

private _trend = (_RH / 100 * 0.4) + ([0, 0.3] select (_T > 25)) + ([0.2, -0.1] select (_windSpeed >= 3));
_trend = (_trend max -0.5) min 0.5;

private _description = switch (true) do {
    case (_trend > 0.2 && overcast > 0.6):        { "Convective" };
    case (_trend > 0.2):                             { "Building" };
    case (_trend >= -0.2):                           { "Stable" };
    default                                          { "Clearing" };
};

missionNamespace setVariable [QGVAR(currentCloudTrend), _trend];
missionNamespace setVariable [QGVAR(currentCloudDescription), _description];
