#include "..\..\script_component.hpp"

/*
Steady-state pupil diameter for a scene luminance.

The pupil sets the retinal illuminance. Its steady diameter follows the
de Groot and Gebhard (1952) JOSA 42(7):492 fit against the luminance in
millilambert (1 mL = 10000/pi cd/m2, the definition of the lambert). The
tanh form is the closed form of that fit:

  d = 4.9 - 3.0 * tanh(0.4 * (log10(B_mL) + 0.5))

TRACED: de Groot and Gebhard 1952 JOSA 42(7):492.
UNSOURCED: the 1.9 and 8.0 mm clamps are guards around the fit. The fit
itself is valid from about 2 mm (bright) to above 8 mm (dark); the clamps
stop a pathological input from leaving the physiological range.

Arguments:
  0: Number - scene luminance, cd/m2

Returns:
  Number - steady pupil diameter in mm, clamped to [1.9, 8.0].
*/

params [["_lum", 0, [0]]];

private _b = _lum / 3.183;   // cd/m2 -> millilambert (10000/pi)
private _x = 0.4 * ((log _b) + 0.5);
private _e = exp (2 * _x);

private _d = 4.9 - (3.0 * ((_e - 1) / (_e + 1)));
_d = (_d max 1.9) min 8.0;

_d
