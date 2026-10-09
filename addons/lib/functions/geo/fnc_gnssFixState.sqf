#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_gnssFixState
 *
 * Pure, argument-driven GNSS fix-continuity kernel.  It reads no world, no
 * config, no player and no engine state, and it holds no state outside the
 * passed state array.  It models the loss of a fix, the time since the last
 * good fix and the re-acquisition ramp after the signal returns.
 *
 * Continuity mechanism: GPS Standard Positioning Service Performance
 * Standard, 5th edition, April 2020 (gps.gov), Section 3.6 and App. A.8.  The
 * service is either available (a good fix) or interrupted; after an
 * interruption the receiver re-acquires the signals over a non-zero interval
 * rather than instantly.
 *
 * UNSOURCED shapes (listed for the per-constant register):
 *   GNSS_FIX_ACQUIRE_FLOOR  effective-signal floor for any fix
 *   GNSS_FIX_REACQ_RATE     re-acquisition progress per second
 *   GNSS_FIX_DECAY_RATE     re-acquisition progress lost per second
 *   GNSS_FIX_LAG_PER_S      lag offset per second since the last fix
 *   GNSS_FIX_LAG_REACQ      lag offset at zero re-acquisition progress
 *   GNSS_FIX_STUTTER_MAX    stutter envelope at zero progress
 *
 * Arguments:
 *   0: dt            <NUMBER> time step, seconds, positive
 *   1: signalQuality <NUMBER> received signal quality, 0 to 1, 1.0 best
 *   2: jamming       <NUMBER> jamming state, 0 to 1
 *   3: prevState     <ARRAY>  previous [timeSinceFix, reacqProgress]; [] at
 *                             the first call
 *
 * Return: [quality, timeSinceFix, reacqProgress, lagOffset, stutterEnvelope]
 *   quality is "none", "degraded" or "ok".  timeSinceFix is seconds.
 *   reacqProgress is 0 to 1.  lagOffset is metres.  stutterEnvelope is a
 *   0 to 1 amplitude.  Feed the next call from this return:
 *   prevState = [_out select 1, _out select 2].
 */
params [
    ["_dt", 0, [0]],
    ["_signalQuality", 0, [0]],
    ["_jamming", 0, [0]],
    ["_prevState", [], [[]]]
];

private _step = _dt max 0;
private _signal = ((_signalQuality) max 0) min 1;
private _jam = ((_jamming) max 0) min 1;

private _timeSinceFix = 0;
private _reacq = 1;
if ((count _prevState) >= 2) then {
    _timeSinceFix = (_prevState select 0) max 0;
    _reacq = ((_prevState select 1) max 0) min 1;
};

// Jamming removes usable signal.  The combination is UNSOURCED.
private _effective = ((_signal - _jam) max 0) min 1;

private _acquireFloor = 0.3;                             // UNSOURCED
private _reacqRate = 0.25;                               // UNSOURCED
private _decayRate = 1.0;                                // UNSOURCED

private _quality = "none";
if (_effective >= _acquireFloor) then {
    _reacq = ((_reacq + (_reacqRate * _step)) min 1);
    if (_reacq >= 1) then {
        _quality = "ok";
        _timeSinceFix = 0;
    } else {
        _quality = "degraded";
        _timeSinceFix = _timeSinceFix + _step;
    };
} else {
    _reacq = ((_reacq - (_decayRate * _step)) max 0);
    _timeSinceFix = _timeSinceFix + _step;
};

// A fix that is still re-acquiring lags the true position and jitters.  Both
// shapes are UNSOURCED.
private _lagPerS = 2;                                    // UNSOURCED
private _lagReacq = 40;                                  // UNSOURCED
private _stutterMax = 0.5;                               // UNSOURCED
private _lagOffset = (_lagPerS * _timeSinceFix) + (_lagReacq * (1 - _reacq));
private _stutter = _stutterMax * (1 - _reacq) * _effective;

[_quality, _timeSinceFix, _reacq, _lagOffset, _stutter]
