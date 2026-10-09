# Vanilla Ambient and Animal Sound Inventory, and AEE Wildlife Integration

Committed research for the wildlife ecology plan. Sourcing key for this
dossier: **[CONFIG]** a class or path in a shipped config. **[AUDIO]** decoded
and measured. **[PATH]** folder convention only. **[NONE]** name only. In the
plan's common key, [CONFIG] and [AUDIO] are [S], and [PATH] and [NONE] are
[U]. No recording is given a species unless a shipped config names it. A
byte-identical md5 match to a named recording also settles an identity at [S].
Every UNKNOWN and UNCONFIRMED entry stays marked.

Read-only research (2026-10-06). Ground truth is the shipped Arma 3 config and
PBO contents at `/ext/SteamLibrary/steamapps/common/Arma 3`, extracted with
`/home/matt/bin/extractpbo` and `/home/matt/bin/dewss`. No repository file was
changed.

Purpose: identify what each ambient and animal sound ACTUALLY is, from config
class names, parent classes, name strings, path convention and metadata, not
from the file name alone. Every category that evidence cannot settle is marked
**UNKNOWN** and is not given a species.

Evidence key: **[CONFIG]** class or path in a shipped config. **[AUDIO]**
decoded with dewss and measured. **[PATH]** folder convention only. **[NONE]**
name only, no supporting evidence.

---

## 1. Provenance: where the files live

Two PBOs share the `A3\Sounds_F` namespace. This matters, because the legacy
and the current copies are not always the same recording.

| PBO | `$PBOPREFIX$` | Ship directory | Role |
| --- | --- | --- | --- |
| `sounds_f.pbo` | `a3\sounds_f` | `Addons/sounds_f/a3/sounds_f/` | Legacy raw set, `CfgSounds`, `CfgSFX`, `CfgVehicles` sound wrappers, engine beds |
| `sounds_f_environment.pbo` | `a3\sounds_f\environment` | `Addons/sounds_f_environment/a3/sounds_f/environment/` | Current set: `environment/animals/**`, redesigned engine ambient |
| `animals_f.pbo` | `a3\animals_f` | `Addons/animals_f/a3/animals_f/` | Animal unit classes, seagull/kestrel/swim sounds |
| `animals_f_beta.pbo` | `a3\animals_f_beta` | `Addons/animals_f_beta/a3/animals_f_beta/` | Sheep, goat, dog, chicken unit classes and clips |
| `sounds_f_enoch.pbo` | `a3\sounds_f_enoch` | `Enoch/Addons/sounds_f_enoch/` | Contact/Livonia fauna: deer, wolves, insect set |

AEE uses the **legacy** path `a3\sounds_f\ambient\animals\*.wss`
(`addons/wildlife/data/sound_manifest.sqf`). For owl, bird and scared-animal
files the legacy copies are byte-identical to the canonical
`environment/animals/**` copies (md5 confirmed), so their identity carries
over. The gull does **not** match.

## 2. Config identity anchors

These are the only shipped definitions that attach a name to an animal sound.

| Class | Config path | Name string | Samples | Identity |
| --- | --- | --- | --- | --- |
| `CfgSFX.Owl` | `sounds_f/.../config.cpp:598` | `$STR_A3_CfgSounds_Owl0` | `A3\Sounds_F\environment\animals\birds\owl1..3` | Owl calls |
| `CfgSFX.Birds` | `sounds_f/.../config.cpp:608` | `$STR_A3_CfgSounds_Birds0` | `...\animals\birds\birds1..5` | Generic songbird chorus |
| `CfgSounds.Scared_Animal1..7` | `sounds_f/.../config.cpp:194-226` | none | `A3\Sounds_F\environment\animals\scared_animalN` | Generic animal distress |
| `CfgSFX.StreamSfx` | `sounds_f/.../config.cpp:702` | none | `A3\sounds_f\dummysound` | **Dummy placeholder** |
| `CfgVehicles.Sound_Stream: Sound` | `sounds_f/.../config.cpp:31561` | `$STR_DN_STREAM` | `sound = "StreamSfx"` | Stream editor object, silent payload |
| `CfgNonAiVehicles.SeaGull: Bird` | `animals_f/.../Seagull/config.cpp:41` | - | `singSound = ...\birds\seagul1` | Seagull call |
| `CfgNonAiVehicles.Crowe: SeaGull` | `animals_f/.../Seagull/config.cpp:54` | - | `...\Seagull\Data\crowe` | Crow call |
| `CfgSounds.Sheep_IdleComm` | `animals_f_beta/.../Sheep/config.cpp:456` | `$STR_A3_titles_sheep_communication` | `A3\sounds_f\dummysound` | Sheep comms, dummy payload |

