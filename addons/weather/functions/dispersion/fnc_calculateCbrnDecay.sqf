#include "..\..\script_component.hpp"

/*
CBRN agent atmospheric decay: the persistence envelope, not a point half-life.

Source: first-order decay C(t) = C0 exp(-t/tau).  No point half-life is
published for any agent, so the agent table carries the JP 1-02 / FM 3-11.9
Table G-6 persistence band [t_lo, t_hi] in hours.  The true half-life lies
somewhere inside that band, so the kernel returns the ENVELOPE the band
implies, with the mapping

  tau_lo = t_lo / ln 2   ->  fast edge  cFast = C0 exp(-t / tau_lo)
  tau_hi = t_hi / ln 2   ->  slow edge  cSlow = C0 exp(-t / tau_hi)

so cFast <= cSlow for every t and the true concentration lies in
[cFast, cSlow].  The slow edge is the casualty-conservative one.  A caller
that holds a point half-life still gets the single decayed value.

The band is scaled to the air temperature by an Arrhenius slope:

  t_half(T) = t_half(T_ref) exp( (slope / R) (1 / T - 1 / T_ref) )

with T_ref = 298.15 K (25 C) and R = 8.314462618 J/(mol*K) (CODATA 2018).
This replaces the Q10 = 2 rule of thumb: the implied Q10 over 15 to 25 C runs
1.42 (CG) to 3.09 (VX) per agent, so one rule of thumb cannot serve them all.

The slope is the agent's published hydrolysis activation energy where one
exists, and the latent heat of vaporisation as the labelled INTERIM slope
otherwise (FM 3-11.9, January 2005, Appendix G, gives deltaHvap only):

  GD  64.25 kJ/mol  Wu et al. 2021, E3S Web Conf 267:02060,
                    doi:10.1051/e3sconf/202126702060 (HCl aqueous, pH 0.90,
                    20 C).
  HD 108.8 kJ/mol   Herriott 1947, J Gen Physiol 30(6):457-464,
                    doi:10.1085/jgp.30.6.457.  QUALIFIED: the hydrolysis of
                    the H.2TDG sulfonium salt over 20 to 100 C, a related
                    species, not neat HD.
  GB, VX, CG        no activation energy found, so the deltaHvap interim
                    slope applies.

This is the intrinsic atmospheric decay.  The environmental scaling of SURFACE
contamination is owned by the persistence kernel,
fnc_calculateCBRNPersistence, which uses the same slope, chosen the same way.

Arguments:
  0: initial concentration C0 (NUMBER, mg/m3)
  1: elapsed time t (NUMBER, hours)
  2: persistence band [t_lo, t_hi] (ARRAY, hours), or a point half-life
     (NUMBER, hours) for a caller that has one
  3: air temperature T (NUMBER, K).  Default 298.15 K (25 C), the temperature
     the tabulated band is quoted at
  4: latent heat of vaporisation (NUMBER, J/mol).  0 or absent means no
     temperature scaling (no agent)
  5: hydrolysis activation energy (NUMBER, J/mol).  0 or absent means use the
     latent heat as the interim slope

Returns [cFast, cSlow] (mg/m3) for a band, or the decayed concentration
(NUMBER, mg/m3) for a point half-life.
*/

params [
    ["_c0", 0, [0]],
    ["_elapsedH", 0, [0]],
    ["_band", 1, [[], 0]],
    ["_tempK", 298.15, [0]],
    ["_deltaHvapJmol", 0, [0]],
    ["_activationEnergyJmol", 0, [0]]
];

// A non-number or absent temperature cannot scale anything.
if !(_tempK isEqualType 0) then { _tempK = 298.15; };
if !(_deltaHvapJmol isEqualType 0) then { _deltaHvapJmol = 0; };
if !(_activationEnergyJmol isEqualType 0) then { _activationEnergyJmol = 0; };

// ─── Temperature — Arrhenius slope, published Ea first ──────────────────────
private _slopeJmol = [_deltaHvapJmol, _activationEnergyJmol] select (_activationEnergyJmol != 0);
private _tempFactor = 1;
if (_slopeJmol != 0) then {
    private _t = (_tempK max 1);
    _tempFactor = exp ((_slopeJmol / 8.314462618) * (1 / _t - 1 / 298.15));
};

// ─── Decay — the band envelope, or a point half-life ────────────────────────
if (_band isEqualType []) then {
    // A one-element band is a point; a reversed band is the same band.
    private _a = ((_band param [0, 1]) max 0.0001);
    private _b = ((_band param [1, _a]) max 0.0001);
    private _lo = _a min _b;
    private _hi = _a max _b;
    private _tauLo = ((_lo * _tempFactor) / ln 2) max 0.0001;
    private _tauHi = ((_hi * _tempFactor) / ln 2) max 0.0001;
    [
        _c0 * exp (-(_elapsedH / _tauLo)),
        _c0 * exp (-(_elapsedH / _tauHi))
    ]
} else {
    private _tau = (((_band max 0) * _tempFactor) / ln 2) max 0.0001;
    _c0 * exp (-(_elapsedH / _tau))
}
