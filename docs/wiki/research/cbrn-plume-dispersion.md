# CBRN agent plume dispersion

AEE models the wind-borne dispersion of a chemical agent release with the
Gaussian plume and puff equations. The model produces a ground-level
concentration at a receptor and an inhaled dose, and it drives the existing
CBRN protective-equipment model. See ADR-038 for the decision.

The implementation lives in `addons/weather/functions/dispersion/`.

## Equations

### Steady Gaussian plume

Turner, *Workbook of Atmospheric Dispersion Estimates*, EPA AP-26 (1970),
eq. 3.3 (ground reflection):

```
C(x,y,z) = Q / (2 pi U sigma_y sigma_z)
         * exp( -y^2 / (2 sigma_y^2) )
         * [ exp( -(z-H)^2 / (2 sigma_z^2) ) + exp( -(z+H)^2 / (2 sigma_z^2) ) ]
```

At ground level on the centreline (`y = 0`, `z = 0`) the bracket is 2 and
`C = Q / (pi U sigma_y sigma_z)`. For a ground source (`H = 0`) this is the
simple `C = Q / (pi U sigma_y sigma_z)` form. `Q` is the emission rate
(mg/s), `U` the wind speed (m/s), `H` the effective release height (m).

### Gaussian puff

Turner AP-26, the instantaneous solution:

```
C = M / ( (2 pi)^1.5 sigma_x sigma_y sigma_z )
    * exp( -(x-xc)^2 / (2 sigma_x^2) )
    * exp( -(y-yc)^2 / (2 sigma_y^2) )
```

`M` is the released mass (mg). The puff centre is advected with the wind.

### Briggs dispersion coefficients (rural, x in m)

Briggs, *Diffusion Estimation for Small Emissions*, ATDL (1973):

| Class | sigma_y | sigma_z |
|---|---|---|
| A | 0.22 x (1+0.0001 x)^-0.5 | 0.20 x |
| B | 0.16 x (1+0.0001 x)^-0.5 | 0.12 x |
| C | 0.11 x (1+0.0001 x)^-0.5 | 0.08 x (1+0.0002 x)^-0.5 |
| D | 0.08 x (1+0.0001 x)^-0.5 | 0.06 x (1+0.0015 x)^-0.5 |
| E | 0.06 x (1+0.0001 x)^-0.5 | 0.03 x (1+0.0003 x)^-1 |
| F | 0.04 x (1+0.0001 x)^-0.5 | 0.016 x (1+0.0003 x)^-1 |

Urban surfaces double `sigma_y`.

### Pasquill stability class

Pasquill (1961), via Turner AP-26 Table 1. The class is the day insolation
category or the night cloud cover, crossed with the 10 m wind speed, or the
measured vertical temperature gradient `dT/dz` (C/100 m) when one is given.

### Agent parameters (FM 3-11.9, January 2005)

FM 3-11.9 / MCRP 3-37.1B / NTRP 3-11.32 / AFTTP(I) 3-2.55, *Potential Military
Chemical/Biological Agents and Compounds*, January 2005: the Chapter II agent
tables (II-3 CG, II-9 GB, II-11 GD, II-15 VX, II-25 HD) and the Appendix G
physical-property tables.

| Agent | LCt50 (mg\*min/m3) | VP @25 C (torr) | Volatility @25 C (mg/m3) | dHvap (kJ/mol) | Persistence band |
|---|---|---|---|---|---|
| VX | 15 | 8.78e-4 | 12.6 | 80.3 | persistent: 24 h to 336 h |
| GB | 35 | 2.48 | 1.87e4 | 48.5 | nonpersistent: 10 min to 15 min |
| GD | 35 | 0.401 | 3.93e3 | 55.2 | nonpersistent: 10 min to 15 min |
| H/HD | 1000 | 0.106 | 906 | 62.8 | persistent: 24 h to 336 h |
| CG | 1500 | 1400 | 7.46e6 | 24.8 | nonpersistent: 10 min to 15 min |

The earlier citation (`FM 3-11, Chemical Operations (2003), Table 4-1`) named
no located document: FM 3-11 (2003) is *Multiservice Tactics, Techniques, and
Procedures for NBC Defense Operations* and FM 3-11 (2011) carries no agent
physical-property table. The values the table carried before are the older,
unverified FM 3-9-era set.

### Decay and washout

No point half-life is published for any agent. The persistence band is the
sourced datum (JP 1-02 / FM 3-11.9 Table G-6), so the kernel returns the
envelope between the band limits:

```
tau_lo = t_lo / ln 2   ->  cFast = C0 exp(-t / tau_lo)   (fast edge)
tau_hi = t_hi / ln 2   ->  cSlow = C0 exp(-t / tau_hi)   (slow edge)
```

The band is scaled to the air temperature by the Clausius-Clapeyron slope of
the latent heat of vaporisation, `t_half(T) = t_half(298.15 K) exp((dHvap / R)
(1/T - 1/298.15))`, with `R = 8.314462618 J/(mol*K)`. The implied Q10 over 15
to 25 C runs 1.42 (CG) to 3.09 (VX) per agent. Rain washout uses
`Lambda = 8.4e-5 I^0.79` (`I` in mm/h). Dry deposition flux is `vd * C`, with
`vd ~ 0.002 m/s` for a vapour.

## Published state

The driver publishes, on the `aee_core` namespace:

| Variable | Meaning |
|---|---|
| `cbrnPlumeConcentration` | ground-level concentration (mg/m3) |
| `cbrnPlumeDose` | accumulated inhalation dose (mg*min/m3) |
| `cbrnPlumeLethal` | dose has reached 1.0 x LCt50 |
| `cbrnPlumeIncapacitated` | dose has reached 0.1 x LCt50 |
| `cbrnStabilityClass` | the current Pasquill class |
| `cbrnDepositionFlux` | dry deposition flux (mg/m2/s) |

## Opting in

The model is off by default. Enable `aee_weather_CbrnPlumeEnabled`, then
start a release:

```sqf
[getPosASL _source, "VX", 100000, 0, false] call aee_weather_fnc_startCbrnRelease;
```

Arguments are position, agent, strength (steady mg/s or burst mass mg),
effective height (m) and burst flag. Fewer than three position elements
stops the release.

## UNSOURCED values

- The numeric solar-flux thresholds (700 and 350 W/m2) are a proxy for the
  standard's qualitative strong/moderate/slight insolation bands.
- The engine `rain` level to mm/h mapping (`x 50`) is a heavy-rain proxy;
  the engine exposes no mm/h rain rate.
