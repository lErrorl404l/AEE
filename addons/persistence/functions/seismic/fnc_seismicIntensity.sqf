#include "..\..\script_component.hpp"
/*
Macroseismic intensity (MMI) from peak ground acceleration.

MMI is the published shaking-severity scale.  Both the ground-motion driver
and the camera-shake kernel read the same value from this kernel, so the
engine-facing shake strength is driven by the published intensity, not by an
arbitrary PGA quotient.

Source: Worden, C.B., Gerstenberger, M.C., Rhoades, D.A. and Wald, D.J.
(2012) "Probabilistic relationships between ground-motion parameters and
Modified Mercalli intensity in California", Bulletin of the Seismological
Society of America 102(1):204-221.  DOI 10.1785/0120110156.
Piecewise-linear in log10(PGA), with PGA in cm/s^2:

  log10(PGA) < 0.14         MMI = 1.71 + 2.08*log10(PGA)
  0.14 <= log10(PGA) < 1.57 MMI = 1.78 + 1.55*log10(PGA)
  log10(PGA) >= 1.57        MMI = -1.60 + 3.70*log10(PGA)

The three segments join at log10(PGA) = 1.57.  The result matches the USGS
ShakeMap instrumental-intensity table at its band edges (0.115 g -> VI,
0.215 g -> VII, 0.401 g -> VIII).  MMI is clamped to 1..12.

Input:  _pgaG   - peak ground acceleration (g)
Output: Number - MMI, clamped to 1..12
Public: No

Example: [0.5] call aee_persistence_fnc_seismicIntensity -> 8.35
*/

params [["_pgaG", 0, [0]]];

if !(_pgaG isEqualType 0) then { _pgaG = 0; };

private _pgaCms2 = (_pgaG max 0) * 980.665;
private _l = log (_pgaCms2 max 0.0001);

private _mmi = -1.60 + 3.70 * _l;
if (_l < 1.57) then { _mmi = 1.78 + 1.55 * _l; };
if (_l < 0.14) then { _mmi = 1.71 + 2.08 * _l; };

(_mmi max 1) min 12
