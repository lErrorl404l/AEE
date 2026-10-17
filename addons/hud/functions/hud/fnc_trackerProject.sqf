#include "..\..\script_component.hpp"
/*
 * aee_hud_fnc_trackerProject
 *
 * Pure tracker projector: the position a GPS receiver REPORTS for a unit.
 * It reads no world, no config, no player and no engine state.
 *
 * With a fix (3D or 2D) the receiver reports the true position displaced by
 * its current horizontal error (fnc_gnssErrorStep, a time-correlated draw
 * from the fix covariance).  Without one it keeps reporting the last fixed
 * position, so the track freezes where the fix was lost.
 *
 * Arguments:
 *   0: exactPos <ARRAY>  true position [x, y, z], metres
 *   1: ellipse  <ARRAY>  the fnc_gnssErrorEllipse return
 *   2: quality  <STRING> "ok", "degraded" or "none" (fnc_gnssFixState)
 *   3: error    <ARRAY>  [east, north] horizontal error, metres
 *   4: heldPos  <ARRAY>  the last reported position ([] if none)
 *   5: trackAge <NUMBER> seconds since the report was received
 *
 * Return: [displayedPos, semiMajor, semiMinor, orientation, trackAge, totalError]
 *   totalError is the horizontal distance from the true position, metres.
 */
params [
    ["_exactPos", [0, 0, 0], [[]]],
    ["_ellipse", [], [[]]],
    ["_quality", "none", [""]],
    ["_error", [0, 0], [[]]],
    ["_heldPos", [], [[]]],
    ["_trackAge", 0, [0]]
];
private _semiMajor = 0;
private _semiMinor = 0;
private _orientation = 0;
if ((count _ellipse) > 5) then {
    _semiMajor = (_ellipse select 3) max 0;
    _semiMinor = (_ellipse select 4) max 0;
    _orientation = _ellipse select 5;
};
private _displayed = _exactPos;
if (_quality isEqualTo "none") then {
    if ((count _heldPos) > 2) then { _displayed = _heldPos; };
} else {
    if ((count _error) > 1) then {
        _displayed = [(_exactPos select 0) + (_error select 0), (_exactPos select 1) + (_error select 1), _exactPos select 2];
    };
};
private _dx = (_displayed select 0) - (_exactPos select 0);
private _dy = (_displayed select 1) - (_exactPos select 1);
[_displayed, _semiMajor, _semiMinor, _orientation, _trackAge, sqrt (_dx * _dx + _dy * _dy)]
