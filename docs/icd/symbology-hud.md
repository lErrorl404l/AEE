# ICD: symbology to hud

- Producer CI: `addons/symbology/`
- Consumer CI: `addons/hud/`
- Direction: one way. `symbology` must initialise before `hud` reads.
- Variables crossing: 2.

A variable named `aee_symbology_{leaf}` is written as `EGVAR(symbology,leaf)` by the producer and read as `EGVAR(symbology,leaf)` or `QEGVAR(symbology,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_symbology_symbologyEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/hud/functions/hud/fnc_hudMarkers.sqf:62` | Registered setting under **AEE HUD > Symbology**: draw the NATO APP-6(C) map and world symbols (default off) |
| `aee_symbology_symbologyPalette` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/hud/functions/hud/fnc_hudMarkers.sqf:49` | Registered setting under **AEE HUD > Symbology**: the affiliation palette NATO, OPFOR or Auto (default Auto) |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
