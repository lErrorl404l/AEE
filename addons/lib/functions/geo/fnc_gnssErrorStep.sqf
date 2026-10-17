#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_gnssErrorStep
 *
 * One step of the time-correlated horizontal GPS position error.  Pure.
 *
 * Successive standalone-GPS position errors are correlated; a first-order
 * Gauss-Markov process describes them, with a measured correlation time of
 * about 4 minutes (N. Abu Ali & M. Abu-Elkheir, "Improving localization
 * accuracy: successive measurements error modeling", Sensors 15 (2015)
 * 15540, doi:10.3390/s150715540):
 *   e_k = phi e_{k-1} + sqrt(1 - phi^2) w,   phi = exp(-dt / tau),
 * w drawn from the fix's own covariance (Cholesky of [[cEE, cEN],
 * [cEN, cNN]]), so the error wanders with the right size and shape and the
 * displayed track drifts instead of jumping.
 *
 * Arguments:
 *   0: prevError <ARRAY>  [east, north] metres ([] at first)
 *   1: ellipse   <ARRAY>  the fnc_gnssErrorEllipse return
 *   2: dt        <NUMBER> seconds
 *   3: u1, u2    <NUMBER> two uniform (0, 1) draws (deterministic RNG)
 * Return: [east, north] metres
 */
params [["_prev", [], [[]]], ["_ellipse", [], [[]]], ["_dt", 1, [0]], ["_u1", 0.5, [0]], ["_u2", 0.5, [0]]];
if ((count _ellipse) < 9 || {(_ellipse select 0) < 0}) exitWith { [0, 0] };
private _sE = _ellipse select 0;
private _sN = _ellipse select 1;
private _cEN = _ellipse select 8;
// Box-Muller: two independent standard normals.
private _r = sqrt (-2 * ln ((_u1 max 1e-6) min 1));
private _z1 = _r * (cos (360 * _u2));
private _z2 = _r * (sin (360 * _u2));
// Correlated draw with the fix covariance (2 x 2 Cholesky).
private _wE = _sE * _z1;
private _rho = if (_sE > 0 && _sN > 0) then { (_cEN / (_sE * _sN)) max -0.999 min 0.999 } else { 0 };
private _wN = _sN * ((_rho * _z1) + (sqrt (1 - _rho * _rho)) * _z2);
private _tau = 240;
private _phi = exp (-((_dt max 0) / _tau));
private _k = sqrt (1 - _phi * _phi);
if ((count _prev) < 2) exitWith { [_wE, _wN] };
[((_prev select 0) * _phi) + (_k * _wE), ((_prev select 1) * _phi) + (_k * _wN)]
