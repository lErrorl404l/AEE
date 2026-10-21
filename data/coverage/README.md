# Modded match coverage

How much of the installed content each AEE matcher can name, split by who
declares the class. The modded number is the one that must reach 100%:
every class a mod declares has to resolve in the matcher for its table.

The measurement is `tools/report_match_coverage.py`, and it reads a scan
that `tools/scan_game_classes.py` writes from the installed game and mods.
A class is **base** when the PBO that declares it is in the base game's
`Addons/` directory, and **modded** otherwise. The base PBO list is
recorded in the baseline, so the split is readable without the install.
A mod class that inherits a base class is modded: the catalogue still has
to name the thing the player is looking at.

Every class that leaves a table before it is scored stays named in the
output, in the baseline under `excluded`, and by name in
`data/coverage/excluded_classes.txt`. The vehicle and armament rules are:

- a ground class whose chain passes `StaticWeapon` is a weapon
  emplacement, not a vehicle. The fleet inventory states the same rule in
  `tools/validation/gen_vehicle_bindings.py`: a ground class is a
  `LandVehicle` that is not a `StaticWeapon`.
- an armament class that the shared kind filter reads as equipment rather
  than a munition is not a weapon that fires a projectile. The filter is
  `tools/validation/munition_kind.py`.

The clothing and load-carriage tables apply the same rule:

- an abstract base class is scaffolding, not an item: `Uniform_Base`,
  `Vest_Camo_Base`, `Weapon_Bag_Base`.
- a gore or damage overlay (`guts`, `bulletholes`, `damagedchest`) is a
  texture with no mass and no slot.
- a rucksack table scores `CfgVehicles` under `Bag_Base`, and that root
  also holds a dismantled HMG, a folded tripod, a mortar tube, a
  parachute, a radio bag and a gun bag. They leave the table as "weapon
  bags", "weapon support bags", "parachutes" and "radio bags".
- headwear declared under `Uniform_Base` is a content defect in the mod,
  not a uniform: it leaves the table as "misdeclared headwear" and its
  classes are listed in `excluded_classes.txt`.


## Family rows

A family entry names a family and no mark. The runtime matcher answers it
last, at confidence 7, from a separate `_families` table, and only when
exactly one family row matches. The measurement reads the same two tables
from the generated file, so a class the family rung answers counts as
resolved and never appears in a gap list. A family row is not excluded from
a table: it is an identity the player sees, and it is what the count credits
when no mark answers.

## Grades

Every class resolves, and the grade says how. The order is the ladder:

| Grade | What answered |
|---|---|
| `exact_class` | the class name the corpus maps |
| `alias` | a curated designation the class text carries |
| `keyword` | a derived designation or keyword |
| `closest` | the one entry with a strictly stronger score |
| `inherited` | the nearest config ancestor the corpus names |
| `family` | one family designation, with no mark |
| `type` | the kind of item, when no identity can answer |

`type` is the last resort and is always counted apart, so a table leaning
on it is visible. It names a kind (a uniform, a night-vision device, an
armoured vehicle), never a model, and it carries no figure. A tie at a
mark layer falls to `type`: two candidate marks name no single mark, but
the kind is still known, and no weaker mark layer answers the tie.

## The table records

Each table keeps the classes it cannot name in its own record, with the
reason and the evidence for the reason:

- vehicles: `data/vehicle/MODDED_CLASS_GAPS.md`
- aircraft: `data/aircraft/MODDED_CLASS_GAPS.md`
- vehicle armament: `data/coverage/modded_gaps_vehicle_armament.txt`,
  `data/munition/modded_coverage.json` and the lock
  `tools/tests/test_modded_weapon_coverage.py`

## Regenerate

```bash
OUT=/tmp/all.jsonl python3 tools/scan_game_classes.py \
    "/ext/SteamLibrary/steamapps/common/Arma 3/Addons" \
    "/ext/SteamLibrary/steamapps/workshop/content/107410"
python3 tools/report_match_coverage.py /tmp/all.jsonl \
    --modded --gaps \
    --write-gaps data/coverage \
    --write-baseline data/coverage/modded_baseline.json
```