There is **no** `CfgSFX` or `CfgSounds` class for hen, dog, chicken_grill, or
the raw ambient birds. Those files are only ever named as file paths, never as
a class target in any extracted config. `sarance1..4` is the case the name
alone cannot settle: it is byte-identical by md5 to the vanilla cricket set, so
its identity is a cricket and not a config class.

## 3. Sound inventory with identities

`d` is measured duration (seconds), `ch` channels, `sr` sample rate. All
decoded files are 44.1 kHz.

| File (legacy path = what AEE uses) | Config class that names it | Identity | Verdict | d / ch |
| --- | --- | --- | --- | --- |
| `ambient/animals/owl1.wss` | `CfgSFX.Owl` sound0 | Owl | **CONFIRMED owl**, species not pinned | 2.97 / 1 |
| `ambient/animals/owl2.wss` | `CfgSFX.Owl` sound1 | Owl | **CONFIRMED owl** | 2.33 / 1 |
| `ambient/animals/owl3.wss` | `CfgSFX.Owl` sound2 | Owl | **CONFIRMED owl** | 1.40 / 1 |
| `ambient/animals/birds1.wss` | `CfgSFX.Birds` sound0 | Generic day songbird ambience | **CONFIRMED bird chorus**, species not pinned | 2.92 / 1 |
| `ambient/animals/birds2.wss` | `CfgSFX.Birds` sound1 | Generic day songbird ambience | **CONFIRMED bird chorus** | 2.95 / 1 |
| `ambient/animals/birds3.wss` | `CfgSFX.Birds` sound2 | Generic day songbird ambience | **CONFIRMED bird chorus** | 2.22 / 1 |
| `ambient/animals/birds4.wss` | `CfgSFX.Birds` sound3 | Generic day songbird ambience | **CONFIRMED bird chorus** | 1.82 / 1 |
| `ambient/animals/birds5.wss` | `CfgSFX.Birds` sound4 | Generic day songbird ambience | **CONFIRMED bird chorus** | 2.71 / 1 |
| `ambient/animals/scared_animal1..7.wss` | `CfgSounds.Scared_Animal1..7` | Generic animal distress/fear cry | **CONFIRMED distress call**, species not pinned | 6.09 / **2** |
| `ambient/animals/hen1.wss` | **none** | Hen/chicken (name only) | **UNCONFIRMED, probable hen** | 3.78 / 1 |
| `ambient/animals/hen2.wss` | **none** | Hen/chicken | **UNCONFIRMED, probable hen** | 1.93 / 1 |
| `ambient/animals/hen3.wss` | **none** | Hen/chicken | **UNCONFIRMED, probable hen** | 3.83 / 1 |
| `ambient/animals/dog1.wss` | **none** | Dog (name only) | **UNCONFIRMED, probable dog** | 2.79 / 1 |
| `ambient/animals/dog2..4.wss` | **none** | Dog | **UNCONFIRMED, probable dog** | 2.08 / 4.79 / 5.45, 1 ch |
| `ambient/animals/sarance1..4.wss` | **none** | Cricket/grasshopper stridulation (Orthoptera) | **CONFIRMED cricket by md5.** sarance1..4 are byte-identical (md5) to `environment/animals/insect/cricket1..4.wss`. The species is not pinned below the order. | 3.40 / 1 |
| `ambient/animals/chicken_grill_1..2.wss` | **none** | Not identifiable | **UNKNOWN.** The name reads as a recording/asset label, not an animal. | 5.97 / 1 |
| `ambient/animals/Seagul_1.wss` | **none** (config gull is `...\birds\seagul1`, different md5) | Gull (name only) | **UNCONFIRMED gull; NOT the seagull unit call** | 2.17 / 1 |
| `animals_f_beta/.../Sheep/Data/sound/sheep1..5.wss` | **none** (`Sheep_IdleComm` is a dummy) | Sheep (name + path convention) | **UNCONFIRMED, probable sheep** | 2.85 / 0.92 / 0.98 / 1.16 / 1.12, 1 ch |
| `ambient/basics/night_insects_birds_*` | engine beds | Night insects + birds | **CONFIRMED content** (real audio, 668 KB+) | 1+ ch |
| `ambient/basics/day_insects_birds_winds1.wss` | engine beds | Day insects + birds + wind | **CONFIRMED content** (996 KB) | 1+ ch |
| `sounds_f\dummysound.wss` | many | BI placeholder | **CONFIRMED placeholder** | 17.6 KB |

