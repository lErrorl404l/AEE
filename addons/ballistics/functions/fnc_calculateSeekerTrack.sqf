#include "..\script_component.hpp"

/*
Seeker acquisition and tracking gate with hysteresis (pure).

The seeker tracks when the target is inside the field of view, the line-of-
sight rate is within the track limit, AND the signal passes the gate.  The
gate has hysteresis so a signal at the threshold does not chatter:

    acquire when   signal >= acquireThreshold        (not yet tracking)
    hold when      signal >= 0.5 * acquireThreshold  (already tracking)

This is the issue #131 rule "acquire at threshold, track at 0.5x threshold".
The half factor is the issue's stated hysteresis; it is a modelling choice,
recorded as UNSOURCED.

Arguments:
  0: _signal           (NUMBER) current signal (IR contrast, or a radar
                       signal-to-threshold ratio), dimensionless
  1: _acquireThreshold (NUMBER) acquisition threshold, > 0
  2: _inFov            (BOOL)   target inside the seeker field of view
  3: _losRate          (NUMBER) line-of-sight rate magnitude, rad/s
  4: _trackLimit       (NUMBER) track-rate limit, rad/s; <= 0 disables it
  5: _wasTracking      (BOOL)   tracking state on the previous tick

Return Value: BOOL - true when the seeker tracks this tick.
Public: No
*/

params [
    ["_signal", 0, [0]],
    ["_acquireThreshold", 1, [0]],
    ["_inFov", false, [false]],
    ["_losRate", 0, [0]],
    ["_trackLimit", 0, [0]],
    ["_wasTracking", false, [false]]
];

if (!_inFov) exitWith { false };

private _rate = abs _losRate;
if (_trackLimit > 0 && _rate > _trackLimit) exitWith { false };

private _gate = _acquireThreshold;
if (_wasTracking) then { _gate = _acquireThreshold * 0.5; };

_signal >= _gate
