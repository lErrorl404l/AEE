#include "..\script_component.hpp"

/*
Ekman wind-driven transport and the Ekman layer depth.

A steady wind stress tau on a rotating ocean drives a net mass transport 90
degrees to the right of the wind in the northern hemisphere (Ekman 1905).  The
depth-integrated transport is independent of the eddy viscosity:

  f   = 2 * Omega * sin(phi)              Coriolis parameter, s^-1
  tau = rho_air * C_D * U10^2             wind stress, N m^-2
  M   = tau / (rho_w * f)                 volume transport, m^2 s^-1
  D_e = sqrt(2 * K_v / |f|)               Ekman e-folding depth, m
  V0  = tau / sqrt(rho_w^2 * |f| * K_v)   surface current, m s^-1

Constants: Omega = 7.2921e-5 s^-1 (Earth rotation rate, Stewart 2008); rho_air
= 1.2 kg m^-3; C_D = 1.2e-3 (bulk drag coefficient at 10 m); rho_w = 1025
kg m^-3 (sea water); K_v = 0.1 m^2 s^-1 (vertical eddy viscosity, Stewart
2008).  At 45 N, U10 = 10 m/s gives tau = 0.144 N m^-2 and M = 1.36 m^2 s^-1;
the issue's own vector tau = 0.1 N m^-2 gives M = 0.95 m^2 s^-1.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The driver
FUNC(calculateOceanCurrent) reads the state and calls this kernel.

Arguments:
  0: Number - wind speed at 10 m, U10, m s^-1
  1: Number - latitude, degrees (positive north)

Returns:
  Array - [transport M (m^2 s^-1), Ekman depth D_e (m), surface speed V0 (m s^-1)]
*/

params [
    ["_windSpeed10", 0, [0]],
    ["_latDeg", 45, [0]]
];

private _omega    = 0.000072921;   // Earth rotation rate, s^-1
private _rhoAir   = 1.2;           // kg m^-3
private _dragCd   = 0.0012;        // bulk drag at 10 m
private _rhoWater = 1025;          // kg m^-3, sea water
private _eddyKv   = 0.1;           // m^2 s^-1, vertical eddy viscosity

private _f = 2 * _omega * sin _latDeg;

// Within a few degrees of the equator f -> 0 and the Ekman model is itself
// invalid; M = tau/(rho f) would divide by zero.  Clamp |f| to the value at
// 0.5 degrees and keep the hemisphere sign.
private _fMin = 2 * _omega * sin 0.5;
if (abs _f < _fMin) then {
    _f = _fMin * ([-1, 1] select (_f >= 0));
};

private _tau = _rhoAir * _dragCd * _windSpeed10 * _windSpeed10;
private _transport    = _tau / (_rhoWater * _f);
private _ekmanDepth   = sqrt (2 * _eddyKv / abs _f);
private _surfaceSpeed = _tau / sqrt (_rhoWater * _rhoWater * abs _f * _eddyKv);

[_transport, _ekmanDepth, _surfaceSpeed]
