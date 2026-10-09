#include "..\..\script_component.hpp"

/*
One adaptation step for the two slow pools.

The dark branch of the eye is biphasic (Lamb and Pugh 2004, Prog Retin Eye
Res 23:307-380): a fast cone component and a slow rod component. Each pool
chases the target log-luminance with its own first-order lag. A pool that
must BRIGHTEN uses the light tau; a pool that must DARKEN uses its dark tau.
Light and dark adaptation are asymmetric: dark adaptation is far slower.

The two pools are the cone pool and the rod pool. This kernel returns them
separately. The mesopic combine happens in the driver.

Arguments:
  0: Array - previous state [coneLog, rodLog]
  1: Number - target log10 luminance (cd/m2)
  2: Number - time step, s
  3: Number - light-adaptation tau, s
  4: Number - cone dark tau, s
  5: Number - rod dark tau, s
  6: Number - mesopic photopic fraction (accepted for signature symmetry;
             the combine is done by the driver, not here)

Returns:
  Array - the two updated pool logs [coneLog, rodLog].
*/

params [
    ["_state", [0, 0], [[]]],
    ["_targetLogLum", 0, [0]],
    ["_dt", 0, [0]],
    ["_tauLight", 2.0, [0]],
    ["_tauDarkCone", 120, [0]],
    ["_tauDarkRod", 400, [0]],
    ["_w", 0, [0]]
];

private _xCone = _state select 0;
private _xRod = _state select 1;

private _tauCone = _tauDarkCone;
if (_targetLogLum >= _xCone) then { _tauCone = _tauLight; };
private _tauRod = _tauDarkRod;
if (_targetLogLum >= _xRod) then { _tauRod = _tauLight; };

private _newCone = _xCone + ((_targetLogLum - _xCone) * (1 - (exp (- (_dt / _tauCone)))));
private _newRod = _xRod + ((_targetLogLum - _xRod) * (1 - (exp (- (_dt / _tauRod)))));

[_newCone, _newRod]