Confirmed non-AEE vanilla fauna (available, unused by AEE):

| File | Config anchor | Identity |
| --- | --- | --- |
| `sounds_f_enoch/.../Fauna/Animals/Deer_Call_01..11.wss` | `Deercall_Forest_Night_SoundSet` + `Deercall_Forest_Night_SoundShader` (`sounds_f_enoch/config.cpp:5036`, `:7935`) | Deer (Contact/Livonia) |
| `sounds_f_enoch/.../Fauna/Animals/Wolves_01..06.wss` | `Wolves_Night_SoundSet` + `Wolves_Night_SoundShader` (`:5048`, `:7941`) | Wolves |
| `sounds_f_enoch/.../Fauna/Insects/Insect_Night_01..10.wss`, `Insect_Trill_*`, `Insect_Raspy_*`, `Insect_Day_*` | Enoch forest sound sets | Night/day insects |
| `sounds_f_environment/.../animals/Chickens/Chicken_01..20.wss` | `environment/animals/Chickens` | Chicken (current recordings) |
| `sounds_f_environment/.../animals/Goats/Goat_01..18.wss` | `environment/animals/Goats` | Goat |
| `sounds_f_environment/.../insect/cricket1..2.wss`, `insect/redesigned/*` | `environment/animals/insect` | Crickets |

## 4. Playback properties the config carries

### CfgSFX 8-element `soundN[]`
Format per BIKI `CfgSFX`: `{file, soundVolume, soundPitch, maxDistance,
probability, minDelay, midDelay, maxDelay}`.

- `CfgSFX.Owl` and `CfgSFX.Birds` both use
  `{file, 0.31622776, 1.0, 1000, 0.2, 0, 15, 30}`.
  Volume 0.316 (about -10 dB), pitch **fixed 1.0**, **maxDistance 1000 m**,
  probability 0.2, random repeat delay 0 to 15 to 30 s.
- `CfgSFX.StreamSfx` uses `{dummysound, 0.316, 1, 60, 1, 1, 1, 1}`,
  maxDistance 60 m, but the sample is a dummy.

CfgSFX entries are positional by construction (played through a sound source
object). They loop with the min/mid/max delay.

### CfgSounds 3-element `sound[]`
Format `{file, volume, pitch}`. `Scared_Animal1..7` use
`{..., 0.31622776, 1.0}`. CfgSounds are non-positional; AEE overrides this by
loading the same file as a raw path through `playSound3D`.

### `singSound[]` (CfgNonAiVehicles)
Format `{file, volume, pitch, maxDistance}`. SeaGull uses
`{seagul1, 0.8912509, 1, 200}`. maxDistance 200 m, pitch 1.

### What AEE actually passes to the engine

- Raw `.wss` one-shot (`fnc_playOneShot.sqf:50`):
  `playSound3D [_source, objNull, false, ATLToASL _position, _volume, 1,
  _distance, 0, true]`.
  Pitch **fixed 1** (no randomisation), distance **120 m**, offset 0,
  **local true**. The config `sound[]` volume, pitch, probability and
  maxDistance are **bypassed** for a raw file path; only the engine global
  defaults apply.
