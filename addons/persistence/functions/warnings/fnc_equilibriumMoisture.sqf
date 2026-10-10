#include "..\..\script_component.hpp"

/*
Simard (1968) equilibrium moisture content (EMC) of fine dead fuel.

EMC is the moisture a dead fuel particle tends toward at a given air
temperature and relative humidity.  Simard's three-branch fit is the
standard form used by the US National Fire Danger Rating System.  The
branches are in degrees Fahrenheit and percent relative humidity, and the
result is a percent.

  RH < 10 :  0.03229 + 0.281073*RH - 0.000578*RH*T
  RH < 50 :  2.22749 + 0.160107*RH - 0.014784*T
  RH >= 50:  21.0606 + 0.005565*RH^2 - 0.00035*RH*T - 0.483199*RH

Source: Simard, A. J. (1968) "Fire Weather and the National Fire Danger
Rating System", as tabulated in NWCG S-490 (course material) and Fosberg
(1977).  The 1-hour fuel class uses this EMC directly.

Returns the EMC as a fraction, clamped to the physical 1 to 35 percent band.

Params:
  _tempC   air temperature, degrees Celsius
  _rhPct   relative humidity, percent
*/

params [["_tempC", 15, [0]], ["_rhPct", 50, [0]]];

private _tF = _tempC * 1.8 + 32;
private _rh = (_rhPct max 0) min 100;

// Start on the high-humidity branch, then override for the lower bands.
private _emcPct = 21.0606 + 0.005565 * _rh * _rh - 0.00035 * _rh * _tF - 0.483199 * _rh;
if (_rh < 50) then {
    _emcPct = 2.22749 + 0.160107 * _rh - 0.014784 * _tF;
};
if (_rh < 10) then {
    _emcPct = 0.03229 + 0.281073 * _rh - 0.000578 * _rh * _tF;
};

((_emcPct / 100) max 0.01) min 0.35
