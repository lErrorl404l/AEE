# ADR-031: The conformance layer - self-describing detect and repair

Status: proposed. Phase 0 (test-suite registration) and the Phase 2 meta-gates
for test registration and ADR numbering landed with this record. The manifest,
the runner and the remaining meta-gates are not yet built.

Relates to ADR-001 (engine anchors), ADR-011 (nightly headless regression),
ADR-017 (flight physics ceiling), ADR-027 (ownership architecture, declared
sovereignty), ADR-030 (map legibility).

---

## Context

AEE already carries a large conformance surface. It is real and it works.
It is also static: every part of it is a hand-written list, and drift is
found by a human who remembers to look.

The evidence:

1. `make lint` (Makefile) runs 56 invocations. The same 56 are written again
   in `.github/workflows/ci.yml` (validate job). `tools/validation/check_lint_parity.py`
   keeps the two lists equal, so a check cannot be added to one and not the
   other. The parity guard is correct, but the list itself is typed by hand.

2. `tools/run_tests.py` hand-lists roughly 150 unit suites. `make test`
   discovers 198 files under `tools/tests/`. CI and pre-commit run
   `run_tests.py --fast`, not discovery. Therefore 48 test suites existed,
   passed, and never gated CI. This is the exact failure recorded on
   2026-10-08: `test_engine_overrides.py` and `test_probe_numbers.py` were
   committed but not registered, so CI never ran them. The detector existed.
   The wiring did not.

3. 35 generators implement `--check`. 24 `tools/**/gen_*.py` do not. The
   difference (corpus build versus runtime projection) lives only in each
   file's docstring.

4. Hand-written tables remain where the method asks for generation:
   `addons/optics/config_locationtypes.hpp`, `config_mapcolors.hpp`,
   `config_mapdisplays.hpp`, `config_mapicons.hpp`, `config_curator.hpp`,
   `RscTitles.hpp`, `addons/wildlife/data/species_table.sqf`,
   `sound_manifest.sqf`. All carry a hand-written header, not a "Generated
   by" header.

5. The Docker probe expectations are hand-synced across three places:
   `tests/docker/verify.py` `_probe_expected`, `tests/docker/verify.py` the
   FAIL regex, and `init.sqf` the `execVM` list. `test_probe_numbers.py`
   guards uniqueness in the three lists. It does not guard completeness: a
   probe file that nobody `execVM`s, or a PASS line for a probe that was
   deleted, passes unnoticed.

6. Two files claimed ADR number 029
   (`ADR-029-map-legibility...` and `ADR-029-marker-derivation...`).
   Nothing checked ADR number uniqueness. The collision is corrected in this
   change: the map-legibility record is now ADR-030, and the marker record
   stays ADR-029. The ADR-number meta-gate below keeps the sequence unique and
   gap-free from then on.

**Root cause.** The conformance layer has no self-description. Every new
generated artifact, test, or probe must be remembered and re-registered by
hand in several places. The `--check` generators already contain the repair
primitive (a deterministic corpus-to-artifact render, byte-stable). What is
missing is a registry that names, for each artifact, its generator, its
truth source, and whether repair is safe, plus a runner that reads the
registry. The operator's method applies directly: **dynamic over static**
(the manifest is data, the runner reads it), **matching over writing** (the
expectations are derived by matching the tree, not typed), **finding over
assuming** (meta-gates discover artifacts and refuse to proceed until each
is classified).

---

## Decision

Build a conformance layer with three parts: a **manifest**, a **runner**,
and **meta-gates that force every new artifact to classify itself**.

### 1. The manifest (the truth index)

One committed file, `tools/conformance/manifest.json` (schema
`aee.conformance.manifest/1`). It records the *conformance index*, not the
data. Each entry has:

| field | meaning |
|---|---|
| `id` | stable name, e.g. `terrain_tables` |
| `generator` | the exact command that writes the artifact |
| `artifacts` | the committed path(s) the generator writes |
| `truth` | the upstream input the generator reads |
| `truth_class` | `corpus-in-repo`, `repo-scan`, `engine`, `external-web`, `seed` |
| `repair` | `auto`, `detect-only`, `art` |
| `check` | the exact command that fails on drift |

