#include "..\..\script_component.hpp"

/*
Standard fuel-model parameters for the Rothermel spread model.

Three of the thirteen standard fire behaviour fuel models (Albini 1976,
INT-GTR-30; Anderson 1982, INT-122) cover the engine's vegetation types:

  grass   -> fuel model 1  (short grass)
  scrub   -> fuel model 5  (brush, low load)
  forest  -> fuel model 8  (closed timber litter)

Each model is represented by its 1-hour fine dead fuel class, the fuel that
carries the flaming front: the surface-area-to-volume ratio (sigma), oven-dry
fuel load (w0), fuel bed depth (delta) and moisture of extinction (Mx).  Heat
content (8000 BTU/lb), total mineral content (0.0555) and effective mineral
content (0.01) are the standard values shared by all models and live in
fnc_rothermelSpread.

Source: Albini, F. A. (1976) "Estimating Wildfire Behavior Effects", USDA
Forest Service General Technical Report INT-GTR-30 (fuel model table);
Anderson, H. E. (1982) "Aids to Determining Fuel Models for Estimating Fire
Behavior", INT-122.

Params:
  _fuelModel   "grass", "scrub" or "forest"

Returns [sigma ft^-1, w0 kg/m^2, delta m, Mx fraction].
*/

params [["_fuelModel", "grass", [""]]];

private _params = [3500, 0.165886, 0.3048, 0.12];      // fuel model 1
if (_fuelModel isEqualTo "scrub") then {
    _params = [2000, 0.224592, 0.6096, 0.20];          // fuel model 5
};
if (_fuelModel isEqualTo "forest") then {
    _params = [2000, 0.336888, 0.06096, 0.30];         // fuel model 8
};

_params
