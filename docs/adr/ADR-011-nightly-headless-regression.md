# ADR-011: Nightly Headless Regression Test

Status: Accepted
Date: 2026-10-04
Decision: The headless Docker test runs nightly on a self-hosted runner that
already holds an Arma 3 dedicated server. There is no steamcmd step and no
per-run server download.

## Context

A Phase-10 regression in the environment tick stayed latent until a manual
Docker run found it. The test existed but ran only on demand, so a fault could
sit in the tree for days. The exposure window needed a bound.

The test needs an Arma 3 dedicated server install. The server is about 10 GB.
A GitHub-hosted runner starts empty, so it would need a steamcmd provision on
every run. That setup is fragile and it wastes runner minutes on the download.
The server files are not redistributable, so they cannot be committed or baked
into a public image.

## Decision

1. The workflow triggers on a nightly schedule at 03:00 UTC and on manual
   `workflow_dispatch`. It does not trigger on push or on pull request.

2. The job runs on a self-hosted runner with the labels `self-hosted`,
   `linux` and `aee`. That runner already holds the Arma 3 dedicated server,
   so there is no provision step and no download.

3. The workflow binds `ARMA3_SERVER_ROOT` from the repository variable
   `vars.ARMA3_SERVER_ROOT`, which the operator sets once. The two fallback
   paths, `tests/docker/server_root` and `tests/docker/server`, are gitignored
   and absent on a fresh checkout.

4. A named preflight step asserts the server binary at `arma3server_x64`. It
   prints an `::error::` message and exits non-zero when the binary is absent.
   The test step then fails loud on a real regression. The two failures are
   distinguishable in the run summary.

5. The workflow uploads the run log on failure, under the artifact name
   `aee-docker-log`.

## Consequences

- Cost: the runner must be online at 03:00 UTC. A missed night leaves a gap
  until the next run or a manual dispatch.
- Safety: the workflow triggers only on a schedule and on dispatch, so a
  public repository never runs untrusted code on the self-hosted runner.
- Scope: `--hosts` and `--maps` stay manual. Their host and Workshop content
  is not in the repository and is not redistributable.
- Alternatives: a GitHub-hosted steamcmd provision was rejected for setup
  cost and a large per-run download. A prebuilt container image was rejected
  because its per-run image pull is still a large download.

A local fallback is a systemd user timer that runs `tools/docker_test.sh`. It
is not equivalent: it has no preflight step, no artifact upload and no GitHub
status.

## References

- Plan: `.omo/plans/aee-coverage-gaps.md`, Part A.
- `tools/docker_test.sh`: the server-root resolution order.
- `.github/workflows/docker-test.yml`: the nightly workflow.
- Steam Subscriber Agreement: the no-redistribution intent. The specific
  section is UNSOURCED in this pass.
