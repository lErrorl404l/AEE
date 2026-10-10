#include "..\script_component.hpp"
/*
Internal tide: thermocline displacement and layer currents (issue #17).

At the tidal frequency (M2, 12.4206 h) the thermocline rises and falls as a
long internal wave.  The interface displacement is a sine of the tidal
phase:

    eta(t) = A * sin(2*pi*t/T)

  A   displacement amplitude (m)
  T   period (s)
  t   time since the epoch (s)

For a long two-layer internal wave the horizontal velocity is uniform within
each layer and follows from continuity (Gill 1982, section 6.2):

    u1 =  c * eta / h1     upper layer
    u2 = -c * eta / h2     lower layer

so the current is in phase with the displacement and is largest in the
thinner layer.  This is the exact two-layer result.  The issue's
approximate form (current about eta * sqrt(g'/h_eff)) is not used.

SQF sin takes degrees, so the phase 360*t/T is passed directly.

Sources:
  Gill (1982) Atmosphere-Ocean Dynamics, section 6.2 (continuity and the
    layer velocities of a two-layer internal wave).
  The M2 period 12.4206 h is the principal lunar semidiurnal constituent
    (Admiralty/NOAA harmonic constituents).

Input:  [_amplitude, _period, _time, _speed, _h1, _h2]
Output: [eta, u1, u2] - displacement (m), upper current (m/s), lower current (m/s)
*/

params [
    ["_amplitude", 20, [0]],
    ["_period", 44714, [0]],
    ["_time", 0, [0]],
    ["_speed", 1, [0]],
    ["_h1", 50, [0]],
    ["_h2", 1000, [0]]
];

private _eta = _amplitude * sin (360 * _time / _period);
private _u1 = _speed * _eta / (_h1 max 0.001);
private _u2 = -_speed * _eta / (_h2 max 0.001);

[_eta, _u1, _u2]
