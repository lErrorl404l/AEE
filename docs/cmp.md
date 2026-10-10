# Configuration Management Plan

This plan sets change control for the AEE repository. It follows JSP 945,
MOD Policy for Configuration Management (V2.0, December 2021). AEE applies
JSP 945 by relevance. AEE holds no MOD system, no classified data, and no
procurement contract. AEE claims no certification. Section 8 states the
claims this repository does not make.

## 1. Scope

The plan covers every file the repository tracks. That is the addons, the
data corpora, the tools, the tests, the documentation, and the build files.

The plan covers the release archives too. The archive directory
`releases/` is not tracked, because a build product is not a source. The
release records live in `docs/releases/` and in `CHANGELOG.md`.

Two records hold the configuration.

| Record | Holds | Authority |
|---|---|---|
| `git` history | File content, author, time, signature | Defence Git Practices |
| `CHANGELOG.md` | The change set of each release | Keep a Changelog |

Git records what changed. The changelog records what shipped.

## 2. Configuration identification

A Configuration Item (CI) is one controlled unit of the product. JSP 945
principle 2 selects the CIs. The design organisation decides the split.

The addons are the software CIs. Each addon is one directory under
`addons/`. The build compiles each addon into one PBO. The addon set is
recorded in `docs/architecture/addon-map.json`. The target tree holds 45
addons. ADR-032 records the split.

| CI class | Item | Path | Control |
|---|---|---|---|
| CI-A | Addon source | `addons/<name>/` | `hemtt check`, `make lint` |
| CI-B | Addon interface | `docs/icd/` | `tools/architecture/interface_contracts.py --check` |
| CI-C | Addon dependency map | `docs/architecture/addon-dependencies.md` | `tools/architecture/addon_dependencies.py` |
| CI-D | Data corpora | `data/` | The per-corpus validators |
| CI-E | Build tooling | `tools/` | `make lint`, `run_tests.py --fast` |
| CI-F | Documentation | `docs/` | The docs gates |
| CI-G | Build configuration | `.hemtt/project.toml`, `mod.cpp` | `hemtt check` |
| CI-H | Version record | `addons/lib/script_version.hpp` | The release process |
| CI-I | Change log | `CHANGELOG.md` | `tools/sync_changelog.sh` |
| CI-J | Decision records | `docs/adr/` | `tools/tests/test_adr_numbers.py` |
| CI-K | Software bill of materials | `tools/make_sbom.py` output | `.github/workflows/sbom.yml` |

The interface between two addons is a CI in its own right (CI-B). The
producer owns the variable. The consumer reads it. The interface documents
under `docs/icd/` record every boundary. They are generated from the source,
so a boundary cannot drift from the code.

## 3. Change control

JSP 945 principle 3 controls the change. AEE uses trunk-based development.

- One permanent branch: `main`. It is the baseline.
- A change runs on a short-lived branch, named `<type>/<issue>-<slug>`.
- The change merges to `main` through a pull request.
- A commit that changes a settled choice adds an ADR under `docs/adr/`.
- A commit that fixes a defect names the issue in the body.
- Every commit is signed. The signature is the non-repudiation record.

The change authority is the repository maintainer. There is no separate
Configuration Control Board, because the repository has one maintainer.
Section 8 of the operating rules reduces the process duties that exist only
to support a team. It never reduces a statutory, safety, or licence duty.

## 4. Configuration status accounting

JSP 945 principle 4 records the state of each CI. AEE records it in three
places.

- `git log` records every change, its author, and its signature.
- `CHANGELOG.md` records the shipped change set of each release.
- The signed tag records each release baseline.

The version lives in `addons/lib/script_version.hpp`. HEMTT reads that file.
The field `[version] path` in `.hemtt/project.toml` names it. The release
process sets the version before the tag.

## 5. Configuration audit

JSP 945 principle 5 audits the CI in two ways.

- A Functional Configuration Audit checks that the item meets its stated
  requirements. In AEE the test suites are the functional audit. The suite
  `tools/validation/validate_oracles.py` checks the physics against
  independent references. Section 5 of the Software Test Plan names the
  levels.
- A Physical Configuration Audit checks the as-built item against the
  design. In AEE the as-built item is the built PBO set. The audit checks
  the built version against `script_version.hpp`, the changelog, and the
  SBOM.

The CI gates run both audits on every change. `make lint` runs the local
set. The workflow `ci.yml` runs the same set. `check_lint_parity.py` fails
when the two sets differ, so a local gate cannot be narrower than CI.

## 6. Baselines and releases

A release baseline is a signed tag on `main`. The release process is in
`docs/releases/README.md`. A baseline record is one file per release under
`docs/releases/`.

The record holds the version, the tag, the change set, and the audit
evidence. The audit evidence is the gate result at the tag. The release
signs the PBO set with an ephemeral key. The file `.hemtt/project.toml`
sets `[hemtt.release] sign = true`.

## 7. Standards and their application

| Standard | Title | Application in AEE |
|---|---|---|
| JSP 945 | MOD Policy for Configuration Management (V2.0, Dec 2021) | Primary source. The five CM principles in sections 2 to 5. |
| Def Stan 05-57 | Configuration Management of Defence Materiel | Reference for a Deliverable CM Plan. AEE has no such contract. |
| ISO 10007 | Quality management. Guidelines for configuration management | The framework JSP 945 aligns with. |
| STANAG 4427 | Configuration Management in System Life Cycle Management | NATO baseline and audit practice. |
| AQAP 2210 | NATO Software Quality Assurance Requirements | Guides the software quality checks by relevance. |
| JSP 939 | Defence Policy for Modelling and Simulation (V3.1, 2025) | The VV&A practice. See `docs/vv-a.md`. |
| JSP 940 | MOD Policy for Quality | CM and quality assurance combine. |

AEE cites no standard as a certified status. A citation names the practice
AEE follows. It does not claim that AEE passed an assessment against the
standard.

## 8. Claims AEE does not make

AEE holds no MoD system, no classified data, and no procurement contract.
AEE does not claim certification against JSP 945, Def Stan 05-57, AQAP
2210, Cyber Essentials, or any other standard. AEE applies the practice by
relevance. It never cites a standard as a passed audit.

## 9. Roles and relief

One maintainer holds every role. The relief covers merge approval, review
panels, and published reports. It never covers a statutory, safety, or
licence duty.
