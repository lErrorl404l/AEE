#include "..\script_component.hpp"

/*
Calculate lateral drift from the Coriolis (Eötvös) effect on a projectile.

  δ (m) = 0.0000729 × sin(lat_rad) × range × bulletTime

Latitude is estimated from the map Y coordinate — the Y axis in Arma runs
north so Y = (worldSize / 2) equates to the equator in this simple
equirectangular projection.

At typical Arma 3 engagement ranges the deflection is tiny (~3 cm at 800 m,
~5 cm at 1000 m).  The raw value is returned as-is; mod authors can scale
for gameplay effect.

Params:
  0: _posASL      — player position in ASL coordinates  (default: [0,0,0])
  1: _range       — target range in metres               (default: 500)
  2: _bulletTime  — projectile time-of-flight in seconds  (default: 1.0)

Sets  QGVAR(coriolisDeflection_m)
Returns the deflection in metres (positive = right in northern hemisphere).
*/

params [
    ["_posASL",    [0,0,0], [[]]],
    ["_range",     500,     [0]],
    ["_bulletTime", 1.0,    [0]]
];

// ─── Simple latitude from map Y ───────────────────────────────────────────
// Defensive: a scalar (bad caller) would make `select 1` a zero-divisor
// crash.  Guard the type so the function degrades to 0 deflection instead.
if (!(_posASL isEqualType [])) then { _posASL = [0, 0, 0]; };
if ((count _posASL) < 2) then { _posASL = [0, 0, 0]; };
private _y   = _posASL select 1;
private _ws  = worldSize;
private _lat = ((_ws / 2) - _y) / 100000 * 90;   // rough equirectangular
_lat = _lat max -90 min 90;

// ─── Coriolis deflection ──────────────────────────────────────────────────
// δ = 0.0000729 × sin(lat_rad) × range × bulletTime
// 0.0000729 ≈ angular velocity of Earth (7.2921e−5) — pre-computed constant
private _deflection = 0.0000729 * sin (_lat * pi / 180) * _range * _bulletTime;

missionNamespace setVariable [QGVAR(coriolisDeflection_m), _deflection];

_deflection
