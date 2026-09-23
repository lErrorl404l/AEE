# Rotor downwash and brownout research

Research for the ground-effect dust model (rotor wash on the ground). The
model is not built yet; this file records what the sources state, so the
implementation is based on physics and real values, never invented ones.

## The phenomenon

A rotor in ground effect drives air down, and the flow turns from vertical
(downwash) to radial (outwash) at the ground. Loose surface material is
lifted into that flow, and a cloud forms that can obscure the pilot's view:
brownout over sand and dust, whiteout over snow.

The physical sequence the literature describes:

1. **Downwash** - the rotor induces a downward velocity field below the
   disc, strongest on the axis and decaying outward.
2. **Impingement and outwash** - at the ground the jet turns radial.  The
   radial sheet carries the highest dynamic pressure near the ground.
3. **Entrainment threshold** - a particle is lifted only when the local
   air velocity exceeds a threshold that depends on the particle size,
   density and the surface moisture.  Below the threshold the bed is
   undisturbed.  This is the key result for a model: brownout is not
   linear in rotor proximity, it switches on.
4. **Splash and bombardment** - a lifted particle strikes the bed and
   ejects others (splash entrainment), so the cloud grows faster than the
   flow alone would suggest.
5. **Cloud transport** - the cloud follows the outwash and then rises in
   the blade-tip vortex, so it surrounds the aircraft rather than staying
   under it.

## Sources

| Source | What it states |
|---|---|
| Wadcock et al., "Rotorcraft Downwash Flow Field Study to Understand the Aerodynamics of Helicopter Brownout", NASA AHS 2008, `rotorcraft.arc.nasa.gov/Publications/files/Wadcock_AHS2008.pdf`; full text at `archive.org/details/NASA_NTRS_Archive_20080046973` | Brownout is dust entrained in the downwash while in ground effect. Divides brownout into three processes: helicopter downwash, particle entrainment, visual obscuration. Full-scale UH-60 tuft test validating a Navier-Stokes CFD; EH-101 comparison. Low disk loading gives lower outwash velocity than high disk loading. |
| "Brownout Simulations of Model-Rotors In Ground Effect", MATEC/University of Glasgow, `eprints.gla.ac.uk/217841` | Time-averaged outflow velocities compared with experiment; the flow turns from downwash to radial outwash at the ground |
| Phillips and Brown, "The Flow Physics of Helicopter Brownout" (Vorticity Transport Model) | Entrainment is activated only when the local airflow exceeds a threshold velocity; the cloud is sensitive to rotor wake structure |
| "Novel approach to helicopter brownout based on vortex and discrete element method", Aerospace Science and Technology, `S0260958...211003497` | A particle entrainment model including fluid threshold velocity, saltation and particle flux rate, coupled to a transport model |
| Bagnold, R.A. 1936/1941, via `en.wikipedia.org/wiki/Bagnold_formula` | The threshold and transport relations (below) |
| Greeley and Iversen 1985, "Wind as a Geological Process", Cambridge University Press | The particle threshold in a rotor flow (the Greeley-Iversen expression); Bagnold's benchmark formula |
| Shao and Raupach; Balme et al. (via the brownout literature) | Modern corrections to the threshold friction velocity model for moisture and roughness |

## The formulas

### Bagnold threshold friction velocity

Bagnold's threshold is the shear velocity at which a grain of a given
size begins to move, from Bagnold (1936, 1941) as restated by Greeley and
Iversen (1985):

```
u*t = A * sqrt( ((rho_s - rho_a) / rho_a) * g * d )
```

  u*t    threshold friction velocity, m/s
  A      dimensionless coefficient: 0.1 for the FLUID threshold (the wind
         alone starts the grain), 0.082 for the IMPACT threshold (the
         grain is kept moving by saltating impacts).  The ratio is 0.82.
  rho_s  particle density, kg/m3 (quartz sand ~2650)
  rho_a  air density, kg/m3 (AEE computes this)
  g      local gravitational acceleration, m/s2
  d      grain diameter, m

Because AEE holds `rho_a` and `g`, the threshold is computable for any
atmosphere and any gravity: thin air lowers it, which is why the same
rotor lifts dust more readily at altitude.

### Bagnold transport (mass flux)

The mass flux across a unit width once saltation is under way:

```
q = C * (rho_a / g) * sqrt(d / D) * u*^3
```

  C      dimensionless, order unity, depends on sorting
  D      the reference grain size of Bagnold's experiments, 250e-6 m
  u*     friction velocity

Transport goes as the CUBE of the friction velocity, so the visible plume
grows very steeply once the threshold is crossed.  Valid in dry
conditions; moisture is not included (the literature corrects it).

### Induced velocity (momentum theory)

The rotor induces a downward velocity; in hover:

```
v_i = sqrt( T / (2 * rho_a * A_disc) )
```

  T        rotor thrust, N
  A_disc   rotor disc area, m2

This is the v_i AEE already uses for helicopter lift.  The downwash
velocity at the disc is v_i; at the ground the flow turns radial and the
outwash velocity is of the same order.  In ground effect the induced
velocity falls as the rotor approaches the ground, and the outwash rises.

## What the model needs

Stated as quantities, so each is either computed from AEE state or marked
as needing research:

1. **Downwash velocity below the rotor.**  Momentum theory gives the
   induced velocity: `v_i = sqrt(T / (2 * rho * A))` for hover, where `T`
   is thrust, `rho` air density and `A` the disc area.  AEE already holds
   `rho` (`fnc_calculateAirDensity`) and rotor lift
   (`fnc_calculateHelicopterLift`), so the induced velocity is derivable.
   In ground effect the induced velocity falls and the outwash rises.
2. **The threshold velocity.**  Needs a citable value per material.  The
   literature states the mechanism; the numbers must come from a source
   before they enter the model.
3. **Outwash radial profile.**  The ground-jet velocity against radius
   from the rotor axis.  The Glasgow paper compares measured profiles.
4. **Entrainment rate above threshold.**  Particle flux from the bed,
   with the splash term.
5. **Cloud rise and transport.**  Blade-tip vortex roll-up, hence the
   cloud surrounds the aircraft.

## Open questions to resolve from sources

- The threshold velocity for sand, soil and snow, in m/s.
- The outwash velocity profile (normalised to induced velocity against
  radius / rotor radius).
- Whether a simple model can be defensible without full CFD, and what it
  must state as a limitation.
