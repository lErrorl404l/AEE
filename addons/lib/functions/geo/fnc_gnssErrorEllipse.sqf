#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_gnssErrorEllipse
 *
 * The horizontal error ellipse of a GPS fix from its geometry.  Pure.
 *
 * The position-error covariance is UERE^2 Q, Q the cofactor matrix of the
 * received satellites (fnc_gnssDop; GPS SPS PS 2020 App. A.8.2), UERE the
 * user range error (fnc_gnssUere).  So
 *   sigma_E^2 = UERE^2 qEE,  sigma_N^2 = UERE^2 qNN,  cov_EN = UERE^2 qEN,
 *   sigma_U^2 = UERE^2 qUU,
 * the ellipse axes are the eigenvalues of the 2 x 2 horizontal block and the
 * semi-major bearing its eigenvector.  The 95 % radius is 2DRMS (SPS PS App.
 * A.8.2, factor 2.0).  CEP ~ 0.59 (sigma_a + sigma_b) (van Diggelen, "GNSS
 * accuracy: lies, damn lies, and statistics", GPS World, Jan 2007).
 *
 * Arguments:
 *   0: dop  <ARRAY> the fnc_gnssDop return [count, qEE, qNN, qEN, qUU]
 *   1: uere <NUMBER> user range error, metres, 1 sigma
 *
 * Return: [sigmaEast, sigmaNorth, sigmaUp, semiMajor, semiMinor,
 *          orientation, cep, r95, covEN]; all -1 with no solution (fewer
 *          than 4 satellites).  orientation: semi-major bearing, deg from
 *          north.
 */
params [["_dop", [0, -1, -1, -1, -1], [[]]], ["_uere", 1.3, [0]]];
if ((count _dop) < 5) exitWith { [-1, -1, -1, -1, -1, 0, -1, -1, 0] };
private _count = _dop select 0;
private _qEE = _dop select 1;
private _qNN = _dop select 2;
private _qEN = _dop select 3;
private _qUU = _dop select 4;
if (_count < 4 || _qEE < 0 || _qNN < 0) exitWith { [-1, -1, -1, -1, -1, 0, -1, -1, 0] };
private _u2 = _uere * _uere;
private _cEE = _qEE * _u2;
private _cNN = _qNN * _u2;
private _cEN = _qEN * _u2;
private _sigmaE = sqrt _cEE;
private _sigmaN = sqrt _cNN;
private _sigmaU = sqrt ((_qUU max 0) * _u2);
private _mean = (_cEE + _cNN) / 2;
private _rad = sqrt ((((_cEE - _cNN) / 2) ^ 2) + (_cEN * _cEN));
private _semiMajor = sqrt (_mean + _rad);
private _semiMinor = sqrt ((_mean - _rad) max 0);
// Angle of the major axis from east (counter-clockwise), then as a bearing.
private _fromEast = 0.5 * ((2 * _cEN) atan2 (_cEE - _cNN));
private _orientation = (((90 - _fromEast) mod 180) + 180) mod 180;
private _cep = 0.59 * (_semiMajor + _semiMinor);
private _r95 = 2.0 * sqrt (_cEE + _cNN);
[_sigmaE, _sigmaN, _sigmaU, _semiMajor, _semiMinor, _orientation, _cep, _r95, _cEN]
