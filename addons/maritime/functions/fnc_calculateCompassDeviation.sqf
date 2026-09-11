#include "..\script_component.hpp"

/*
Magnetic declination at the player's current location using a simple
dipole approximation.

Method:
  1. Get player position via CBA_fnc_currentUnit
  2. Estimate latitude from Y coordinate relative to map centre
     lat ≈ ((y − worldSize/2) / (worldSize/2)) × 40°
     This assumes a ~80° latitude span typical of Arma 3 maps.
  3. Declination via simplified dipole:
     δ = 10 × sin(lat × π/180 × 2) + 5
     Gives roughly realistic values: ~15°W (negative) in N. America,
     ~0° in Europe, ~10°E in Asia.

Stored in GVAR(magneticDeclinationDeg) — degrees, positive east.
*/

params [];

private _unit = call CBA_fnc_currentUnit;
if (isNil "_unit") exitWith { 0 };

private _pos   = getPos _unit;
private _y     = _pos select 1;   // northing (Arma: x=east, y=north)
private _ws    = worldSize;
private _yCent = _y - (_ws / 2);

// ─── Estimate latitude from Y offset ───────────────────────────────────────
// Map centre → 0° offset; edges → ±40° latitude.
private _latDeg = (_yCent / (_ws / 2)) * 40;
_latDeg = _latDeg max -80 min 80;   // clip to plausible bounds

// ─── Magnetic declination — simplified dipole ──────────────────────────────
private _declination = 10 * sin (_latDeg * pi / 180 * 2) + 5;

missionNamespace setVariable [QEGVAR(core,magneticDeclinationDeg), _declination];

_declination