- CfgSFX bed (`fnc_playAmbientBed.sqf:37`):
  `createSoundSourceLocal [_source, _position, [], 0]`.
  Positional and looping, using the CfgSFX's own params (1000 m for Owl).
  The AEE `_gain` is **not passed** (see mismatch 5).
- Loop: the one-shot path does not loop. It replays a 2-3 s clip on every
  tick, capped at 3 live instances that expire after 3 s (the acoustic niche
  density target; `fnc_playOneShot.sqf:45-50`).
- Constants (`script_component.hpp:7-8`):
  `WILDLIFE_SOUND_INSTANCE_CAP = 3`, `WILDLIFE_SOUND_MAX_DISTANCE = 120`.
  The dossier records both as UNSOURCED modelling choices.

## 5. AEE integration map

Load: `fnc_initWildlife.sqf:23-24` compiles `data/sound_manifest.sqf` into
`QGVAR(manifest)`. Compiled once.

Select context: `fnc_soundBedForContext.sqf:42-71`. Precedence
water > night > biome family (a=tropical, b=arid, d/e=cold, else temperate).
If `vegScore >= 0.5`, append `_forest` (`:67-69`). Returns `[key, gain]`.

Compute gain: take the base gain of the **first** matching manifest row
(`fnc_soundBedForContext.sqf:73-81`), scale by `(1 - disturbance)`, then wind
and rain (`:83-86`), then damp ground (`fnc_wildlifeTick.sqf:152-156`).

Choose the source: `fnc_wildlifeTick.sqf:203-214`. It scans the manifest and
keeps the **first** row whose key equals `_bedKey`:
```
208:  if ((_row select 0) == _bedKey) then {
209:      if (_source == "") then { _source = _row select 1; };
```

Play: `fnc_playAmbientBed.sqf:28-38`. A source that contains a dot is played
as a raw one-shot; a source without a dot is loaded as a CfgSFX bed.

Fauna fear: `fnc_applyAnimalBehaviour.sqf:134-135` hardcodes
`a3\sounds_f\ambient\animals\scared_animal1.wss` for every fleeing animal,
bypassing the manifest entirely.

### Where a species matcher slots in

1. `fnc_soundBedForContext` currently returns one key and one gain. Change it
   (or add a sibling kernel) to return a weighted candidate list.
2. `fnc_wildlifeTick.sqf:205-212` must change from first-match to a
   deterministic weighted pick over all matching rows, so multi-file contexts
   actually vary.
3. Inputs already computed in `fnc_wildlifeTick`: biome (`:41`), night (`:47`),
   near-water (`:51-57`), wind (`:59-60`), rain (`:62-64`), disturbance
   (`:71-76`), vegetation score (`:125-135`). Add temperature
   (`aee_core_currentTemperature`), sun elevation
   (`aee_core_currentSunElevation`), and month from the engine date.
4. `species_table.sqf` drives fauna spawning only. Add a parallel
   species-to-sound-group table (owl, day songbird, night insect, gull, hen,
   dog, sheep, deer, wolf, frog) and join the two on biome.

## 6. Mismatches named

These are the choices that are wrong given what the sounds actually are, or
are unreachable given how the selector works.

1. **Only the first manifest row per context ever plays.**
   `fnc_wildlifeTick.sqf:209`. Every multi-file context collapses to one file:
   water to `Sound_Stream`; night to `Owl`; `day_temperate` to `birds1`;
   `day_cold` to `birds1`; `day_arid` to `birds3`; `day_tropical` to `birds2`;
   every `_forest` context to its first bird; farm to `hen1`; grass to
   `sheep1`; fear to `scared_animal1`. `birds2-5`, `owl1-3`, `hen2-3`,
   `dog1-4`, `sheep2-5` and `scared_animal2-7` never play.
2. **Four context keys are unreachable.** `fnc_soundBedForContext.sqf:42-71`
   returns only `water`, `night`, `day_*`. It never returns `farm`, `coast`,
   `grass` or `fear`. So the manifest hen/dog rows, the gull row, the sheep
   rows and the 7 fear rows are dead entries. The fear sound is only ever the
   hardcoded `scared_animal1` from `fnc_applyAnimalBehaviour.sqf:134`.
