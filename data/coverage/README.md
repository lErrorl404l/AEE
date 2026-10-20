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

Two kinds of class leave a table before it is scored, and both stay named
in the output and in the baseline under `excluded`:

- a ground class whose chain passes `StaticWeapon` is a weapon
  emplacement, not a vehicle. The fleet inventory states the same rule in
  `tools/validation/gen_vehicle_bindings.py`: a ground class is a
  `LandVehicle` that is not a `StaticWeapon`.
- an armament class that the shared kind filter reads as equipment rather
  than a munition is not a weapon that fires a projectile. The filter is
  `tools/validation/munition_kind.py`.


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
`carried_launchers`, `vehicle_armament`. Three `#` comment lines carry the
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
(`hit`, `total`, `pct`), `unresolved_modded`, and `excluded` by kind.

`tools/tests/test_match_coverage.py` holds the lock. It re-derives every
table from the scan and compares the result with this file, and it checks
each gap file against the tool's own output. A stale artefact fails the
sweep.
