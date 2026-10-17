#include "..\..\script_component.hpp"

/*
Muzzle-flash illuminance for the eye model.

A muzzle flash raises the scene illuminance at the eye for a moment. The
returned quantity is illuminance in lux. The physical chain for a flash of
luminous intensity I (candela) at range d is the inverse-square law
E = I / d^2 (illuminance on a surface perpendicular to the source; A. Ryer,
"Light Measurement Handbook", chapter 6). The
engine exposes the flash strength as CfgAmmo visibleFire, which carries no
published photometric unit and no range, so no sourced conversion to lux
exists. The two factors below are GAME TUNABLES: they stand in for I / d^2
and are declared here in one place so the calibration is visible.

ANCHOR (order of magnitude only).  A measured 5.56 x 45 mm muzzle flash
(flash suppressor removed) reaches up to 2 x 10^5 lux with a peak standard
deviation of 8.3 x 10^4 lux, measured at the objective lens of a
night-vision device: I. Pemcak et al., "Measurement of Flash Intensity at
the Muzzle of a Firearm and Possible Protection against its Effects",
Advances in Military Technology 19(2):253-267, 2024, DOI
10.3849/aimt.01843.  That is illuminance at a near-field receiver, not a
source intensity, and CfgAmmo visibleFire is not that illuminance, so the
scale stays a game tunable; the measurement only bounds the order of
magnitude.

A suppressed weapon cuts the visible flash. The engine exposes no ratio, so
the suppression factor is a second game tunable.

Arguments:
  0: Number - CfgAmmo visibleFire value
  1: Bool - true when a suppressor is fitted

Returns:
  Number - transient flash illuminance, lx.
*/

params [
    ["_ammoVisibleFire", 0, [0]],
    ["_suppressed", false, [false]]
];

// GAME TUNABLE: lux per visibleFire unit. No published photometric unit
// exists for CfgAmmo visibleFire, so this is a game calibration, not a
// physical constant.
private _scale = 1500;
// GAME TUNABLE: suppressed visible-flash ratio. The engine exposes no
// suppression ratio, so this is a game calibration.
private _suppressFactor = 0.25;

private _lux = _ammoVisibleFire * _scale;
if (_suppressed) then { _lux = _lux * _suppressFactor; };

_lux
