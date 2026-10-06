#include "..\..\script_component.hpp"

/*
Published adaptation state.

Reports the adaptation for the player-perception monitor: which way the eye
is moving and how long it will take.  The level moves as a first-order lag
toward the scene target, so the time to cover 95 % of the remaining distance
is tau * ln(20), about 3 tau.  The effective tau is the SLOWEST pool that must
travel, because the rod pool gates dark adaptation and the fast pupil branch
is not the limit at these time scales.

Direction is +1 when the eye is light-adapting (target brighter), -1 when it
is dark-adapting (target darker), and 0 when it is settled.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Array  - pool state [coneLog, rodLog]
  1: Number - target log10 luminance, cd/m2
  2: Number - mesopic photopic fraction, 0 scotopic to 1 photopic
  3: Number - light-adaptation tau, s
  4: Number - cone dark tau, s
  5: Number - rod dark tau, s

Returns:
  Array - [direction, tauS, timeToAdaptS].  direction is -1, 0 or 1.
*/

params [
    ["_state", [0, 0], [[]]],
    ["_targetLog", 0, [0]],
    ["_mesopic", 1, [0]],
    ["_tauLight", 2.0, [0]],
    ["_tauDarkCone", 120, [0]],
    ["_tauDarkRod", 400, [0]]
];

private _xCone = _state select 0;
private _xRod = _state select 1;
private _level = (_mesopic * _xCone) + ((1 - _mesopic) * _xRod);
private _delta = _targetLog - _level;

// Settled within 0.05 log10 (about 12 % of luminance).  UNSOURCED tolerance:
// it only decides whether the monitor reports "settled" or a direction.
private _settled = 0.05;
private _direction = 0;
if (_delta > _settled) then { _direction = 1; };
if (_delta < -_settled) then { _direction = -1; };

private _tauCone = _tauDarkCone;
if (_targetLog >= _xCone) then { _tauCone = _tauLight; };
private _tauRod = _tauDarkRod;
if (_targetLog >= _xRod) then { _tauRod = _tauLight; };
private _tau = _tauCone max _tauRod;

// First-order lag: 95 % of the move in tau * ln(20).
private _timeToAdapt = _tau * (ln 20);

[_direction, _tau, _timeToAdapt]
