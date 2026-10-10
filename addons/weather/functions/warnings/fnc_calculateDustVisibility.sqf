#include "..\..\script_component.hpp"

/*
Blowing-dust (haboob) visibility (issue #106).

A dust storm scatters and absorbs light, and the visibility falls as the
airborne mass concentration rises.  Baddock et al. (2014) relate the two
with a single power law over the concentration range a haboob covers:

  V_km = k / C          k = 0.5 km*mg/m3, C in mg/m3

The paper splits the relation into two regimes at 3.5 km, but the brief
gives one constant for the whole range, so one constant is used here.

The issue's states, expressed as concentration bands:
  moderate  100 to 1000 ug/m3 (0.1 to 1 mg/m3)   0.5 to 5 km
  severe    1 to 10 mg/m3                        50 to 500 m
  extreme   above 10 mg/m3                       below 50 m

The result is turned into the 0 to 1 intensity the FX layer consumes.  The
mapping is a MODELLING CHOICE anchored on the issue's visibility states:
5 km moderate onset, 0.5 km, and 0.05 km extreme onset.

Koschmieder 1924 relates the visibility to the extinction coefficient,
sigma = 3.912 / V_km, and that value is returned for the optical layer.

Args:
  0: dust concentration (NUMBER, mg/m3, default 0)

Returns a HashMap with the keys:
  visibilityKm     V, km (300 when the air is clear)
  extinctionPerKm  sigma, km^-1 (Koschmieder)
  state            "none" / "moderate" / "severe" / "extreme"
  intensity        0..1, for the FX layer
*/

params [["_concentration", 0, [0]]];

// Baddock et al. 2014.
private _k = 0.5;

private _visKm = 300;
if (_concentration > 0) then { _visKm = _k / _concentration; };

private _state = "none";
if (_visKm < 5) then { _state = "moderate"; };
if (_visKm < 0.5) then { _state = "severe"; };
if (_visKm < 0.05) then { _state = "extreme"; };

// Intensity for the FX layer, anchored on the state boundaries above.
private _intensity = 0;
if (_visKm < 5) then { _intensity = 0.5 * (5 - _visKm) / 4.5; };
if (_visKm < 0.5) then { _intensity = 0.5 + (0.5 * (0.5 - _visKm) / 0.45); };
_intensity = _intensity max 0 min 1;

private _extinction = 3.912 / _visKm;

createHashMapFromArray [
    ["visibilityKm", _visKm],
    ["extinctionPerKm", _extinction],
    ["state", _state],
    ["intensity", _intensity]
]