The manifest is the single source for the runner, for `make`, and for the
CI. `make lint` and CI are then generated from the manifest, so the
hand-listed 56 collapse into one place. `check_lint_parity.py` becomes a
check that the workflow equals the manifest, which is stronger than the
current Makefile-versus-workflow equality.

### 2. The runner (`tools/conformance.py`)

Two modes, both idempotent and deterministic:

- `--check` - run every `check` command. Report **all** failures (never
  stop at the first), and exit 1 on any. This is what CI and pre-commit run.
- `--repair` - run the `generator` in write mode for every entry whose
  `repair` is `auto` or `art`, then re-run `--check` to prove convergence.
  If `--check` still fails, exit 1 and print the residual. **Repair never
  touches a `detect-only` or `external-web` entry.**
- `--discover` - walk the tree and print any artifact, generator, test, or
  probe that is not yet classified. This is the "finding instead of
  assuming" probe. It writes nothing.

The repair boundary is the core decision. The rule is mechanical:

> **Repair automatically when the artifact is a pure function of a
> committed, in-repo input, and the artifact is itself committed.**
> Everything else detects and escalates.

That gives four classes:

| class | example | repair |
|---|---|---|
| runtime projection | `terrain_symbols.json` -> `terrain_symbols.sqf` | **auto** |
| generated doc/code | repo scan -> `extension-contract.md`, `config_docs` | **auto** |
| deterministic art | seed -> NVG blemish PNG/PAA | **art** (auto, binary) |
| corpus build | engine config -> `app6_catalogue.json`, web -> `designations_*.json` | **detect-only** |

### 3. Meta-gates (registration by discovery, not by memory)

New checks, each using the allowlist-with-reason pattern already proven
in `tools/tests/test_dump_state_contract.py`:

- `test_suite_registration` - derive the test set by globbing
  `tools/tests/test_*.py`. Assert each is registered in `run_tests.py` or on
  a reasoned allowlist. **Closes the 48-suite gap.**
- `test_adr_numbers` - derive the ADR set by globbing `docs/adr/ADR-NNN-*.md`.
  Assert the numbers are unique and gap-free, or on a reasoned allowlist.
  **Closes the 029 collision and stops a recurrence.**
- `generator_registration` - derive the generator set by globbing
  `tools/**/gen_*.py`. Assert each is in the manifest or on a reasoned
  allowlist. **Closes the 24-generator gap.** (Not yet built.)
- `artifact_generation` - derive the artifact set by globbing
  `addons/**/config_*.hpp` and `addons/**/data/*.sqf`. Assert each carries a
  "Generated by" header that names a manifest entry, or is on a reasoned
  allowlist. **Finds the hand-written tables that should be generated.**
  (Not yet built.)
- `manifest_hygiene` - assert generator, artifact, truth, and repair fields
  are present and valid, that every listed path exists, and that every probe
  file under `tests/docker/missions/*/aee_p*_*.sqf` is referenced by
  `init.sqf` and has both a PASS expectation and a FAIL-regex entry.
  (Not yet built.)

`test_probe_numbers.py` extends to read the manifest and to generate the two
`verify.py` lists, so the three hand-synced probe lists become one.

### 4. What each check verifies, against which truth

| check family | verifies | truth source |
|---|---|---|
| `--check` projection | the committed artifact equals a fresh render of the corpus | the committed corpus (`data/**/*.json`) |
| corpus validator (`validate_*`) | the corpus is well-formed, sourced, and internally consistent | the corpus plus its `sources.json` provenance |
| source validator (`sqf_validator`, `config_style_checker`, `validate_cross_module`) | the code matches the declared contract | the code and the engine naming rules |
| `gen_extension_contract --check` | the published contract equals a scan of the tree | the tree itself |
| ownership sentinel | the live config still carries AEE's declared value | the engine config, read live at init |
| oracle validation (JSP 939 VV&A) | the formula matches a published reference | the standard or the published table |
| Docker probes (P64-P122) | the built PBO behaves correctly in the engine | the engine runtime |

