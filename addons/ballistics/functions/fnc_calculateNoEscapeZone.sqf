#include "..\script_component.hpp"

/*
No-escape zone (pure).

    NEZ = min( R_kinematic, R_seeker ) * margin

    R_kinematic  range the missile can still reach the target kinematically, m
    R_seeker     range at which the seeker holds the target, m
    margin       fraction of the smaller range that is the guaranteed zone,
                 0.7 to 0.9 (issue #131)

Inside the NEZ the target cannot outrun the missile even with its best
manoeuvre.  The margin exists because the two ranges are limits, not
guarantees, so the zone is drawn inside both.

MARGIN IS UNSOURCED.  The 0.7 to 0.9 band is the issue's stated figure; no
named source fixes it.  The caller supplies the margin; this kernel only
takes the smaller of the two ranges and scales it.

Arguments:
  0: _kinematicRangeM (NUMBER) R_kinematic, m, >= 0
  1: _seekerRangeM    (NUMBER) R_seeker, m, >= 0
  2: _margin          (NUMBER) fraction, 0..1, default 0.8

Return Value: NUMBER - no-escape-zone radius in metres.  Returns 0 when
either range is zero (no zone).
Public: No
*/

params [
    ["_kinematicRangeM", 0, [0]],
    ["_seekerRangeM", 0, [0]],
    ["_margin", 0.8, [0]]
];

private _kinematic = _kinematicRangeM max 0;
private _seeker = _seekerRangeM max 0;
if (_kinematic <= 0 || _seeker <= 0) exitWith { 0 };

private _m = (_margin max 0) min 1;

(_kinematic min _seeker) * _m
