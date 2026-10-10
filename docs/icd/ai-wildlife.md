# ICD: ai to wildlife

- Producer CI: `addons/ai/`
- Consumer CI: `addons/wildlife/`
- Direction: one way. `ai` must initialise before `wildlife` reads.
- Variables crossing: 4.

A variable named `aee_ai_{leaf}` is written as `EGVAR(ai,leaf)` by the producer and read as `EGVAR(ai,leaf)` or `QEGVAR(ai,leaf)` by the consumer.

| Variable | Type | Unit | Range | Update | Evidence (first read) | Purpose (Annex C) |
|---|---|---|---|---|---|---|
| `aee_ai_agents` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_ecologyTick.sqf:34` | The agent registry, one entry per registered agent |
| `aee_ai_disturbance` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_ecologyTick.sqf:66` | The local disturbance field, an array of `[[cx,cy], magnitude, time]` |
| `aee_ai_ecologyDriven` | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | `addons/wildlife/functions/fnc_ecologyTick.sqf:46` | UNKNOWN |
| `aee_ai_need` | SCALAR | fraction | 0..1 | UNKNOWN | `addons/wildlife/functions/fnc_applyAnimalBehaviour.sqf:106` | Need pressure 0..1 on an anchor object |

The default value and the update frequency are the producer's contract. They are set in the producer's CBA settings and recorded in `docs/wiki/annexes/annex-c-variable-reference.qmd`. This document records the boundary and the direction, not a second copy of the variable reference.

Regenerate with `python3 tools/architecture/interface_contracts.py`.
