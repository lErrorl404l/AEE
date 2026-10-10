#include "..\script_component.hpp"

/*
Radar minimum detectable power (pure).

    Pmin = k * T0 * B * Fn * SNR_min

    k        Boltzmann constant, 1.380649e-23 J/K (exact since the 2019 SI)
    T0       standard noise reference temperature, 290 K
    B        receiver bandwidth, Hz
    Fn       receiver noise figure (linear, NOT dB)
    SNR_min  detection signal-to-noise ratio (linear, NOT dB)

This is the receiver noise floor (k*T0*B) raised by the noise figure and the
detection threshold.  The radar range equation (fnc_calculateRadarRange)
consumes the result as its denominator power.

SOURCE.  Skolnik, "Radar Handbook", 3rd ed., McGraw-Hill, 2008, ISBN
978-0-07-148547-0, ch. 1 (the radar range equation and the k*T0*B noise
floor); the 290 K reference and the exact Boltzmann constant are standard.

COORDINATION.  The repository's general radar detection model (issue #104,
addons/radio/functions/radar/fnc_radarNoiseFloor.sqf, branch
feat/104-radar-detection) owns this equation.  This kernel is the missile
seeker's own copy, written while #104 was unmerged; the two must be
reconciled at integration so the repository keeps one model of this physics.

SNR_min NOTE.  The issue #131 states "SNRmin ~ 13 dB for Pd=0.5, Pfa=1e-6".
That pairing is wrong.  Albersheim's closed-form approximation gives, single
pulse at Pfa = 1e-6: about 11.2 dB for Pd = 0.5, and about 13.1 dB for
Pd = 0.9 (Albersheim, "A closed-form approximation to Robertson's detection
characteristics", Proc. IEEE 69(7):839, 1981, DOI 10.1109/PROC.1981.12082).
So 13 dB belongs to Pd = 0.9, not Pd = 0.5.  The caller passes the linear
SNR for its own Pd/Pfa.

Arguments:
  0: _bandwidthHz (NUMBER) B, Hz, > 0
  1: _noiseFigure (NUMBER) Fn, linear, > 0
  2: _snrMin      (NUMBER) SNR_min, linear, > 0

Return Value: NUMBER - minimum detectable power in watts.  Returns 0 when any
argument is not positive.
Public: No
*/

params [
    ["_bandwidthHz", 0, [0]],
    ["_noiseFigure", 1, [0]],
    ["_snrMin", 1, [0]]
];

if (_bandwidthHz <= 0) exitWith { 0 };
if (_noiseFigure <= 0) exitWith { 0 };
if (_snrMin <= 0) exitWith { 0 };

private _k = 1.380649e-23;
private _t0 = 290;

_k * _t0 * _bandwidthHz * _noiseFigure * _snrMin
