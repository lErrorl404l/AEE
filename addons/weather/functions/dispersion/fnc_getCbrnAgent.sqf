#include "..\..\script_component.hpp"

/*
CBRN agent parameters.

Source: FM 3-11.9 / MCRP 3-37.1B / NTRP 3-11.32 / AFTTP(I) 3-2.55, "Potential
Military Chemical/Biological Agents and Compounds", January 2005: the per-agent
Chapter II tables (II-3 CG, II-9 GB, II-11 GD, II-15 VX, II-25 HD) and the
Appendix G physical-property tables (G-1 vapour pressure and volatility, and
the latent heat of vaporisation used by the decay kernel).  The earlier
citation, "FM 3-11, Chemical Operations (2003), Table 4-1", was wrong: no
edition of FM 3-11 titled "Chemical Operations" was located, and FM 3-11 (2011)
carries no agent physical-property table.

  Agent  LCt50 (mg*min/m3)  VP @25 C (torr)  Volatility @25 C (mg/m3)
  VX     15   (Table II-15)  8.78e-4          12.6
  GB     35   (Table II-9)   2.48             1.87e4
  GD     35   (Table II-11)  0.401            3.93e3
  H/HD   1000 (Table II-25)  0.106            906
  CG     1500 (Table II-3)   1400             7.46e6

LCt50 is the vapour inhalation median-lethal exposure for a 15 min exposure,
mg*min/m3.  The rows are the FM 3-11.9 figures.  The values this table carried
before (VX 10, GB 85 as the midpoint of 70-100, GD 60 as the midpoint of 50-70,
H 1500, CG 3200) are the older FM 3-9-era set, which was not located in a
primary copy and is unverified.  The FM 3-11.9 set is the sourced one and it
also removes the row shift: FM 3-11.9 gives CG = 1500 and CX = 3200, and the
old table had H = 1500 with CG = 3200.

A row is

  [lcT50, vapourPressureTorr, volatilityMgM3, deltaHvapKJmol, bandHours,
   hydrolysisEaKJmol]

deltaHvapKJmol is the latent heat of vaporisation at 25 C (FM 3-11.9 Appendix
G).  hydrolysisEaKJmol is a published hydrolysis activation energy, and it
takes precedence over deltaHvap in the decay kernel:

  GD  64.25  Wu et al. 2021, E3S Web Conf 267:02060,
             doi:10.1051/e3sconf/202126702060 (HCl aqueous, pH 0.90, 20 C).
  HD 108.8   Herriott 1947, J Gen Physiol 30(6):457-464,
             doi:10.1085/jgp.30.6.457.  QUALIFIED: this is the hydrolysis of
             the H.2TDG sulfonium salt over 20 to 100 C, a related species,
             not neat HD.
  GB, VX, CG  0.  No activation energy was found (the search is recorded in
             .omo/research/cbrn-kinetics-ea.md), so the kernel keeps the
             deltaHvap INTERIM slope for them, labelled as an interim and
             not as an activation energy.

persistenceBand is the JP 1-02 persistence class limits in HOURS, as classified
by FM 3-11.9 Table G-6 with its notes:

  nonpersistent (CG, GB, GD)  dissipates and loses its casualty effect in
                              10 to 15 minutes  ->  [10 / 60, 15 / 60]
  persistent (VX, H/HD)       remains a casualty risk beyond 24 hours, to
                              several days or weeks ->  [24, 336]

No point half-life is published for any agent, so the band is the sourced
datum and the decay kernel returns the envelope between its limits.  The 24 h
floor is the JP 1-02 figure.  The 336 h ceiling is the "weeks" reading of the
same JP 1-02 sentence; the phrase is qualitative, so the exact ceiling is
UNSOURCED and is kept as a band limit, never as a point half-life.

AC (hydrogen cyanide, LCt50 2860 mg*min/m3, Table II-19) is in the source but
is not modelled here.

Arguments:
  0: agent name (STRING, "VX"/"GB"/"GD"/"H"/"CG")

Returns [lcT50, vapourPressureTorr, volatilityMgM3, deltaHvapKJmol, bandHours,
         hydrolysisEaKJmol].
*/

params [["_agent", "", [""]]];

// Default: H (distilled mustard), the persistent agent.
private _row = [1000, 0.106, 906, 62.8, [24, 336], 108.8];

private _a = toUpper _agent;

if (_a == "VX") then {
    _row = [15, 8.78e-4, 12.6, 80.3, [24, 336], 0];
} else {
    if (_a == "GB") then {
        _row = [35, 2.48, 18700, 48.5, [10 / 60, 15 / 60], 0];
    } else {
        if (_a == "GD") then {
            _row = [35, 0.401, 3930, 55.2, [10 / 60, 15 / 60], 64.25];
        } else {
            if (_a == "CG") then {
                _row = [1500, 1400, 7460000, 24.8, [10 / 60, 15 / 60], 0];
            };
        };
    };
};

_row
