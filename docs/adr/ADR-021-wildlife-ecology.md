# ADR-021: Wildlife ecology - a mind that reads the world, not a looping sound

Status: Accepted

## Context

The wildlife layer began as a client-local ambient bed with a spawn budget,
hunger and thirst, and a spook reaction. It was a sound file and a spawn
count, not an animal that reads the world.

Six gaps remained.

The matcher could not read the air temperature, the true sun elevation in
degrees, or the month. It selected from a biome alone, so dawn, dusk, season
and heat had no effect on which animals were present.

The environment read was flat. The spawn and the tick read a single
vegetation score, and the two reads disagreed: the spawn read a Number and
the tick read a HashMap, so the element-1 divergence was a live defect. No
animal sampled the surface material, the water, the structures or the local
noise around it.

The sound path was a first-match loop, so most manifest rows could never
play. Several context keys were unreachable, the water bed was silent, the
night source named a `CfgSFX` class as a `CfgVehicles` class, the `grass`
key played a sheep, and the fear cry was hardcoded.

The hear gate was a fixed range. A gunshot at 121 m did not exist and a
gunshot at 119 m existed at full strength. The engine `Fired` flag was the
stimulus, not the sound level at the animal.

Calls had no meaning. There was no emit, no receive and no bus, so an alarm
from one animal could not reach another.

The pitch was fixed, and the shot audio was not coupled to the ballistics.

## Decision

### Species rules are a cited data corpus

Real species groups live in `data/wildlife/ecology.json`, each entry
source-graded. A generator writes `addons/wildlife/data/ecology_corpus.sqf`
and `asset_map.sqf`. A validator checks the schema, the grading, that no
media path is third-party, and that no vanilla class or sound is invented.
The matcher reads the corpus. It does not branch species in SQF, and it is
not a hand-set per-map table.

### The matcher reads the real inputs

`getSpeciesMatch` is a pure ordered ladder. It matches the Koppen family,
adds the water and settlement overlays, applies the season rule, the
temperature band, the temporal weight from the true sun elevation in degrees,
and a seeded jitter. `getCallPattern` and `getSeason` give the temporal and
seasonal shape. The Dolbear relation gives the cricket rate.

### The environment is a budgeted neighbourhood grid

`sampleNeighbourhood` walks a local grid and returns the foliage fraction,
the surface votes, the water fraction, the structure fraction and the mean
elevation. It is bounded by an object-query cap and a millisecond budget, and
it re-queues its unsampled cells at the front, so no cell starves.
`environmentSuitability` scores a group against the sample, so a cricket on
concrete and a bird over a treeless apron score low. `habitatBoundary` keeps
an animal in its patch with a rare seeded excursion. `environmentGrid` owns
the bounded, aged per-cell cache.

### Cognition runs over the existing substrate

`wildlifePerceive`, `wildlifeThink` and `ecologyTick` run perceive, think,
act and recover over the `addons/ai` substrate. The tick is bounded by a
count budget and a millisecond budget, and it re-queues its unsolved animals
at the front. The first animal of a call is always processed. The substrate
change is additive: with cognition off the generic substrate drives every
animal exactly as before.

### Calls are typed signals

`callEmit` turns a condition and the perception into a typed call (alarm,
mating, territorial, contact, food) with an urgency. `callReceive` decodes a
heard call against the receiver's relation and state into a response.
`callPublish` and `callSample` own the bounded, decayed heard-call bus, which
mirrors the disturbance field: the same cell key, horizon and cap.

### Sound is a propagated level, not a flag

`acousticSourceDb` gives the source level of a sound event (gunshot,
explosion, grenade, vehicle, aircraft, footstep and the rest).
`acousticLevel` propagates the event with spherical spreading, terrain and
object occlusion, and the air absorption AEE already computes. The
propagated level at the animal is the auditory stimulus. `shotAudio` derives
the muzzle report, the supersonic crack, the near-pass snap and the ricochet
from the projectile's real parameters, reusing the ballistics kernel.
`callPitch` gives the seeded per-call jitter, the Doppler shift and the
species pitch. `emitterPlan` keeps the attached emitters bounded and releases
one on despawn, a radius exit or a key change.

### The sound schedule follows the behaviour

`soundTick` plays species calls on the temporal pattern: birds peak at dawn
and lull mid-day, crickets follow the Dolbear duty cycle, and the amphibian
chorus is rain-gated. The per-emission volume carries the silence model, so
the attenuation the `CfgSFX` bed discarded now applies. The bed is recreated
only on a key change.

### Every constant is graded

The per-constant register is
`docs/wiki/research/wildlife-ecology-constants.md`. Each value is graded
sourced, sourced-literature, derived, or unsourced. Several values are
UNSOURCED and stay UNSOURCED.

## Alternatives rejected

- A hand-set per-map species table. It cannot follow the weather or the time.
- Branching species in SQF. The rules are data and belong in the corpus.
- A fixed hear/don't-hear range. A level is continuous and a flag is not.
- The engine `Fired` flag as the stimulus. It is not the sound at the animal.
- Per-species emitter logic. One generic emitter keeps the cost flat.
- A custom audio file, model or texture. Only shipped vanilla media is used.
- Assigning a species to an unverified recording. `chicken_grill` stays
  UNKNOWN and the name-only recordings stay unconfirmed.
- Inventing a constant. A stated ceiling is honest and an invented value is
  not.

## Consequences and ceiling

- Species identity is capped by the vanilla media. One generic owl bank and
  one generic songbird bank exist, and `chicken_grill` is UNKNOWN. The
  matcher works at the group level and records each gap.
- The deer and wolf calls are Enoch media. They resolve only when the Enoch
  platform is present, and fall back to the base night bed with a gap flag
  otherwise.
- The ecology is a script model over engine agents with the AI FSM disabled.
  The animals are real engine objects, but the behaviour is scripted.
- A headless server has no local player, so the ecology tick is client-only
  and the probe drives the pure kernels instead.
- A headless probe cannot read a pixel or hear a sample. The audible and
  visual result is an operator-only check and is recorded as UNVERIFIED.
- Several constants are UNSOURCED modelling choices and are stated as such
  in the register.
