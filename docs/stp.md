# Software Test Plan

This plan states how AEE is tested. It is the test baseline for the
software CIs named in `docs/cmp.md` section 2.

The plan covers four test levels. Each level answers a different question.

## 1. Scope

The plan covers the addon source, the data corpora, the tooling, and the
built mod. The engine keeps the solver and the renderer. The plan tests the
mod against the engine, not the engine itself.

## 2. Test levels

| Level | Question | Tool | Runs |
|---|---|---|---|
| Unit | Does one kernel compute the stated result? | `tools/run_tests.py` | Every commit |
| Verification | Does the code match the published formula? | `tools/validation/validate_physics.py` | Every commit |
| Validation | Does the output match an independent oracle? | `tools/validation/validate_oracles.py` | Every commit |
| Integration | Does the mod run in the engine? | `tools/docker_test.sh`, `tests/docker/` | Nightly, and on demand |

### 2.1 Unit tests

A unit suite is one file `tools/tests/test_<name>.py`. The runner is
`tools/run_tests.py`. The flag `--fast` runs the unit suites and skips the
validation harness.

A unit suite reads the source or executes the shipped SQF. The harness
`tools/tests/sqf_lite.py` runs the shipped SQF functions. It proves the
shipped code, not a copy.

A suite that is not registered in the runner does not gate CI. The gate
`tools/tests/test_suite_registration.py` fails on an unregistered suite.

### 2.2 Verification

Verification checks the SQF mirror against a published formula. The script
`tools/validation/validate_physics.py` holds the mirror and the reference
values. A mirror that disagrees with the published formula fails.

The sensor scripts `validate_sensors.py`, `validate_illuminance.py`, and
`validate_dof.py` verify the sensor equations against published bands.

### 2.3 Validation

Validation checks the output against an independent oracle. The script
`tools/validation/validate_oracles.py` feeds one scenario through the mod
and through an independent solver, and compares them. The oracles are in
`docs/vv-a.md`.

The tolerance band is the acceptance criterion. A result outside the band
fails.

### 2.4 Integration

Integration runs the built mod in the engine. The harness is
`tools/docker_test.sh`. The test missions are under `tests/docker/`. The
harness runs an Arma 3 server headless, loads the mod, and runs a mission
that exercises a subsystem.

The nightly workflow `docker-test.yml` runs the integration suite. The
workflow `ci.yml` runs the unit, verification, and validation levels.

## 3. Test environment

- Python 3.12 with `numpy` and `pillow`.
- HEMTT, for the build and the config check.
- An Arma 3 dedicated server, for the integration level only.

The local gate set matches the CI set. The gate
`tools/validation/check_lint_parity.py` fails when the two differ. A local
gate narrower than CI is not a gate.

## 4. Entry and exit criteria

Entry: the source builds with `hemtt check -p -e`.

Exit: every level passes.

- `python3 tools/run_tests.py --fast` exits 0.
- `python3 tools/validation/validate_oracles.py` exits 0.
- `make lint` exits 0.
- The integration suite reports no failed phase.

A failing level blocks the merge.

## 5. Test data

A physics test uses a cited corpus under `data/`. The corpus names its
source. A test value with no source is a gap. The gap is recorded, not
hidden.

The generator `tools/validation/gen_star_catalog.py` and its siblings
regenerate a data table from its corpus. The flag `--check` proves the
committed table is fresh.

## 6. Coverage

A requirement in `docs/srs.md` traces to a test. The test name and the
requirement source share the ADR number or the issue number. A requirement
with no test is a gap.

The map from a requirement to a test is by source, not by a separate
matrix. The ADR or the issue is the join key.

## 7. Roles and relief

One maintainer runs the tests. The relief in `docs/cmp.md` section 9 covers
a review panel. It never covers the test itself.
