# ICD: ambience to wildlife

- Producer CI: `addons/ambience/`
- Consumer CI: `addons/wildlife/`
- Direction: one way. `ambience` must initialise before `wildlife` reads.
- Variables crossing: 6.

A variable named `aee_ambience_{leaf}` is written as `EGVAR(ambience,leaf)` by the producer and read as `EGVAR(ambience,leaf)` or `QEGVAR(ambience,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_ambience_ambientEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_logWildlifeState.sqf:98` | UNKNOWN |
| `aee_ambience_callBudget` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_applyAnimalBehaviour.sqf:241` | The heard-call bus cap |
| `aee_ambience_callRange` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_applyAnimalBehaviour.sqf:255` | The audibility range, metres |
| `aee_ambience_communicationEnabled` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_applyAnimalBehaviour.sqf:218` | Enable the heard-call bus |
| `aee_ambience_silenceDecay` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_wildlifeTick.sqf:217` | UNKNOWN |
| `aee_ambience_soundInstances` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_logWildlifeState.sqf:84` | The live one-shot expiry times, bounded by the instance cap |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
