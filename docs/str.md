# Software Test Report

This report records the test result for the current baseline. It follows
the plan in `docs/stp.md`.

## 1. Baseline tested

| Field | Value |
|---|---|
| Branch | `main` |
| Base commit | `e1ff9584` |
| Change under test | The documentation layer of issue #73 |
| Date | 2026-10-10 |
| Environment | Linux, Python 3.12, HEMTT, no Arma 3 server |

The change under test adds documentation and two tools. It changes no
addon, no setting, and no engine call. The test result below therefore
covers the whole repository at this commit.

## 2. Result summary

| Level | Command | Result |
|---|---|---|
| Unit and physics | `python3 tools/run_tests.py --fast` | Pass |
| Local gate set | `make lint` | Pass |
| Verification | `python3 tools/validation/validate_physics.py` | Pass |
| Validation | `python3 tools/validation/validate_oracles.py` | Pass |
| Library audit | `python3 rules/audit.py` | Pass |
| Interface gate | `python3 -m unittest tools.tests.test_icd_docs` | Pass |
| Integration | `tools/docker_test.sh` | Not run |

## 3. Unit and physics result

The fast runner ran 225 suites. It reported 5714 test cases. No suite
failed. The runner exited 0.

The new suite `tools/tests/test_icd_docs.py` ran seven checks. Every check
passed.

## 4. Verification result

The script `tools/validation/validate_physics.py` checks the SQF mirror
against the published formula. It passed.

The sensor scripts `validate_sensors.py`, `validate_illuminance.py`, and
`validate_dof.py` passed.

## 5. Validation result

The script `tools/validation/validate_oracles.py` compares the mod output
against independent oracles. It passed. The oracles and the tolerance
bands are in `docs/vv-a.md`.

## 6. Integration result

The integration level did not run. No Arma 3 dedicated server is available
in this environment. The integration suite runs in the workflow
`docker-test.yml`.

This is a gap in this report. The gap is recorded, not hidden. The
integration result for a release comes from that workflow.

## 7. Gate parity

The local gate set matches the CI set. The gate
`tools/validation/check_lint_parity.py` reported 64 matching checks.

## 8. Defects found

One defect is recorded against the version file.

- `addons/lib/script_version.hpp` reads 1.1.0.0. The released version is
  1.1.1. The version file was not bumped at that release. See `docs/svd.md`
  section 1 and `docs/releases/v1.1.1.md` section 1.

No defect was found in the change under test.

## 9. Conclusion

The unit, verification, validation, and audit levels pass. The integration
level is not run in this environment. The baseline is fit to merge on the
strength of the levels that ran.
