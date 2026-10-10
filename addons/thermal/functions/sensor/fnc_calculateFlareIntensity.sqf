#include "..\..\script_component.hpp"

/*
Infrared decoy flare radiant intensity over time (pure).

    J(t) = J0 * exp( -t / tau )

    J0    peak radiant intensity at ignition, W/sr
    tau   decay time constant, s
    t     time since ignition, s

The single-exponential form is a common simplification.  A real magnesium /
Teflon / Viton (MTV) flare shows an ignition spike, then a plateau, then the
decay; a single exponential captures the decay only.  The caller compares the
flare's intensity against the target's to decide a lock switch, so a RELATIVE
figure is what matters; an absolute J0 is not required by the consumer.

SOURCING.  The issue #131 cites DTIC ADA432299 for flare rejection.  That
report is Bartak, "Mitigating the MANPADS Threat: International Agency, U.S.,
and Russian Efforts", Naval Postgraduate School thesis, March 2005.  It holds
no flare intensity or decay data, so it does NOT support this model.  No
canonical open-literature J0 or tau for a specific flare was found, so BOTH
J0 and tau are UNSOURCED tuning values.  The issue's 5-10 s burn is likewise
UNSOURCED.  The consumer must treat them as tunables.

Arguments:
  0: _peakIntensity (NUMBER) J0, W/sr, >= 0
  1: _decayTau      (NUMBER) tau, s, > 0
  2: _elapsedS      (NUMBER) t, s, >= 0

Return Value: NUMBER - radiant intensity at the given time, W/sr.  Returns
J0 at t = 0 and decreases toward 0.  Returns 0 when J0 is zero or tau is not
positive (an undecaying or inverted decay is refused).
Public: No
*/

params [
    ["_peakIntensity", 0, [0]],
    ["_decayTau", 1, [0]],
    ["_elapsedS", 0, [0]]
];

private _j0 = _peakIntensity max 0;
if (_j0 <= 0) exitWith { 0 };
if (_decayTau <= 0) exitWith { 0 };

private _t = _elapsedS max 0;

_j0 * exp (0 - _t / _decayTau)
