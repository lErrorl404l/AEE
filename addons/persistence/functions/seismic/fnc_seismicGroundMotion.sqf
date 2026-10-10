#include "..\..\script_component.hpp"

/*
Ground-motion prediction (Boore and Atkinson 2008) and macroseismic
intensity (Worden et al. 2012).

The issue text proposed PGA = 10^(a + b*M + c*log10(R) + d*R) with
coefficients "from Boore-Atkinson 2008 or Akkar-Bommer 2010".  No published
GMPE has that form: both candidates take the logarithm of sqrt(Rjb^2 + h^2)
and neither has a linear d*R term.  This kernel implements the real
Boore-Atkinson 2008 (BA08) equation.

Source: Boore, D.M. and Atkinson, G.M. (2008) "Ground-motion prediction
equations for the average horizontal component of PGA, PGV, and 5%-damped
PSA at spectral periods between 0.01 s and 10.0 s", Earthquake Spectra
24(1):99-138.  DOI 10.1193/1.2830434.  Table 6.

    ln Y = F_M(M) + F_D(Rjb, M) + F_S(Vs30, Rjb, M)
    F_M  = e1*U + e2*SS + e3*NS + e4*RS + e5*(M-Mh) + e6*(M-Mh)^2  (M <= Mh)
         = e1*U + e2*SS + e3*NS + e4*RS + e7*(M-Mh)                 (M >  Mh)
    F_D  = (c1 + c2*(M - 4.5)) * ln(R) + c3*(R - 1),  R = sqrt(Rjb^2 + h^2)
    F_S  = blin*ln(Vs30/760) + fnl(...)

This kernel evaluates the equation at the reference rock Vs30 = 760 m/s,
where the site term F_S is exactly zero (blin*ln(1) = 0 and the nonlinear
term vanishes on rock).  This is the reduction the source paper supports; it
is the simplest faithful form and the one the formula research recommended.
It is a rock-site GMPE: a soft soil site would give higher ground motion.

Y is PGA in g and PGV in cm/s.  The fault term is fixed to a normal fault
(NS = 1, all other dummies 0), the common case for the shallow crustal events
BA08 models.

Coefficients (BA08 Table 6):
    PGA  c1 -0.66050  c2 0.11970  c3 -0.01151  h 1.35
         e1 -0.53804  e2 -0.50350 e3 -0.75472  e4 -0.50970
         e5 0.28805   e6 -0.10164 e7 0.00000   Mh 6.75
    PGV  c1 -0.87370  c2 0.10060  c3 -0.00334  h 2.54
         e1 5.00121   e2 5.04727  e3 4.63188   e4 5.08210
         e5 0.18322   e6 -0.12736 e7 0.00000   Mh 8.50

Intensity from PGA follows Worden, C.B., Gerstenberger, M.C., Rhoades, D.A.
and Wald, D.J. (2012) "Probabilistic relationships between ground-motion
parameters and Modified Mercalli intensity in California", Bulletin of the
Seismological Society of America 102(1):204-221.  DOI 10.1785/0120110156.
Piecewise-linear in log10(PGA), with PGA in cm/s^2:

    log10(PGA) < 0.14         MMI = 1.71 + 2.08*log10(PGA)
    0.14 <= log10(PGA) < 1.57 MMI = 1.78 + 1.55*log10(PGA)
    log10(PGA) >= 1.57        MMI = -1.60 + 3.70*log10(PGA)

The three segments join at log10(PGA) = 1.57.  MMI is clamped to 1..12.  The
result matches the USGS ShakeMap instrumental-intensity table at its band
edges (0.115 g -> VI, 0.215 g -> VII, 0.401 g -> VIII).

Validity: BA08 is fitted over about Mw 5.0-8.0 and Rjb up to about 200 km.
Values outside that range are extrapolation and are flagged in the evidence.

Input:  [_magnitude, _rjbKm] - moment magnitude and Joyner-Boore distance
        (km).
Output: [PGA (g), PGV (cm/s), MMI]
Public: No
*/

params [
    ["_mag", 6.5, [0]],
    ["_rjbKm", 10, [0]]
];

if (_rjbKm < 0 || _mag < 0) exitWith { [0, 0, 1] };

// BA08 Table 6, layout [c1, c2, c3, h, e3, e5, e6, e7, Mh].
private _pga = [-0.66050, 0.11970, -0.01151, 1.35, -0.75472, 0.28805, -0.10164, 0.0, 6.75];
private _pgv = [-0.87370, 0.10060, -0.00334, 2.54, 4.63188, 0.18322, -0.12736, 0.0, 8.50];

private _dmPGA = _mag - (_pga select 8);
private _fmPGA = (_pga select 4) + (_pga select 5) * _dmPGA + (_pga select 6) * (_dmPGA ^ 2);
if (_mag > (_pga select 8)) then { _fmPGA = (_pga select 4) + (_pga select 7) * _dmPGA; };
private _rPGA = sqrt (_rjbKm * _rjbKm + (_pga select 3) * (_pga select 3));
private _fdPGA = ((_pga select 0) + (_pga select 1) * (_mag - 4.5)) * (ln _rPGA) + (_pga select 2) * (_rPGA - 1);
private _pgaG = exp (_fmPGA + _fdPGA);

private _dmPGV = _mag - (_pgv select 8);
private _fmPGV = (_pgv select 4) + (_pgv select 5) * _dmPGV + (_pgv select 6) * (_dmPGV ^ 2);
if (_mag > (_pgv select 8)) then { _fmPGV = (_pgv select 4) + (_pgv select 7) * _dmPGV; };
private _rPGV = sqrt (_rjbKm * _rjbKm + (_pgv select 3) * (_pgv select 3));
private _fdPGV = ((_pgv select 0) + (_pgv select 1) * (_mag - 4.5)) * (ln _rPGV) + (_pgv select 2) * (_rPGV - 1);
private _pgvCms = exp (_fmPGV + _fdPGV);

// Worden et al. 2012, piecewise-linear in log10(PGA) with PGA in cm/s^2.
private _pgaCms2 = _pgaG * 980.665;
private _l = log (_pgaCms2 max 0.0001);
private _mmi = -1.60 + 3.70 * _l;
if (_l < 1.57) then { _mmi = 1.78 + 1.55 * _l; };
if (_l < 0.14) then { _mmi = 1.71 + 2.08 * _l; };
private _mmiClamped = (_mmi max 1) min 12;

[_pgaG, _pgvCms, _mmiClamped]
