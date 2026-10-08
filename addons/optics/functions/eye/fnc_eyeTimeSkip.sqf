#include "..\..\script_component.hpp"

/*
Did the world clock jump since the last driver tick?

A time skip (skipTime, setDate, an Eden time change) moves the world clock in
one step.  The real clock (diag_tickTime) does not move with it, so the eye
driver cannot see the skip from its own timestep.  The eye must ARRIVE adapted
to the new scene, the same rule the mission start uses (ADR-007), or it chases
the jumped scene over the slow dark tau and the aperture is wrong for minutes.

The clock wraps at 24 h, so a delta above 12 h is read the short way round.

The threshold must sit above the largest clock advance a single driver tick can
produce under time acceleration, and below the smallest useful skip.  The
driver ticks at 0.1 s.  The engine clamps time acceleration to 100x, so one
tick advances at most 10 s of world time (0.0028 h).  The default 0.05 h
(180 s) leaves a wide margin on both sides.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - previous world hour [0, 24), or -1 when no sample exists yet
  1: Number - current world hour [0, 24)
  2: Number - skip threshold, hours

Returns:
  Boolean - true when the clock moved by more than the threshold in one step.
*/

params [
    ["_prevHour", -1, [0]],
    ["_nowHour", 0, [0]],
    ["_thresholdHours", 0.05, [0]]
];

if (_prevHour < 0) exitWith { false };

private _delta = _nowHour - _prevHour;
if (_delta > 12) then { _delta = _delta - 24; };
if (_delta < -12) then { _delta = _delta + 24; };

abs(_delta) > _thresholdHours
