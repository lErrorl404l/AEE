# AI and Wildlife Operator QA

This checklist holds the operator-only rows for the `aee_ai` and
`aee_wildlife` layer. Each row gives the exact steps, the RPT path and the
expected observation. No row is verified in this work. A headless run cannot
confirm a visual result or an audible result.

The RPT path is the report file of the active Arma 3 profile. On Windows the
default is `%LOCALAPPDATA%\Arma 3\<profile>.rpt`. On Linux it is
`~/.local/share/Arma 3/<profile>.rpt`. The `-profiles=` launch option moves
the root. Read the newest `.rpt` after each run.

## Single player

Steps. Start a local mission with one player. Turn on the `AEE Debug > AI` and
`AEE Debug > Wildlife` switches. Stand in one place for 60 s.

RPT path. The active profile `.rpt`.

Expected. One `[AEE][wildlife][INFO] wildlife state |` line, then
`[AEE][wildlife][DEBUG]` lines each tick. The `fauna=` value stays at or below
16. The `sound=` value stays at or below 8. No script error line.

## JIP

Steps. Start a local server with one player. Join a second player mid mission.
Make the second player walk 200 m.

RPT path. The second machine's active profile `.rpt`.

Expected. The state line starts at INFO on the joining machine. The local
fauna and sound counts fill from zero. No script error line.

## Respawn

Steps. Start a local mission. Note the state line. Kill the player and
respawn.

RPT path. The active profile `.rpt`.

Expected. The state line resumes after the respawn. The bed is recreated. No
orphaned sound source. No script error line.

## Death

Steps. Start a local mission. Kill the player and stay on the death camera
for 60 s.

RPT path. The active profile `.rpt`.

Expected. The audible output stops. No new spook. The state line reports the
empty anchor. No script error line.

## Alt-tab

Steps. Start a local mission. Alt-tab away for 60 s. Return to the game.

RPT path. The active profile `.rpt`.

Expected. The ppEffect and the bed re-create. The state line resumes. No
script error line.

## Two-client parity

Steps. Start two real clients. Stand both at one grid. Compare the species
mix and the bed context key.

RPT path. Both machines' active profile `.rpt`.

Expected. The species mix and the context key match. The individual animal
objects differ. This row needs two real clients.

## Audible bed and spook

Steps. Listen near water, in forest and at night. Sneak past the listener.
Then sprint past the listener. Fire one shot.

RPT path. The active profile `.rpt`.

Expected. The bed matches the context. A quiet approach keeps the call. A
rush damps it. A shot raises a spook wave. This is a listening check only.

## Live fauna

Steps. Stand on grazing ground near water. Watch for five minutes. Let one
animal thirst.

RPT path. The active profile `.rpt`.

Expected. Animals spawn by biome and graze. They move to water and back. They
cull beyond the despawn radius and above the cap. This is a visual check
only.

## Monitor

An operator can run the monitor from the debug console.

```
[] call aee_wildlife_fnc_monitorWildlife;
```

It prints the state line and the two tick costs. It is a dry run.

## Honest limits

- Two real clients are needed for the parity row. A headless run cannot check
  it.
- The self-hosted runner is operator-only. It holds the nightly job and the
  weekly soak. Its registration and its server install are operator tasks.
- A headless run cannot claim the visual result or the audible result. Those
  rows stay operator-only.
- No row in this file is verified in this work.

## Rows not covered

The plan edge matrix also holds a water shoreline, a forest boundary, a biome
extreme, a large time skip and the force hooks. Those run headless in the
edge probe. They are not operator rows.
