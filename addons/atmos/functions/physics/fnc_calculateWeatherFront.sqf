#include "..\..\script_component.hpp"

/*
Bergen (Norwegian) cyclone life cycle as a deterministic front state machine.

Bjerknes (1919) describes the mid-latitude cyclone as a repeating life cycle:
a stationary front, cyclogenesis (a wave on the front), the mature stage (a
warm sector between a warm front and a cold front), occlusion (the cold front
overtakes the warm front), then dissipation.  Northern-hemisphere cyclones
evolve over 2 to 7 days, most lasting 3 to 5 (Stull, "Practical Meteorology",
ch. 13), so the cycle is the 4-day middle of that range.  This kernel maps mission time onto that cycle
and returns the front state at the current instant.  It is a PURE function of
mission time and the seeded progression, so every machine computes the same
front and nothing is broadcast (no publicVariable).

The front is one line that sweeps across the map.  Its bearing (direction of
motion) follows the prevailing mid-latitude westerlies: fronts track broadly
eastward and poleward (Stull ch. 13), so the bearing is fixed at 60 deg
compass, east with a poleward tilt.  The seed offsets the life cycle so two
missions do not share a front.

The per-stage numbers, with their source register:
  cold front      speed 45 km/h.  Published: 25-30 mph (40-48 km/h typical,
                  extreme fronts to 60 mph) - FAA Aviation Weather Handbook
                  FAA-H-8083-28, ch. 11 (successor to FAA AC 00-6B).
  warm front      speed 25 km/h.  Published: 10-25 mph (16-40 km/h) - FAA
                  FAA-H-8083-28, ch. 11.
  occluded front  speed 48 km/h.  An occluded front is the boundary left when
                  the cold front has overtaken the warm one (AMS Glossary,
                  "occluded front"), so it travels with its parent low:
                  cyclones move at 12 to 15 m/s, 43 to 54 km/h (Stull ch. 13),
                  and 48 km/h is the middle of that range.
  stationary      speed 4.6 km/h.  A front is stationary when each air mass
                  advances into the other at less than 5 knots (9.26 km/h) at
                  the surface, so the speed is the middle of that defined
                  band, 2.5 kt.
  gradient zone   50-100 km (cold), 100-150 km (warm) - FAA-H-8083-28 ch. 11.
  wind veer       40-90 deg (cold) - FAA-H-8083-28 ch. 11.
  temperature contrast 5-15 C across the front (issue's research, NOAA/UKMO).
  cloud trend     magnitude is a modelling choice, not a published value.

Arguments:
  0: mission time in seconds (Number)
  1: seeded progression 0..1 (Number) — offsets the cycle and the bearing

Return Value:
  ARRAY:
    0  type            STRING  "stationary" | "warm" | "cold" | "occluded"
    1  speedKmh        NUMBER
    2  contrastC       NUMBER  temperature step across the front
    3  zoneHalfWidthKm NUMBER  half-width of the gradient zone
    4  veerDeg         NUMBER  total clockwise wind veer at passage
    5  troughHpa       NUMBER  pressure deficit at the front line
    6  cloudTerm       NUMBER  cloud-trend forcing (magnitude: a modelling choice)
    7  precipRateMmH   NUMBER  frontal precipitation rate at the line
    8  warmSide        NUMBER  +1 warm air ahead, -1 warm air behind
    9  bearingDeg      NUMBER  direction of motion (compass degrees)
   10  distanceKm      NUMBER  front position along the bearing, from the anchor

Example: [time, 0.5] call aee_atmos_fnc_calculateWeatherFront
Public: No
*/

params [["_missionTime", 0, [0]], ["_seed", 0.5, [0]]];

if !(_missionTime isEqualType 0) then { _missionTime = 0; };
if !(_seed isEqualType 0) then { _seed = 0.5; };
_seed = (_seed max 0) min 1;

// Four days (345600 s): most northern-hemisphere cyclones last 3 to 5 days
// (Stull, Practical Meteorology ch. 13; Bjerknes 1919).
private _cycleLength = 345600;

// The life-cycle stages.  Each entry:
//   [phaseStart, type, speedKmh, contrastC, zoneHalfWidthKm, veerDeg,
//    troughHpa, cloudTerm, precipRateMmH, warmSide]
// The cloudTerm magnitudes are a modelling choice inside the existing
// [-0.5, 0.5] cloud-trend clamp; the sign follows the passage signature.
private _stages = [
    [0.00, "stationary",  4.6,  3,  60, 10, 1.0, 0.10,  0.5,  1],
    [0.12, "warm",       25,  6, 125, 45, 2.0, 0.30,  3.0, -1],
    [0.30, "cold",       45, 10,  50, 65, 3.0, 0.35, 25.0,  1],
    [0.55, "occluded",   48,  6,  90, 50, 2.5, 0.20, 10.0,  1],
    [0.80, "stationary",  4.6,  3,  60, 10, 1.0, 0.10,  0.5,  1]
];

private _n = count _stages;
private _phase = (((_missionTime + _seed * _cycleLength) mod _cycleLength) / _cycleLength);
if !(_phase isEqualType 0) then { _phase = 0; };

// Find the stage that holds the current phase and integrate the distance the
// front has travelled along its bearing.  The speed is piecewise constant, so
// the distance is a piecewise-linear function of the phase.
private _travelledKm = 0;
private _current = _stages select 0;
for "_i" from 0 to (_n - 1) do {
    private _stage = _stages select _i;
    private _pStart = _stage select 0;
    private _pEnd = if ((_i + 1) < _n) then { (_stages select (_i + 1)) select 0 } else { 1 };
    private _speed = _stage select 2;
    if (_phase >= _pEnd) then {
        _travelledKm = _travelledKm + _speed * ((_pEnd - _pStart) * _cycleLength / 3600);
    } else {
        if (_phase >= _pStart) then {
            _travelledKm = _travelledKm + _speed * ((_phase - _pStart) * _cycleLength / 3600);
            _current = _stage;
        };
    };
};

// The front starts half of its own cycle travel behind the anchor and sweeps
// through as the cycle advances, so an observer at the anchor sees it
// approach, pass and recede, and the crossing falls at the middle of the
// cycle, the mature (cold-front) stage.  The offset is computed from the
// stage speeds, not chosen.
private _cycleTravelKm = 0;
for "_i" from 0 to (_n - 1) do {
    private _stage = _stages select _i;
    private _pStart = _stage select 0;
    private _pEnd = if ((_i + 1) < _n) then { (_stages select (_i + 1)) select 0 } else { 1 };
    _cycleTravelKm = _cycleTravelKm + ((_stage select 2) * ((_pEnd - _pStart) * _cycleLength / 3600));
};
private _distanceKm = _travelledKm - (_cycleTravelKm / 2);

// Bearing: cyclones propagate toward the east and poleward (Stull ch. 13),
// so the track is 60 deg compass, east with a poleward tilt.
private _bearingDeg = 60;

[
    _current select 1,
    _current select 2,
    _current select 3,
    _current select 4,
    _current select 5,
    _current select 6,
    _current select 7,
    _current select 8,
    _current select 9,
    _bearingDeg,
    _distanceKm
]
