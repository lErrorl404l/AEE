# ADR-015: AI and Wildlife Soak Observability

Status: Accepted
Date: 2026-10-05
Decision: The AI and wildlife layer is verified by a separate long mission with a soak mode and a stress mode, by a consolidated debug line, and by an on-demand monitor. The live client rows stay operator-only.

## Context

The disturbance field records movement and gunfire, and it is per-machine state. The field grew with every miss, because no owner pruned it. A player who kept moving added up to nine cells per second, and every apply and every sample walked the whole field. The per-tick cost grew with the field.

The addon defined four constants and used none of them. `AI_CELL_SIZE` is 50 m, `AI_CELL_HORIZON` is 120 s, `AI_CELL_CAP` is 256 and `AI_STIMULUS_HALF_LIFE` is 45 s.

The live animals and the sound bed run only on a machine with a player. A headless dedicated server cannot start them. The soak must therefore drive the pure kernels and the server path. The live client look and sound cannot be proven headless.

## Decision

1. The disturbance field is bounded. `fnc_disturbancePrune` drops any cell past `AI_CELL_HORIZON` and caps the field at `AI_CELL_CAP`. The two owners, `fnc_receiveStimulus` in `aee_ai` and `fnc_wildlifeTick` in `aee_wildlife`, call the prune. `AI_CELL_SIZE` sets the cell edge at 50 m and `AI_STIMULUS_HALF_LIFE` decays a stimulus over 45 s.

2. The soak and the stress run headless. They drive the pure kernels in Python and the server path in Docker. A separate mission, `aee_soak.Stratis`, carries both. `tools/docker_test.sh` starts it with the `--soak` and `--stress` modes. The soak holds for 20 min nominal and 30 min under stress, and it samples every 30 s. The default mission is untouched.

3. The consolidated line is the observability contract. `fnc_logWildlifeState` prints the field size, the live agent count, the live sound-source count and the tick cost in one INFO line. The existing `AEE Debug > AI` and `AEE Debug > Wildlife` switches gate it. The line is cheap when the switches are off, because the function returns before it reads any state.

4. The monitor is the on-demand instrument. `fnc_monitorWildlife` prints the consolidated line, the wildlife tick cost and the AI tick cost at once, from the debug console. It reads local state only, and it prints to the local log only.

5. The live client rows are operator-only. The visual look and the audible bed cannot be claimed from a headless run. The two-client parity check needs two real clients.

6. The self-hosted runner holds the nightly and the weekly soak. The `soak` job in `.github/workflows/docker-test.yml` runs on the self-hosted runner with the labels `self-hosted`, `linux` and `aee`. It stays operator-gated, and it is not exposed to a public push.

## Consequences

- The field cost is bounded regardless of player movement.
- The soak proves the field bound, the caps and the tick budget. It proves nothing about the live client look.
- The debug line adds no network traffic, because it reads local state only.
- The core `updateEnvironment` budget stays at 5 ms. The wildlife dry-run tick budget stays at 2 ms. Both are unchanged, and both are re-asserted at the soak end.
- Alternatives: a soak inside the default mission was rejected, because the 180 second wait and the fixed DONE timer would break it. A new setting was rejected, to keep the settings taxonomy stable. The existing debug switches gate the line.

## References

- `docs/adr/ADR-013-wildlife-ambience-ownership.md`, the addon split and the client-local rule.
- `docs/adr/ADR-011-nightly-headless-regression.md`, the headless regime and the self-hosted runner.
- `.omo/plans/aee-ai-wildlife-qa.md`, the tasks, the hull and the budgets.
- `docs/wiki/research/wildlife-ambience-dossier.md`, the field semantics and the source register.
- No Linux Arma 3 client exists, so the live client rows are operator-only.
