#include "..\..\script_component.hpp"

/*
Eye adaptation temporal state (perception consumption, pure mapping).

The eye adaptation driver publishes its temporal state for the perception
monitor.  This kernel folds the raw published values into the four fields
the perception schema carries for `eyeAdaptationState`:

  [level, target, direction, timeToAdapt]

The level is the same weighted-log definition the eye adaptation model uses:
level = mesopic * coneLog + (1 - mesopic) * rodLog, in log10 cd/m2.  The
target is the published scene target in lux.  The direction and the time to
adapt are read from the published state.  A defensive fallback derives them
from the level and the target when the published direction reports settled
but the log gap does not.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The
perception driver reads the published values and calls this.

Published names this kernel consumes (bound in the driver, not here):
  aee_optics_eyeAdaptState          [coneLog, rodLog]
  aee_optics_eyeAdaptTargetLux      scene target, lux
  aee_optics_eyeAdaptDirection      -1, 0 or +1
  aee_optics_eyeAdaptTau            effective tau, s
  aee_optics_eyeAdaptTimeToAdapt    time to adapt, s
  aee_optics_eyeMesopic             mesopic photopic fraction, 0 to 1

Constants (graded):
  SETTLED_LOG   0.05 log10.  UNSOURCED.  It matches the eye adaptation
                model's own settled tolerance, about 12 % of luminance.  It
                only decides whether the fallback reports a direction.
  LOG_FLOOR     1e-9.  UNSOURCED.  It guards log10 of a non-positive target.
  TAU_95        ln(20), about 2.9957.  SOURCED: a first-order lag covers
                95 % of the remaining distance in tau * ln(20).  The eye
                adaptation model uses the same factor.

Arguments:
  0: Array  - pool state [coneLog, rodLog]
  1: Number - scene target, lux
  2: Number - mesopic photopic fraction, 0 to 1
  3: Number - published direction, -1, 0 or +1
  4: Number - effective tau, s
  5: Number - published time to adapt, s

Returns:
  Array - [level, target, direction, timeToAdapt]
*/

params [
    ["_state", [0, 0], [[]]],
    ["_targetLux", 1, [0]],
    ["_mesopic", 1, [0]],
    ["_direction", 0, [0]],
    ["_tau", 0, [0]],
    ["_timeToAdapt", 0, [0]]
];

private _cone = 0;
private _rod = 0;
if ((_state isEqualType []) && {(count _state) >= 2}) then {
    _cone = _state select 0;
    _rod = _state select 1;
};
if !(_cone isEqualType 0) then { _cone = 0; };
if !(_rod isEqualType 0) then { _rod = 0; };

private _w = _mesopic;
if !(_w isEqualType 0) then { _w = 1; };
_w = (_w max 0) min 1;

if !(_targetLux isEqualType 0) then { _targetLux = 1; };

private _level = (_w * _cone) + ((1 - _w) * _rod);

// The published direction is authoritative.  Derive it only when the
// published value reports settled and the log gap says it is not.
private _dir = _direction;
if !(_dir isEqualType 0) then { _dir = 0; };
_dir = (round _dir) max -1 min 1;
if (_dir == 0) then {
    private _targetLog = log ((_targetLux max 1e-9) min 1e12);
    private _gap = _targetLog - _level;
    if (_gap > 0.05) then { _dir = 1; };
    if (_gap < -0.05) then { _dir = -1; };
};

private _time = _timeToAdapt;
if !(_time isEqualType 0) then { _time = 0; };
if (_time <= 0) then {
    private _tauEff = _tau;
    if !(_tauEff isEqualType 0) then { _tauEff = 0; };
    if (_tauEff > 0) then { _time = _tauEff * (ln 20); };
};

[_level, _targetLux, _dir, _time]
