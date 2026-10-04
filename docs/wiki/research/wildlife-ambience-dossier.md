# Wildlife Ambience - Sound Inventory and Findings

This dossier records the vanilla ambient-sound inventory for the wildlife
layer, the finding list, and the sources. The layer reuses vanilla media
only. It never fetches, licenses or generates an audio asset. A context that
vanilla cannot supply becomes a FINDING, never a fetch.

The machine-readable table is
`addons/wildlife/data/sound_manifest.sqf`. Each row is
`[contextKey, vanillaPathOrCfgSFXClass, maxDistance, baseGain]`. A row with a
dot in the second value is a raw vanilla `.wss` file loaded with `playSound3D`
and the `local` argument true. A row without a dot is a vanilla `CfgSFX` class
loaded with `createSoundSource` as a looping positional bed.

Sourcing key: **[P]** primary document read. **[P-W]** primary via Wayback.
**[PROJECT]** already in this repository with its own citation.
**[UNSOURCED]** no primary obtained.

## The manifest

| contextKey | Source | Type | maxDistance m | baseGain | Source state |
| --- | --- | --- | --- | --- | --- |
| water | Sound_Stream | CfgSFX | 120 | 0.60 | [P] BIKI createSoundSource |
| night | Owl | CfgSFX | 120 | 0.45 | [P] BIKI CfgSFX |
| night | owl1.wss, owl2.wss, owl3.wss | raw | 120 | 0.70 | [P] BIKI Sound Files |
| day_temperate | birds1.wss to birds5.wss | raw | 120 | 0.70 | [P] BIKI Sound Files |
| day_cold | birds1.wss, birds4.wss | raw | 120 | 0.55 | [P] BIKI Sound Files |
| day_arid | birds3.wss, birds5.wss | raw | 120 | 0.45 | [P] BIKI Sound Files |
| day_tropical | birds2.wss, birds3.wss | raw | 120 | 0.75 | [P] BIKI Sound Files |
| farm | hen1.wss, hen2.wss, hen3.wss | raw | 120 | 0.55 | [P] BIKI Sound Files |
| farm | dog1.wss to dog4.wss | raw | 120 | 0.60 | [P] BIKI Sound Files |
| coast | seagul_1.wss | raw | 120 | 0.60 | [P] BIKI Sound Files |
| grass | sheep1.wss to sheep5.wss | raw | 120 | 0.55 | [P] BIKI Sound Files |
| fear | scared_animal1.wss to scared_animal7.wss | raw | 120 | 0.90 | [P] BIKI Sound Files |

