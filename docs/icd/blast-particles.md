# ICD: blast to particles

- Producer CI: `addons/blast/`
- Consumer CI: `addons/particles/`
- Direction: one way. `blast` must initialise before `particles` reads.
- Variables crossing: 2.

A variable named `aee_blast_{leaf}` is written as `EGVAR(blast,leaf)` by the producer and read as `EGVAR(blast,leaf)` or `QEGVAR(blast,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_blast_blastInjury` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/fnc_dumpState.sqf:20` | Last explosion injury vector [eardrum, lungThresh, lung1, lung50, lung99, throw] |
| `aee_blast_blastOverpressureKpa` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/particles/functions/fnc_dumpState.sqf:26` | Last explosion incident overpressure in kPa (Kingery-Bulmash) |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