The install is found from the Steam library. `AEE_ARMA3_DIR` or `--install`
names it instead. The tool stops with an error when the install or its
`Addons/` directory is absent, rather than call every class modded.

## `modded_gaps_<table>.txt`

One file per table: `vehicles`, `aircraft`, `small_arms`,
`carried_launchers`, `vehicle_armament`, `night_vision_devices`,
`uniforms`, `vests`, `helmets`, `rucksacks`. `INVENTORY.md` states every
generated identity table, the corpus behind it, and the tables this
measurement does not score. Three `#` comment lines carry the
table name, the unresolved count and the resolved percentage. Every line
after them is one unresolved modded class, tab-separated:

```
class	display	parent	source
```

`source` is the PBO that declares the class. Rows are ordered by source,
then by class, so rewriting the same content gives the same file and a
worker can diff two runs.

## `modded_baseline.json`

`aee.match_coverage.baseline/1`. `provenance` holds the date, the scan
file, its SHA-256, its row count, the install, the base PBO count and the
base PBO list. It also holds `known_unresolvable`, the modded vehicle gaps
that are expected to stay. Thirteen vehicles stay open in the 2026-10-20
measurement: five tie on a family designation the generator derives from a
mark's canonical name, five tie on the derived RG-33 family keyword, two name
the maker Land Rover and no mark, and one names the FMTV family over a
generic class. `data/vehicle/MODDED_CLASS_GAPS.md` gives each class and its
reason. `tables` holds, per table, the `base` and `modded` counts
(`hit`, `total`, `pct`), `unresolved_modded`, `excluded` by kind, and
`grades`: how many classes each rung answered. `provenance` also holds
`measured_tables`, so a table cannot drop out of the measurement without
the lock noticing. Every table resolves, so every gap file carries its
header and no rows; the file is still written, so a regression that opens
a class shows up as a diff rather than a missing artefact.

`tools/tests/test_match_coverage.py` holds the lock. It re-derives every
table from the scan and compares the result with this file, and it checks
each gap file against the tool's own output. A stale artefact fails the
sweep.

## Captured sources are not redistributed

The repository publishes the extracted data and its citations. It never
publishes the captured third-party pages, drawings, manuals or renders.

- **The record keeps the citation.** Every source record keeps its `url`,
  `locator`, `retrieved`, `sha256`, `tier` and `licence`.
- **The record states where the bytes are.** A record that holds bytes
  carries `"capture": "local-cache-only"`. The value means the bytes that
  `sha256` identifies are held in the machine-local source cache and are not
  redistributed. `sha256` identifies the retrieved bytes. It does not mean
  the bytes ship with the repository.
- **The cache is outside the working tree.** `tools/validation/source_cache.py`
  names it: `$AEE_SOURCE_CACHE` when set, else
  `$XDG_DATA_HOME/aee/source-cache`, else
  `~/.local/share/aee/source-cache`. It mirrors each domain, so
  `data/vehicle/sources/achzarit.wiki` is held at
  `<cache>/vehicle/achzarit.wiki` and `data/symbology/sources/render/x.png` at
  `<cache>/symbology/render/x.png`.
- **Only JSON is tracked.** `data/*/sources/` may hold JSON records and
  nothing else. `tools/tests/test_source_capture_policy.py` fails, naming the
  path, when a tracked file has another extension. There is no allowlist.
- **A verifier skips cleanly.** A tool or test that hashes a capture reads
  the cache and reports a skip when the cache is absent, so a clean clone
  passes. `fetch_vehicle_sources.py --verify`,
  `fetch_aircraft_sources.py --verify`,
  `register_munition_source.py --verify`,
  `validate_vehicle_data.py`, `validate_aircraft_data.py`,
  `validate_ballistics_data.py`, `validate_symbology_catalogue.py` and
  `gen_symbology_catalogue.py --check` follow this rule.

The coverage measurement reads a scan of the installed game, never a capture,
so the split and the counts are unaffected by this policy.
