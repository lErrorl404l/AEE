#include "..\script_component.hpp"

/*
 * Author: AEE Dev Team
 * Calculate magnetic field anomaly at a position using the dipole model.
 *
 * The anomaly is the deviation from Earth's background field caused by
 * ferrous objects (vehicles, structures, buried ordnance, mineral deposits).
 *
 * Dipole flux density (Blakely 1995, SI):
 *   B = (mu0 / 4pi) * M / r^3 * sqrt(1 + 3cos^2(theta))
 *   mu0 = 4pi * 1e-7 T m / A (vacuum permeability, CODATA)
 *
 * Where:
 *   M = magnetic dipole moment (A m^2)
 *   r = distance from dipole centre (m)
 *   theta = angle between sensor-dipole line and dipole axis
 *
 * Detection ranges (NATO MAD specs):
 *   Vehicle/engine block:   10-50 m
 *   Steel structure:        5-30 m
 *   Buried ordnance/IED:    0.1-2 m (ground-penetrating)
 *   Mineral deposit:        10-100 m (large, diffuse)
 *
 * Arguments:
 *   0: Array [sx, sy, sz] - sensor position (AGL, metres)
 *   1: Array [ax, ay, az] - anomaly source position (AGL, metres)
 *   2: Number             - dipole moment M (A m^2, default 1000)
 *   3: Number (optional)  - dipole tilt from vertical in degrees (default 0)
 *
 * Returns:
 *   Number - magnetic field deviation in nanotesla (nT)
 *   Returns 0 if distance < 0.1 m (sensor inside source).
 *
 * Example:
 *   [[100, 200, 1.5], [105, 200, 0], 5000] call FUNC(calculateMagneticAnomaly);
 *
 * Reference:
 *   Blakely, R.J. (1995) Potential Theory in Gravity and Magnetic Applications.
 *   Cambridge University Press.
 *   NGA World Magnetic Model (WMM2025).
 */

params [
    ["_sensorPos", [0, 0, 0], [[]]],
    ["_sourcePos", [0, 0, 0], [[]]],
    ["_dipoleMoment", 1000, [0]],
    ["_tiltDeg", 0, [0]]
];

private _r = _sensorPos distance _sourcePos;

// Guard: sensor inside source — no meaningful dipole field.
if (_r < 0.1) exitWith {0};

// Unit vector from source to sensor.
private _dx = (_sensorPos select 0) - (_sourcePos select 0);
private _dz = (_sensorPos select 2) - (_sourcePos select 2);

// Dipole axis: vertical by default, tilted by _tiltDeg degrees.
// Vertical component dominates in most military scenarios.
// SQF sin/cos take degrees; _tiltDeg is already degrees.
private _axisX = sin _tiltDeg;
private _axisZ = cos _tiltDeg;

// cos(theta) = dot product of (unit sensor vector) and (dipole axis).
private _cosTheta = (_dx * _axisX + _dz * _axisZ) / _r;

// Dipole flux density: B = (mu0 / 4pi) * M / r^3 * sqrt(1 + 3cos^2(theta)).
// The mu0 factor makes this a flux density (tesla), not the magnetic field
// strength H (A/m); without it the result is ~795775x too large.
// Result in tesla; convert to nanotesla (x 1e9).
private _r3 = _r * _r * _r;
private _mu0 = 4 * pi * 1e-7;   // vacuum permeability, T m / A (CODATA)
private _bField = ((_mu0 / (4 * pi)) * _dipoleMoment / _r3) * sqrt(1 + 3 * _cosTheta * _cosTheta);

// Convert to nanotesla.
_bField * 1e9
