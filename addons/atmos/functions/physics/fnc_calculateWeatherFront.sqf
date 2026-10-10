#include "..\..\script_component.hpp"

/*
Bergen (Norwegian) cyclone life cycle as a deterministic front state machine.

Bjerknes (1919) describes the mid-latitude cyclone as a repeating life cycle:
a stationary front, cyclogenesis (a wave on the front), the mature stage (a
warm sector between a warm front and a cold front), occlusion (the cold front
overtakes the warm front), then dissipation.  The cycle runs about one week.
This kernel maps mission time onto that cycle and returns the front state at
the current instant.  It is a PURE function of mission time and the seeded
progression, so every machine computes the same front and nothing is
broadcast (no publicVariable).

The front is one line that sweeps across the map.  Its bearing (direction of
motion) follows the prevailing mid-latitude westerlies: fronts track broadly
eastward.  The seed spreads the bearing over a 60 deg arc (UNSOURCED spread)
and offsets the life cycle so two missions do not share a front.

The per-stage numbers come from the issue's research (FAA Advisory Circular
00-6B ch 10.3 Aviation Weather; WW2010 UIUC; NOAA JetStream; UK Met Office):
  cold front      speed 30-60 km/h, gradient zone 50-100 km, veer 40-90 deg
  warm front      speed 20-30 km/h (about half the cold-front speed)
  occluded front  speed 25-45 km/h
  stationary      speed below 5 km/h
  temperature contrast 5-15 C across the front

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
    6  cloudTerm       NUMBER  cloud-trend forcing (magnitude UNSOURCED)
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

// One week: the Bjerknes (1919) life cycle, ~1 week.
private _cycleLength = 604800;

// The life-cycle stages.  Each entry:
//   [phaseStart, type, speedKmh, contrastC, zoneHalfWidthKm, veerDeg,
//    troughHpa, cloudTerm, precipRateMmH, warmSide]
// The cloudTerm magnitudes are a modelling choice inside the existing
// [-0.5, 0.5] cloud-trend clamp; the sign follows the passage signature.
private _stages = [
    [0.00, "stationary",  3,  3,  60, 10, 1.0, 0.10,  0.5,  1],
    [0.12, "warm",       25,  6, 125, 45, 2.0, 0.30,  3.0, -1],
    [0.30, "cold",       45, 10,  50, 65, 3.0, 0.35, 25.0,  1],
    [0.55, "occluded",   35,  6,  90, 50, 2.5, 0.20, 10.0,  1],
    [0.80, "stationary",  3,  3,  60, 10, 1.0, 0.10,  0.5,  1]
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

// The front starts 1500 km behind the anchor (a modelling choice) and sweeps
// through as the cycle advances, so an observer at the anchor sees it
// approach, pass and recede.  1500 km places the crossing in the mature
// (cold-front) stage, the dominant passage.
private _distanceKm = -1500 + _travelledKm;

// Bearing: the prevailing westerlies carry fronts broadly eastward; the seed
// spreads the track over a 60 deg arc (UNSOURCED spread).
private _bearingDeg = 60 + _seed * 60;

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
