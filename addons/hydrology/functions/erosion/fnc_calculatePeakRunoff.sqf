#include "..\..\script_component.hpp"
/*
Event peak runoff rate for MUSLE (issue #21).

The MUSLE term (Q * qp)^0.56 needs the peak runoff rate qp. The published
relation is the NRCS triangular unit hydrograph: the direct-runoff volume is
the triangle 0.5 * qp * Tb, with the time base Tb = 2.67 * Tp (the NRCS peak
rate factor 484; TR-55 1986; NEH Part 630 chapter 16). In SI units that is

  qp = 0.208 * A * Q / Tp         A km2, Q mm, Tp h -> qp m3/s

and 0.208 is 484 times the unit conversion. Because A * Q = V / 1000 for the
runoff volume V in m3, the expression reduces to qp = 0.000208 * V / Tp: the
caller can pass either form.

The time to peak is the SCS lag relation Tp = D/2 + 0.6 * Tc (the NRCS lag is
tl = 0.6 * tc), with D the excess-rainfall duration. The time of concentration
Tc is Kirpich (1940):

  Tc[min] = 0.0195 * L^0.77 * S^-0.385        L m, S m/m

The US form 0.0078 * L^0.77 * S^-0.385 with L in feet converts to 0.0195 in
SI (0.0195 / 0.0078 = 3.2808^0.77).

MODELLING CHOICE (stated, not published): the RUSLE slope length is used as
the Kirpich hydraulic length. The two are the same overland-flow path in this
model, so no second terrain sweep is needed.

Sources:
  Kirpich, Z.P. (1940) "Time of concentration of small agricultural
    watersheds", Civil Engineering 10(6):362 (SI form).
  USDA NRCS TR-55 (1986) "Urban Hydrology for Small Watersheds"; NRCS
    National Engineering Handbook Part 630, chapter 16 (Hydrographs).
  Williams, J.R. (1975) "Sediment-yield prediction with universal equation
    using runoff energy factor", USDA ARS-S-40, pp. 244-251 (MUSLE).

Args:
  0: runoff volume V (NUMBER, m3, default 0)
  1: slope length L (NUMBER, m, default 22.13, the RUSLE unit plot)
  2: slope (NUMBER, rise/run m/m, default 0)
  3: excess-rainfall duration D (NUMBER, h, default 0)

Returns the peak runoff rate qp in m3/s, never below zero.

Example:
  [1000, 100, 0.10, 0.5] call aee_hydrology_fnc_calculatePeakRunoff -> 0.78076
*/

params [
    ["_volumeM3", 0, [0]],
    ["_slopeLengthM", 22.13, [0]],
    ["_slopeFraction", 0, [0]],
    ["_rainDurationH", 0, [0]]
];

if !(_volumeM3 isEqualType 0) then { _volumeM3 = 0; };
if !(_slopeLengthM isEqualType 0) then { _slopeLengthM = 22.13; };
if !(_slopeFraction isEqualType 0) then { _slopeFraction = 0; };
if !(_rainDurationH isEqualType 0) then { _rainDurationH = 0; };

private _v = _volumeM3 max 0;
if (_v <= 0) exitWith { 0 };

// Kirpich (1940) time of concentration in minutes. Floors keep the two powers
// total at a zero length or a zero slope.
private _l = _slopeLengthM max 1;
private _s = _slopeFraction max 0.0005;
private _tcMin = 0.0195 * (_l ^ 0.77) / (_s ^ 0.385);

// SCS lag: Tp = D/2 + 0.6 * Tc.
private _tp = ((_rainDurationH max 0) / 2) + (0.6 * (_tcMin / 60));
_tp = _tp max 0.001;

// SCS triangular unit-hydrograph peak in SI (0.208 * A * Q / Tp).
0.000208 * _v / _tp
