#include "..\script_component.hpp"
/*
Bioluminescence from mechanically stimulated dinoflagellates (issue #14).

Many dinoflagellates flash blue-green light when the water is disturbed.
A swimmer or a boat wake leaves a glowing trail.  The emission peaks at
472 nm for Pyrocystis noctiluca (Widder, Case and others 1983, Biological
Bulletin 165:791).  That peak sits in the blue-green band the water
transmits best.

Gate.  The flash is visible only when three conditions hold together.

  1. Darkness.  Light suppresses the flash (photoinhibition).  The gate is
     ambient below 0.01 lux, which is night.  A moonlit or daylight scene
     suppresses it.
  2. Clear water.  The 475 nm emission is absorbed by dissolved matter.
     The gate is Kd below 0.2 m^-1 (Jerlov III or better).  Turbid water
     hides the flash.
  3. Disturbance.  The trigger is mechanical shear on the cell.  The gate
     is a positive disturbance level.

Flash envelope.  The flash is a fast rise and a slow decay, modelled as a
double exponential:

    f(t) = exp(-t / tau_decay) * (1 - exp(-t / tau_rise))

with tau_rise = 0.077 s and tau_decay = 0.5 s.  The peak is at about
0.17 s and the total flash lasts about 0.5 to 0.6 s.  The kinetics match
the measured single-cell flash of 70 to 84 ms rise and 425 to 570 ms
decay (Latz, Frank and others 1994, Limnology and Oceanography 39:1424,
as reported in issue #14).  The two time constants were not independently
verified: that paper is behind a paywall.

Input:  [_ambientLux, _kd, _disturbance, _elapsed]
          _ambientLux  - ambient light at the eye (lux)
          _kd          - blue-band diffuse attenuation, 475 nm (m^-1)
          _disturbance - mechanical disturbance level (0 = still, 1 = strong)
          _elapsed     - seconds since the disturbance began
Output: [visible, intensity] - visible is a boolean, intensity is 0..1
*/

params [
    ["_ambientLux", 1, [0]],
    ["_kd", 0, [0]],
    ["_disturbance", 0, [0]],
    ["_elapsed", 0, [0]]
];

private _dark = _ambientLux < 0.01;
private _clear = _kd < 0.2;
private _stirred = _disturbance > 0;
private _visible = _dark && _clear && _stirred;

private _intensity = 0;
if (_visible && _elapsed > 0) then {
    private _tauRise = 0.077;
    private _tauDecay = 0.5;
    private _envelope = (exp (-_elapsed / _tauDecay)) * (1 - exp (-_elapsed / _tauRise));
    _intensity = (_disturbance min 1) * _envelope;
};

[_visible, _intensity]
