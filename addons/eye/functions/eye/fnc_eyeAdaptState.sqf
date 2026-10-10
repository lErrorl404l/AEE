#include "..\..\script_component.hpp"

/*
Published adaptation state.

Reports the adaptation for the player-perception monitor: which way the eye
is moving and how long it will take.  The level moves as a first-order lag
toward the scene target.  The effective tau is the SLOWEST pool that must
travel, because the rod pool gates dark adaptation and the fast pupil branch
is not the limit at these time scales.

Direction is +1 when the eye is light-adapting (target brighter), -1 when it
is dark-adapting (target darker), and 0 when it is settled.

When the eye is SETTLED it reports tau 0 and time 0: no adaptation is pending.
This is not cosmetic.  The pool comparison that picks the tau flips to the
slow dark branch on a floating-point hair when a settled pool sits a hair
above the target, so without the settled guard a settled eye reported the dark
95 % time (~20 minutes) and the perception monitor read it as a stuck eye.

When the eye is adapting the time is the ACTUAL time to close the remaining
log gap to the settled tolerance under the effective first-order lag,
tau * ln(|delta| / settled).  It falls as the eye approaches the target and
reaches zero when it settles, which is what the monitor's stuckAdaptation test
(a time that does not fall) needs.  A constant tau * ln(20) never falls and
false-fired that flag on every adapting window.

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
// it decides the reported direction and whether any adaptation is pending.
private _settled = 0.05;
private _direction = 0;
if (_delta > _settled) then { _direction = 1; };
if (_delta < -_settled) then { _direction = -1; };

// A settled eye has nothing pending, so it reports no tau and no time.  The
// tau comparison alone is not enough: it flips to the slow dark branch on a
// floating-point hair when a settled pool sits a hair above the target.
private _tau = 0;
private _timeToAdapt = 0;
if (_direction != 0) then {
    private _tauCone = _tauDarkCone;
    if (_targetLog >= _xCone) then { _tauCone = _tauLight; };
    private _tauRod = _tauDarkRod;
    if (_targetLog >= _xRod) then { _tauRod = _tauLight; };
    _tau = _tauCone max _tauRod;

    // Time to close the remaining log gap to the settled tolerance under the
    // effective first-order lag.  Falls as the eye approaches, zero on settle.
    _timeToAdapt = _tau * (ln ((abs _delta) / _settled));
};

[_direction, _tau, _timeToAdapt]