All raw paths are under `a3\sounds_f\ambient\animals\`, except the sheep set
under `a3\animals_f_beta\sheep\data\sound\`.

## Requested-context coverage

The plan requests eleven contexts. A context with no confirmed vanilla source
is a finding.

| Requested context | Status |
| --- | --- |
| Day birds | Covered, `day_*` rows |
| Night owls | Covered, `night` rows |
| Night insects | FINDING, no confirmed vanilla insect sound |
| Farm bird | Covered, `farm` hen rows |
| Dog | Covered, `farm` dog rows |
| Gull | Covered, `coast` row |
| Sheep | Covered, `grass` rows |
| Deer | FINDING, exact Enoch subfolder not pinned |
| Wolves | FINDING, exact Enoch subfolder not pinned |
| Water | Covered, `water` CfgSFX row |
| Flight and fear | Covered, `fear` rows |

## FINDING list

- FINDING: no owl unit class in vanilla. The owl exists as an ambient sound
  only. Source, BIKI Arma 3 CfgVehicles Animals (Wayback, January 2025).
- FINDING: no cow class in vanilla. Any cattle context must be a sound, not
  an animal.
- FINDING: no dolphin class in vanilla. The `Fin_*` classes are dogs, not
  dolphins.
- FINDING: no flying-bird or insect unit class in vanilla. Flying birds and
  insects are `CfgNonAIVehicles` ambients, not spawnable agents.
- FINDING: night insects have no confirmed vanilla sound in the plan's
  confirmed set. The bed falls back to the owl or bird context instead of a
  fetch.
- FINDING: deer and wolves. The plan cites the prefix
  `A3\sounds_f_enoch\` with the filenames `deer_call_01..11.wss` and
  `wolves_01..03.wss`. The exact subfolder is not pinned, and the base game is
  not installed on the build machine, so no full path is committed to the
  manifest. This is the one deliberate omission.
- FINDING: no `CfgAmbientSounds` class list. The engine ambient bed is
  controlled by `enableEnvironment`, not by a per-context class list.

## Species table

The machine-readable table is `addons/wildlife/data/species_table.sqf`. Each
row is `[biomeFamily, [class, ...]]`. The families are the Koppen first-letter
groups, cold, temperate, arid and tropical, plus the water and settlement
overlays. Every class is a confirmed vanilla CfgVehicles Animals class. The
kernel `fnc_speciesForBiome` builds a deterministic `[class, count]` mix from
the biome, the time, the water and the vegetation score, using a small integer
hash of the mission seed and the class index. Two clients at the same cell and
time see the same mix.

## Resource model

Water is a cell where `EFUNC(environmental,getCoastDistance)` is below the
arrival distance. Grazing is a cell where the vegetation vote in
`aee_environmental_terrainSignals` scores high. `fnc_resourceScore` turns the
water proximity or the vegetation score and the distance into a suitability,
and `fnc_pickResourceTarget` walks an eight point ring at each increasing
radius and returns the best point. The providers that read the two published
facts are supplied by the fauna runtime.

## Fauna register additions

The fauna constants are modelling choices, UNSOURCED, except the animal class
list and the agent control facts.

| Constant | Value | Source | State |
| --- | --- | --- | --- |
| Animal hard cap per client | 16 | Modelling | [UNSOURCED] |
| Spawn radius | 350 m | Modelling, inside the 800 m ambient far plane | [UNSOURCED] |
| Despawn radius | 600 m | Modelling | [UNSOURCED] |
| Hunger rate | 0.02 per second | Modelling | [UNSOURCED] |
| Thirst rate | 0.03 per second | Modelling | [UNSOURCED] |
| Herd size, sheep and goat | 3 to 6 | Modelling | [UNSOURCED] |
| Grazing arrival distance | 40 m | Modelling | [UNSOURCED] |
| Water arrival distance | 25 m | Modelling | [UNSOURCED] |
| Biome species table | Per-biome class lists | BIKI CfgVehicles Animals | [P-W] |
| `BIS_fnc_animalBehaviour_disable` | true | BIKI Animals, Override Default Animal Behaviour | [P] |
| Agent move commands | `moveTo`, `setDestination` | BIKI Animals, agents cannot use `doMove` | [P] |
| Agent locality | Local | BIKI createAgent, BI feedback T155634 | [P] |

## Two-client parity

The layer is client-local cosmetic ecology. Each client spawns its own local
animals, so the same cell, biome and time give the same species mix on both
machines, but not the same individual objects. No publicVariable is needed and
no server spawn happens. The engine ambient system behaves the same way. An
operator confirms parity by joining two clients, standing at one grid, and
checking that the species mix matches while the individual animals differ.
This is the operator-only parity check.

## Sources

- BIKI Arma 3 Sound Files, the confirmed `.wss` set.
- BIKI `playSound3D`, the positional one-shot and its `local` argument.
- BIKI `createSoundSource`, the local looping positional source.
- BIKI `CfgSFX`, the `Owl` and `Sound_Stream` classes.
- BIKI `enableEnvironment`, `[ambientLife, ambientSound, windSound]`.
- BIKI Arma 3 CfgVehicles Animals (Wayback, January 2025), the animal class
  list and the four findings about absent classes.
- BIKI Arma 3 Animals Ambient System, the per-client local ambient spawn.

## Register additions

The sound runtime constants are modelling choices, UNSOURCED.

| Constant | Value | Source | State |
| --- | --- | --- | --- |
| Sound-instance cap per client | 8 | Modelling | [UNSOURCED] |
| One-shot sound max distance | 120 m | `playSound3D` distance argument | [P] |
| Spook flight-initiation distance, small bird | 8 to 25 m | Flight-initiation distance scales with body mass and starting distance, Blumstein 2003 and Ydenberg and Dill 1986 | [P-concept], numeric default [UNSOURCED] |
| Gunfire spook radius | 150 to 250 m | The human gunshot peak is about 140 dB at the muzzle, NIOSH and OSHA hearing-loss literature. No animal distance source | [UNSOURCED] |
| Quiet approach speed threshold | 1.5 m/s | Modelling, from the engine `speed` value | [UNSOURCED] |