Each manifest entry states its `truth_class`, so a reader can see whether a
check proves a *projection is fresh*, a *corpus is sourced*, or a *runtime
behaves*.

### 5. How it runs, in order, failing fast

```
developer loop      make repair                 # write mode, then prove convergence
pre-commit          conformance --check         # fast subset (no engine, no network)
                    run_tests.py --fast
make lint / CI      run_tests.py --fast
                    conformance --check         # all 56, all failures reported
                    check_lint_parity.py        # workflow == manifest
engine (Docker)     docker_test.sh               # probes; corpus-vs-engine freshness
```

Ordering is by cost and by truth dependency: pure-code checks first (no
engine, no network, fast), engine-truth checks last (slow, needs Docker).
`conformance --check` aggregates and reports every failure in one run, as
`make lint` already does, so a later broken gate is visible without a second
pass.

### 6. Ceilings (what cannot be automated, and why)

- **Engine internals.** The solver, renderer, flight model, ballistic
  integrator, and AI routing are closed C++ (ADR-017). No check reaches
  them. Only a Docker probe observes their behaviour.
- **External truth cannot be rebuilt in a gate.** A corpus built from the
  engine or the web needs that source present. The gate can prove the
  corpus is *unchanged since commit*. It cannot prove it is *still correct*
  without the source. That is a Docker or a manual step.
- **Standards judgement.** A check can prove a value carries a source and a
  grade. It cannot prove the value is *right*. Physics fidelity and colour
  representation are human calls (for example the RGB representation of a
  named USGS colour).
- **Licensing and authorship.** Provenance is a datum. The decision to adopt
  a licence, and whether a source may be absorbed, is a human decision (the
  Workshop licence survey stands as evidence, not as an oracle).
- **Load order over an undeclared mod.** Priority is not guaranteeable
  (ADR-027). Detect and log. Do not chase.
- **Naming and ADR choices.** A generator can enforce that an ADR number is
  unique. It cannot choose the architecture.
- **Semantic drift inside a generated artifact.** Repair keeps the artifact
  equal to its corpus. If the *corpus* is wrong, repair propagates the wrong
  value faithfully. The correction belongs upstream, in the corpus and its
  source.

### 7. Build order (phased)

**Phase 0 - Measure and register. No behaviour change.**
- Add `test_suite_registration` with the current 48 as reasoned allowlist
  entries, then drain the allowlist by registering the real suites. Each
  entry needs a reason (superseded, slow, needs Docker). Deliverable: the 48
  classified. CI runs every suite that is not explicitly exempt.
- **Landed in this change for the suites that run in the fast unit context.
  The remainder sit on the reasoned allowlist.**

**Phase 1 - Manifest and runner, detect only.**
- Write `tools/conformance/manifest.json` and `tools/conformance.py`.
- Seed the manifest from `--discover` and from the existing `--check`
  invocations. `--repair` exists but is not wired.
- `check_lint_parity.py` reads the manifest.
- Gate: `conformance --check` equals the current `make lint` result, no
  regression.

**Phase 2 - Meta-gates.**
- Add `generator_registration`, `artifact_generation`, `manifest_hygiene`
  (includes ADR-number uniqueness).
- Extend `test_probe_numbers.py` to the probe manifest and generate the
  `verify.py` lists.
- Gate: adding an unclassified generator, artifact, test, or probe fails.
- **Landed in this change: `test_suite_registration` and `test_adr_numbers`,
  wired into the `Makefile` lint target and the CI validate job. The
  generator, artifact and probe meta-gates remain.**

**Phase 3 - Repair by default.**
- Add `make repair`. Wire `conformance --check` into `make lint`, CI, and
  the pre-commit hook.
- Gate: a deliberate drift is fixed by `make repair`. `git diff` shows only
  the artifact. `--check` passes after repair.

**Phase 4 - Promote hand-written tables to generators.**
- Move `config_locationtypes.hpp`, `config_mapcolors.hpp`,
  `config_mapdisplays.hpp`, `config_mapicons.hpp` to read
  `data/symbology/terrain_symbols.json` (the memory records the palette is
  already sourced there).
- Move `species_table.sqf` and `sound_manifest.sqf` to read
  `data/wildlife/ecology.json` and `asset_map.json`.
