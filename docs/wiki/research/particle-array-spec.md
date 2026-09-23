# ParticleArray deep reference (issue #157)

The complete verified spec for the Arma 3 particle emitter: the 24-element
ParticleArray, the companion `setParticleRandom` / `setParticleCircle` /
`setDropInterval` calls, the rain-trail technique, and the performance
notes. It is the reference the shipped particle pipeline is written
against (issues #149, #150, #151), and the surface #128 (per-component
anchors) and #152 (eye-space droplets) read.

The command surface was mapped in #146. This document completes it for
particles.

## How to read this

- **Index**: the ParticleArray position, 0-based. Verified against the
  array the shipped emitter builds
  (`addons/fx/functions/particle/fnc_particlePipelineEmit.sqf`).
- **Used by AEE**: does the shipped pipeline set this element, and from
  what. A blank means the element keeps the array default.
- **Spec**: the engine behaviour, from the BI wiki ParticleArray page
  (archived).

The array has **22 live elements (indices 0-21)**. The shipped emitter
builds exactly these, in order:

| Index | Name | Type | Spec | Used by AEE |
|---|---|---|---|---|
| 0 | shapeName | Render | `[p3dPath, nth, index, count, loop]` - the model, which frame of its animation, and the frame range | `Universal.p3d, 16, 12, 9, 0` (constant) |
| 1 | animationName | - | **Obsolete.** "will throw 'Skeletal animation not supported for particles' RPT error if not empty" | `""` (must stay empty) |
| 2 | type | Render | `"Billboard"` or `"SpaceObject"` | `"Billboard"` |
| 3 | timerPeriod | Script | seconds between `onTimer` calls | `1` |
| 4 | lifetime | Physical | seconds the particle lives | the config row's `lifetime` |
| 5 | position | Physical | a Position, **or a String naming an object selection** | `[0, 0, 0]` (the source is placed by `createVehicleLocal` and `attachTo`) |
| 6 | moveVelocity | Physical | initial velocity | wind x `slant`, wind y `slant`, config `fall` |
| 7 | rotationVelocity | Physical | rotations per second | `0` |
| 8 | weight | Physical | "weight of the particle (kg)" | `fnc_particleState` / `fnc_kickupParams` |
| 9 | volume | Physical | "volume of the particle in m^3" | `fnc_particleState` / `fnc_kickupParams` |
| 10 | rubbing | Physical | "How particles are affected by wind (**include downwash by helicopters**)" | `fnc_particleState` / `fnc_kickupParams` |
| 11 | size | Render | "particle size along its lifetime, in meters" | the config row's `size` array (start, end) |
| 12 | color | Render | RGBA over lifetime | `[_rgb+[0], _rgb+[_alpha], _rgb+[0]]` - fade in, hold, fade out |
| 13 | animationPhase | Render | frame play speed | `[0.5]` |
| 14 | randomDirectionPeriod | Random | seconds between random direction changes | `1` |
| 15 | randomDirectionIntensity | Random | magnitude of the random velocity change | `0` (randomness lives in `setParticleRandom`) |
| 16 | onTimer | Script | `_this` = particle position, PositionAGL | `""` (see the hooks note) |
| 17 | beforeDestroy | Script | `_this` = particle position AGL | `""` (see the hooks note) |
| 18 | object | Physical | "if not objNull, the particle source is attached to the object" | the request's `emitter` |
| 19 | angle | Physical | starting angle in radians (pi = 180 degrees) | the local wind bearing |
| 20 | onSurface | Physical | "Bounce the particles when they hit the surface if true. If circleRadius > 0, place on (water) surface" | `fnc_particleState` element 5, or the config row |
| 21 | bounceOnSurface | Physical | "coef of bounce in collision with ground, 0..1, **-1 to disable collision**" | `fnc_particleState` / `fnc_kickupParams` |

Element 22 (`emissiveColor`) and 23 (`vectorDir`) are documented by the
engine but the shipped emitter does not append them; the array is
truncated at index 21, and the engine defaults the rest.

## The companion calls

`setParticleParams` is one of four calls that configure a source. The
pipeline uses all four.

| Call | Purpose | AEE value |
|---|---|---|
| `setParticleParams` | the ParticleArray above | built in `fnc_particlePipelineEmit` |
| `setParticleRandom` | the per-particle random spread: lifetime, position, velocity, rotation, size, colour, angle | lifetime x0.3, position up to circle/2, colour all zero, wind bearing |
| `setParticleCircle` | a circular emitter: `[radius, [velX, velY, velZ]]` | the request radius or the config `circle` |
| `setDropInterval` | seconds between emissions; rate = 1/interval | `1 / (rate max 0.01)` |

The source itself is `"#particlesource" createVehicleLocal pos`, then
`attachTo` the emitter when the config row says `attach`.

## New findings for the open issues

1. **`position` accepts a selection-name STRING.** The particle source can
   anchor to a named selection, so a source can emit from a vehicle's
   `wheel_1` component rather than its origin. This is the ADR-001 anchor
   mechanism applied to particles, and it is the native input for #128
   (per-component effects). The shipped emitter does not use it yet: it
   places the source at `[0, 0, 0]` and attaches to the emitter object.
2. **`rubbing` includes helicopter downwash.** The rotor-wash coupling is
   native to the engine, so #150's wind coupling can carry rotor downwash
   from the lift model without a new mechanism.
3. **`onTimer` and `beforeDestroy` give per-particle POSITION** (`_this` =
   PositionAGL). This is the per-particle hook. The shipped emitter leaves
   both empty; #152's eye-space droplets and #150's per-particle state
   coupling are the callers that would use it.
4. **`object` is bounded by object view distance.** An attached source
   stops generating particles past the object view distance, so a source's
   reach is bounded by the render distance. This is the performance link
   to #97 and #139.
5. **`emissiveColor` needs values about 100x.** It is the "works as
   lighting" parameter; a value in 0..1 has no visible effect.
6. **`bounceOnSurface` carries a documented performance cost**: "should be
   used soberly as it has a significant impact on performance." #150
   drives it from ground state, so the #149 allocator must budget it. The
   config rows already carry a `particles` estimate for this.

## Rain trails, the technique

Rain trails are not a separate feature. They are the size-over-lifetime
array plus a wind-coupled velocity, and the engine stretches the billboard
between the two sizes:

```sqf
// size: 0.3 m at birth, 3 m at death -> a streak, not a dot
["...", "", "Billboard", 1, lifetime, [0,0,0], moveVelocity, 0,
 _weight, _volume, _rubbing, [0.3, 3], /* ... */]
```

The velocity comes from the local wind field, so the streak slants with
the wind. This is what #151's rain and the hurricane composite use.

## Test vectors

- `position = "wheel_1"`: the source emits from that selection, not the
  origin. The #128 anchor test.
- `bounceOnSurface 0.6` against `-1`: measure the frame-time delta. The
  documented cost, and the #149 allocator's budget input.
- size `[0.3, 3]` plus a wind-slanted `moveVelocity`: visible streaks.
- `onTimer` logging `_this`: prints the per-particle AGL position, the
  debug tool for the #152 fix.

## Sources

- BI wiki, ParticleArray page (archived 2025-03-20).
- BI wiki, `drop` command page (archived).
- `addons/fx/functions/particle/fnc_particlePipelineEmit.sqf` - the
  shipped array, the ground truth for the index mapping above.
- #146 (command surface 3), #149, #150, #151.