3. **The water bed is silent.** The `water` row selects `Sound_Stream`
   (`sound_manifest.sqf:21`). `Sound_Stream` is a `CfgVehicles` wrapper whose
   `sound = "StreamSfx"`, and `StreamSfx` (`config.cpp:702`) points at
   `dummysound`. The water context plays a placeholder, not a stream.
4. **The night bed may not resolve.** The first `night` row is the CfgSFX
   class `Owl`. `createSoundSourceLocal` expects a `CfgVehicles` class. No
   `CfgVehicles` wrapper named `Owl` exists in any extracted config, so this
   needs a runtime check. Either way the raw `owl1-3` rows are shadowed
   (mismatch 1).
5. **The CfgSFX bed ignores the AEE silence model.** `fnc_playAmbientBed.sqf`
   receives `_gain` (`:22`) but the CfgSFX branch (`:30-38`) never uses it.
   Night and water beds therefore do not attenuate with disturbance, wind,
   rain or damp ground. The code also deletes and recreates the source every
   tick (`:33-38`), restarting the CfgSFX and defeating its 0-30 s random
   repeat.
6. **Night insects are not a genuine gap.** The dossier records night insects
   as a FINDING. Vanilla has `ambient/basics/night_insects_*` and Enoch has
   `Insect_Night_01..10` and `Insect_Trill/Raspy`. An insect bed exists and is
   unused.
7. **`grass` plays sheep.** Sheep are domestic livestock, not grassland
   wildlife. This is a setting mismatch (and unreachable anyway).
8. **Biome-specific birds are arbitrary.** `day_arid` uses `birds3` and
   `day_tropical` uses `birds2`, but `birds1-5` are all generic temperate
   songbird chorus with no biome or species marker in config. The biome
   assignment has no supporting evidence.
9. **`hen`/`dog`/`Seagul_1` are orphans.** No config class names them. Using
   them trusts the file name. `chicken_grill_1-2` is genuinely UNKNOWN and must
   not be given a species. `sarance1-4` is no longer unknown: it is
   byte-identical by md5 to the vanilla cricket set, so it is a confirmed
   cricket.
10. **The coastal gull is an unverified recording.** AEE uses
    `ambient/animals/Seagul_1.wss`; the config-confirmed gull call is
    `environment/animals/birds/seagul1` (different md5). AEE's gull is not the
    one the seagull unit uses.
11. **Fear is not species-matched.** Every fleeing animal (goat, rabbit,
    sheep, snake) emits the same generic `scared_animal1` distress cry.

## 7. Source list

- `addons/wildlife/data/sound_manifest.sqf` (AEE, all rows)
- `addons/ambience/functions/fnc_soundBedForContext.sqf`
- `addons/wildlife/functions/fnc_wildlifeTick.sqf`
- `addons/ambience/functions/fnc_playAmbientBed.sqf`
- `addons/ambience/functions/fnc_playOneShot.sqf`
- `addons/wildlife/functions/fnc_applyAnimalBehaviour.sqf`
- `addons/wildlife/functions/fnc_initWildlife.sqf`
- `addons/wildlife/script_component.hpp`
- `sounds_f/a3/sounds_f/config.cpp` (CfgSounds, CfgSFX, CfgVehicles wrappers)
- `sounds_f/a3/sounds_f/$PBOPREFIX$.txt`
- `sounds_f_environment/a3/sounds_f/environment/$PBOPREFIX$.txt`
- `animals_f/a3/animals_f/Seagull/config.cpp`
- `animals_f_beta/a3/animals_f_beta/Sheep/config.cpp`
- `sounds_f_enoch/config.cpp`
- BIKI `CfgSFX`: https://community.bistudio.com/wiki/CfgSFX
- BIKI `playSound3D`: https://community.bistudio.com/wiki/playSound3D
- BIKI `createSoundSource`: https://community.bistudio.com/wiki/createSoundSource
- BIKI `WSS File Format`: https://community.bistudio.com/wiki/WSS_File_Format