- Each gains a `--check` and a manifest entry. Gate: `artifact_generation`
  passes because every generated artifact names its manifest entry.

**Phase 5 - Engine-truth detection.**
- In the Docker harness, run `conformance --check --truth-class engine` after
  the build, so a corpus that no longer matches the engine config is caught
  where the engine is present.
- Gate: a corpus drift against the engine is reported by the harness.

---

## Consequences

- One index describes the whole conformance surface. A new artifact is
  classified once, and CI enforces it from then on.
- `make lint` and CI cannot drift from each other or from the manifest, so
  the parity guard becomes total rather than pairwise.
- The 48 dormant test suites start gating. Their first run may surface real
  failures. That is the point.
- Repair becomes the default for the safe class, so a stale projection is
  fixed by one command instead of by a worker noticing.
- Cost: a manifest to maintain, and one new runner. The meta-gates pay this
  back by refusing unclassified additions.
- Risk: auto-repair can hide a semantic change. The convergence proof and
  the reviewable diff bound this. Repair only runs for the `auto` and `art`
  classes.

---

## References

- `Makefile` (lint target), `.github/workflows/ci.yml` (validate job).
- `tools/validation/check_lint_parity.py`.
- `tools/run_tests.py`.
- `tools/tests/test_suite_registration.py`, `tools/tests/test_adr_numbers.py`
  (the Phase 2 meta-gates landed with this record).
- `tools/tests/test_probe_numbers.py`, `tests/docker/verify.py`.
- `docs/adr/ADR-027-ownership-architecture.md`, ADR-001, ADR-011, ADR-017,
  ADR-030.
- `tools/gen_ownership_sentinels.py`, `tools/gen_extension_contract.py`,
  `tools/validation/gen_terrain_tables.py` (the `--check` pattern).
- `tools/tests/test_dump_state_contract.py` (the allowlist-with-reason
  pattern).
- Operator method: dynamic over static, matching over manually writing,
  finding instead of assuming.

---

## Appendix A - Manifest sketch

```json
{
  "schema": "aee.conformance.manifest/1",
  "entries": [
    {
      "id": "terrain_tables",
      "generator": "python3 tools/validation/gen_terrain_tables.py",
      "check": "python3 tools/validation/gen_terrain_tables.py --check",
      "artifacts": ["addons/optics/data/terrain_symbols.sqf"],
      "truth": "data/symbology/terrain_symbols.json",
      "truth_class": "corpus-in-repo",
      "repair": "auto"
    },
    {
      "id": "ownership_sentinels",
      "generator": "python3 tools/gen_ownership_sentinels.py",
      "check": "python3 tools/gen_ownership_sentinels.py --check",
      "artifacts": ["addons/core/data/ownership_sentinels.sqf"],
      "truth": "data/ownership/sentinels.json",
      "truth_class": "corpus-in-repo",
      "repair": "auto"
    },
    {
      "id": "extension_contract",
      "generator": "python3 tools/gen_extension_contract.py",
      "check": "python3 tools/gen_extension_contract.py --check",
      "artifacts": ["docs/wiki/research/extension-contract.md"],
      "truth": "addons/**",
      "truth_class": "repo-scan",
      "repair": "auto"
    },
    {
      "id": "app6_catalogue",
      "generator": "python3 tools/gen_app6_catalogue.py",
      "check": "python3 tools/gen_app6_catalogue.py --check",
      "artifacts": ["data/symbology/app6_catalogue.json"],
      "truth": "data/symbology/engine_markers.json",
      "truth_class": "engine",
      "repair": "detect-only"
    }
  ],
  "exempt": {
    "generators": {},
    "artifacts": {
      "addons/optics/config_curator.hpp": "hand-tuned Eden module list"
    }
  }
}
```

## Appendix B - Allowlist with reason (the house pattern)

```python
# addon or suite -> reason. An entry is a deliberate exemption. An empty
# allowlist means every discovered item must be registered.
ALLOWLIST = {
    "test_exhaust_shimmer": "needs the engine; runs in the Docker harness",
    "gen_designations": "one-shot ETL from national designation sources",
}
```
