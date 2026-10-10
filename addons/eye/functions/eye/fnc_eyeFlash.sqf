#include "..\..\script_component.hpp"

/*
Muzzle-flash illuminance for the eye model.

A muzzle flash raises the scene luminance for a moment. The engine exposes
the flash strength as CfgAmmo visibleFire, which has no published mapping to
lux, so the scale below is UNSOURCED and declared here in one place. A
suppressed weapon cuts the visible flash by the suppressor ratio, also
UNSOURCED.

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

private _scale = 1500;          // UNSOURCED: lux per visibleFire unit
private _suppressFactor = 0.25; // UNSOURCED: suppressed visible-flash ratio

private _lux = _ammoVisibleFire * _scale;
if (_suppressed) then { _lux = _lux * _suppressFactor; };

_lux
