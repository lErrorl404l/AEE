#include "..\script_component.hpp"

/*
Nuclear EMP pulse waveform (issue #9).

The E1 and E2 phases are a double-exponential pulse:

    E(t) = E0 * k * (exp(-alpha*t) - exp(-beta*t))

Source: IEC 61000-2-9, adopted by MIL-STD-464C A.5.9.1 (the HEMP waveform
standard).  The DOE Waveform Application Guide (2023) states the same form.

E1 (early, the fast pulse):
    E0    = 50 kV/m peak field
    k     = 1.3    amplitude correction so the double exponential peaks at E0
    alpha = 4e7 s^-1
    beta  = 6e8 s^-1
    rise about 2.5 ns, FWHM about 23 ns.

E2 (intermediate, like lightning):
    E0    = 100 V/m
    FWHM  about 693 us (same form, slower constants).
The issue's source does NOT publish E2's rate constants (alpha, beta, k), so
the kernel takes them as arguments and does not invent them; only the E1
constants are hard-coded as defaults.

At t = 0 the two exponentials cancel: E(0) = E0*k*(1 - 1) = 0.  The pulse
then rises to the peak and decays.  The kernel is pure: it reads no engine
state and returns the field in volts per metre at time t.

Arguments:
  0: tS    (NUMBER) - time from pulse onset, seconds (>= 0)
  1: e0    (NUMBER) - peak field, V/m (default 50000, the E1 peak)
  2: k     (NUMBER) - amplitude correction (default 1.3)
  3: alpha (NUMBER) - slow decay constant, s^-1 (default 4e7)
  4: beta  (NUMBER) - fast decay constant, s^-1 (default 6e8)

Return Value: NUMBER - field magnitude at t, V/m
Example: [2.5e-9] call aee_core_fnc_calculateEmpWaveform
Public: No
*/

params [
    ["_tS", 0, [0]],
    ["_e0", 50000, [0]],
    ["_k", 1.3, [0]],
    ["_alpha", 4e7, [0]],
    ["_beta", 6e8, [0]]
];

if (_tS < 0) exitWith { 0 };

private _rise = exp ((0 - _alpha) * _tS);
private _fall = exp ((0 - _beta) * _tS);

_e0 * _k * (_rise - _fall)
