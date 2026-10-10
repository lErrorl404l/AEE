# Engine command surface 2: system diagnostics, effects and sound, object manipulation

This is the verified command surface for the second slice of the #144-#147
command-surface series. It records the system and diagnostic commands the
performance work (#97, #139) depends on, the effects and sound commands the
acoustic and FX work depends on (#80, #116, #128), and the object
manipulation commands that place and state an object. It answers issue #145.

The document names a command, its group, its introduction version and the one
caveat that changes how AEE must call it. It does not restate the area
narratives in [engine-commands-and-features.md](engine-commands-and-features.md).
Read that document for the engine systems behind the commands.

## Source and method

- **Source.** The local Arma 3 wiki command DB, acemod/arma3-wiki dist
  **v2.22**. Commands live in `commands/<name>.yml`.
- **Version.** The `since:` block of a page records the introduction version.
  The column-0 `since:` block is the command's own version. A nested,
  indented `since:` block belongs to one alternative syntax or one parameter,
  not to the command. Read the column-0 block. A command that predates the
  field carries no `arma_3` entry, shown here as **n/v** (no version
  recorded).
- **Labels.** **VERIFIED** means the value is read from the local DB page.
  **UNKNOWN** means the local DB does not carry the claim. Nothing here comes
  from memory.

The DB records no ordering field and no per-command index. Any statement
about an order or a count is marked UNKNOWN against this source.

## 1. System and diagnostics (the #97 performance surface)

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `diag_fps` | 0.50 | Diagnostic, Performance Profiling | Returns the average framerate, calculated over the last 16 frames, as a Number. | Render-cost measurement (#97, #139). |
| `diag_tickTime` | 0.50 | Diagnostic, Time | Returns real time in seconds since the start of the game, as a Number. On Windows it uses `timeGetTime`. | The per-function timing base (#97 counter macros). |
| `diag_frameNo` | 0.50 | Diagnostic, Performance Profiling | Returns the number of the frame currently displayed, as a Number. | Frame-delta timing. |
| `diag_activeScripts` | 1.64 | Diagnostic | Returns a 4-element array: the counts of scripts running under `spawn`, `execVM`, `exec` and `execFSM`, in that order. The DB example is `[0,0,0,1]`. | Script-load monitor (#97). |
| `diag_captureSlowFrame` | 1.00 | Diagnostic, Performance Profiling | Takes `[section, threshold, frameSkip, toFile, continuousCounter]` and returns Nothing. Captures a frame that exceeds the threshold. See the spec below. | The server-side profiler (#97). |
| `diag_log` | 0.50 | Diagnostic | Dumps the argument value to the report file. Each call writes a new line. | Output surface (#97). |

### diag_captureSlowFrame, the verified spec

The command takes up to five parameters. The DB gives a `since` for three of
them, and none for `section` or `threshold`.

| Parameter | Optional | Default | Since | Verified meaning |
|---|---|---|---|---|
| `section` | no | - | n/v | The profiling selection. The DB says the names come from expanding the profiling tree. |
| `threshold` | no | - | n/v | The value to compare against, in seconds, or a string with a unit. |
| `frameSkip` | yes | 0 | 1.18 | The number of frames to ignore before measuring. |
| `toFile` | yes | false | 2.20 | If true, do not open the UI, write straight to a file. Logging to file also writes a `.trace` file for chrome://tracing. If false it can still force to file when there is no UI, as on a server or a headless client. |
| `continuousCounter` | yes | 0 | 2.20 | Captures N slow frames. 0 or 1 captures one frame only. Do not set it negative. It aborts on a later `diag_captureFrame` or `diag_captureSlowFrame`. |

The DB examples are the evidence for the threshold forms:

```
diag_captureSlowFrame ["total", 0.003]
diag_captureSlowFrame ["total", "0.003s"]
diag_captureSlowFrame ["total", "3ms"]
diag_captureSlowFrame ["total", "333fps"]
diag_captureSlowFrame ["memAl", 0.0001, 30]
diag_captureSlowFrame ["total", 0, 0, false, 3]  // opens the capture UI three times
```

**The threshold string form is VERIFIED** by the examples above: a number in
seconds, or a string with the unit `s`, `ms` or `fps`.

**UNKNOWN against the local DB.** The issue lists the `section` selection
names as `Render`, `Main Thread`, `Visualize`, `Mjob`, `bgD3D`, `total`,
`sLoop`, `cLoop`, `memAl`, `visul`. The DB page carries no such list. Only
`total` and `memAl` appear, in the examples. The claim that `sLoop` is the
dedicated-server loop and `cLoop` is the headless-client loop is not on the
page.

**UNKNOWN against the local DB.** The issue states an inverted rule for the
`fps` unit: the capture fires when the section duration is *longer* than the
threshold, except for `fps`, where it fires when the value is *lower*. The DB
page says only that the dialog opens "if current frame exceeds set threshold
in seconds". It carries no inverted-`fps` rule. The `["total", "333fps"]`
example is present, but its comparison direction is not stated.

**UNKNOWN against the local DB.** The issue states that the string threshold
form arrived "since 2.20". The `threshold` parameter carries no `since` on the
page. Only `toFile` and `continuousCounter` are marked 2.20.

## 2. Effects and sound (the FX surface)

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `drop` | 0.50 | Particles | Creates a particle effect from a ParticleArray. It makes smoke, fire and similar effects. The particles are single polygons that always face the player. They can change position, size and direction, take different weights, and depend on the wind. The DB return type is Unknown. | Particle effects. |
| `say3D` | 0.50 | Sounds | `object say3D [sound, ...]` plays a `CfgSounds` class on one object. Returns the sound source as an Object, or a NetObject when the `isGlobal` option is used. See the caveats below. | Positional sound (#80 acoustic). |
| `playSound` | 0.50 | Sounds | Plays a sound from `CfgSounds`, defined in `missionConfigFile`, `configFile` or `campaignConfigFile`. The form `playSound soundName` returns the speaker object, which is Nothing before 2.00. The form `[soundName, isSpeech, offset]` is also present. | `CfgSounds` playback. |
| `setRandomLip` | 0.50 | Object Manipulation | `unit setRandomLip bool` enables or disables the random lip. When enabled, the unit moves its lips continuously as if talking. | Face animation (NPC). |
| `attachTo` | 0.50 | Object Manipulation | `object1 attachTo [object2, offset, memPoint, followBoneRotation]`. Attaches one object to another. The offset applies to the object centre, or to the memory point when one is given. | Anchor-based attachment (ADR-001). |
| `createVehicle` | 0.50 | Object Manipulation | Creates an empty object of the given class name. See the randomization caveat below. | Dynamic object creation (#116 scalar-field emitters). |

**The `say3D` caveats (VERIFIED).** An object can say only one sound at a
time. Consecutive calls queue, and the next sound starts when the previous
one ends. The sounds are not synchronised for JIP players. To stop a sound,
delete the returned sound source with `deleteVehicle`, or kill it with
`setDamage`. Use it for short-range, short sounds with the speed-of-sound
simulation off. Since 2.00 the sound source is returned and can be deleted
directly. When the `isGlobal` option is used, a null NetObject is returned, so
destroy the `from` object instead.

**The `attachTo` memory-point rule (VERIFIED).** The offset applies to the
object centre unless a memory point is given, in which case the offset applies
to the memory point position. With no offset, the current offset between the
two objects is used. All direction commands on an attached object are
relative to the reference object, in model space. The `followBoneRotation`
parameter is since 2.2. This is the ADR-001 memory-point mechanism for placing
effects on vehicle components (#128).

**The `createVehicle` randomization rule (VERIFIED).** To avoid vehicle
randomization, set the `BIS_enableRandomization` variable to false immediately
after creating the object, in an unscheduled environment.

**UNKNOWN against the local DB.** The issue states that `drop` returns an
Object since 2.20. The DB page records the return type as Unknown and carries
no such note.

## 3. Object manipulation (position and state)

| Command | Since | Group | Verified spec | AEE use |
|---|---|---|---|---|
| `setDir` | 0.50 | Object Manipulation | Sets the object heading in degrees clockwise from north. See the caveats below. | Placement ordering. |
| `setPosASL` | 0.50 | Positions | Sets the object position above sea level. The position must be in PositionASL format. | Exact-position placement. |
| `createVehicleLocal` | 0.50 | Object Manipulation | Creates an object of the given type. The object is not transferred over the network. Its `netId` in multiplayer is "0:0". Disable it with `CfgDisabledCommands`. The alternative syntax with `markers`, `placement` and `special` is since 2.14. | Local-only dynamic objects. |

**The `setDir` caveats (VERIFIED).** The command resets the object's velocity
and its `vectorUp`. Its effect is global, but the argument is local. Setting
the direction *after* the position can lead to strange behaviour, as the DB
notes. On a mine the effect is local, so broadcast the change through a
position modification. When a group is attached, its leader is used.

## 4. Corrections against issue #145

No command name in the issue is absent from the DB. Every command named in
the issue exists. The corrections are in the version and capability claims:

1. **`diag_activeScripts` is since 1.64**, not 0.50. It is the only command
   in section 1 that does not date to 0.50.
2. **`diag_captureSlowFrame` is since 1.00.** Its `frameSkip` is since 1.18,
   and its `toFile` and `continuousCounter` are since 2.20.
3. **`drop` does not return an Object since 2.20** on the DB page. The return
   type is Unknown.

The following issue claims are UNKNOWN against the local DB: the full
`diag_captureSlowFrame` section-name list and the `sLoop`/`cLoop` meaning, the
inverted-`fps` comparison rule, the "since 2.20" version for the string
threshold form, and the `drop` "returns an Object since 2.20" claim.

## Sources

- Command DB: acemod/arma3-wiki dist v2.22. Commands read from
  `commands/<name>.yml`: `diag_fps`, `diag_tickTime`, `diag_frameNo`,
  `diag_activeScripts`, `diag_captureSlowFrame`, `diag_log`, `drop`, `say3D`,
  `playSound`, `setRandomLip`, `attachTo`, `createVehicle`,
  `createVehicleLocal`, `setDir`, `setPosASL`.
- Related AEE records: `docs/adr/ADR-001-engine-anchors.md`,
  [command-surface.md](command-surface.md) (the #144 slice),
  [engine-commands-and-features.md](engine-commands-and-features.md).
