#include "..\..\script_component.hpp"

/*
Chemical/biological agent surface persistence (hours).

Persistence is the time constant of first-order decay.  The temperature term
is the Clausius-Clapeyron slope of the agent's latent heat of vaporisation
(FM 3-11.9, "Potential Military Chemical/Biological Agents and Compounds",
January 2005, Appendix G), the same quantity the airborne decay kernel uses:

  rate(T) = rate(T_ref) exp( -(deltaHvap / R) (1/T - 1/T_ref) )
  P(T)    = P_ref / rate(T) / rate(T_ref)

with T_ref = 298.15 K (25 C) and R = 8.314462618 J/(mol*K) (CODATA 2018).

deltaHvap is an INPUT.  This kernel cannot resolve an agent, so the caller
(the core environment tick) passes the active agent's value from
aee_weather_fnc_getCbrnAgent.  With no agent the term is 1: no deltaHvap is
published for an unidentified agent, and no generic value exists.

The Q10 rule of thumb that stood here is gone: its decay rate doubled per
10 C.  Its implied Q10 over 15 to 25 C runs 1.42 (CG) to 3.09 (VX) per agent,
so it was 30 percent low for HD and 55 percent low for VX.  The INTERIM basis
is the deltaHvap slope: FM 3-11.9 gives deltaHvap and no hydrolysis activation
energy, so the kinetic term is UNSOURCED as a hydrolysis activation energy
until a published one is found.

REMOVED terms, no published value found (.omo/research/cbrn-kinetics.md):

  - Humidity multiplier (was x0.67 at 100 %RH, x2.0 at 0 %RH).  No published
    "RH to persistence" multiplier exists.  Humidity acts indirectly, through
    the condensed water and its pH, salt and temperature, which set the
    hydrolysis rate; a direct humidity multiplier has no basis.
  - Wind factor (was 1/(1 + 0.05 v)).  Wind is dispersion, not decay, and the
    plume path (fnc_updateCbrnPlume) already models it, so the factor
    double-counted dispersion as persistence loss.

Rain washout is kept: it is a scavenging term of the Gaussian plume, not a
decay-rate factor.

The stored value is the per-tick exponential decay factor with the resulting
time constant.  Stored in QEGVAR(core,cbrnPersistence).

Arguments:
  0: latent heat of vaporisation (NUMBER, J/mol).  0 or absent means no
     temperature term (no active agent)
*/

params [["_deltaHvapJmol", 0, [0]]];

// ─── Inputs ────────────────────────────────────────────────────────────────
private _temp_C  = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _interval = EGVAR(core,updateInterval);

if !(_temp_C isEqualType 0) then { _temp_C = 15; };
if !(_deltaHvapJmol isEqualType 0) then { _deltaHvapJmol = 0; };

// ─── Temperature — per-agent Clausius-Clapeyron (interim: deltaHvap) ───────
// Base persistence lives in compat_acm (ACM loaded) with a 24 h fallback
// when ACM is absent.  The 24 h fallback is UNSOURCED: no source gives a
// generic point base persistence (JP 1-02 gives a band, not a point).
private _basePersistenceH = missionNamespace getVariable [QEGVAR(compat_acm,CBRNBasePersistence), 24];
private _rateMultiplier = 1;
if (_deltaHvapJmol != 0) then {
    private _tempK = (_temp_C + KELVIN_OFFSET) max 1;
    _rateMultiplier = exp (-(_deltaHvapJmol / 8.314462618) * (1 / _tempK - 1 / 298.15));
};
private _persistenceH = _basePersistenceH / _rateMultiplier;

// ─── Rain washout — the scent model's one non-overlapping factor ───────────
// The scent dispersion model (aee_weather) publishes its rain washout factor
// separately.  Rain scavenges the airborne agent, the washout term of the
// Gaussian plume (concentration falls with exp(-lambda x / u); Turner,
// "Workbook of Atmospheric Dispersion Estimates", 2nd ed, CRC, 1994), so it
// shortens persistence.  Only rain is reused.  Temperature is NOT reused: the
// plume path carries the same deltaHvap temperature scaling, so a second
// application would double-count.  The scent ground factor is NOT reused: it
// encodes scent detectability and its sign (snow and frozen ground suppress
// scent) inverts the surface-persistence physics.
// The 0.2-in-rain magnitude is the scent model's own constant
// (fnc_calculateScentDispersion) and has no published basis as a CBRN scavenging
// coefficient.  The read is a soft sibling read by name, defaulting to 1 (no
// washout) when the scent model has not run.
private _scentRainFactor = missionNamespace getVariable ["aee_weather_scentRainFactor", 1];
if !(_scentRainFactor isEqualType 0) then { _scentRainFactor = 1; };
_persistenceH = _persistenceH * _scentRainFactor;

// ─── Decay per tick — exponential decay with the scaled time constant ──────
private _modifier = exp (-(_interval / 3600) / _persistenceH);

missionNamespace setVariable [QEGVAR(core,cbrnPersistence), _modifier];

_modifier
