# Release process

This directory holds the release records. One file per release records the
baseline. The release archive itself is not tracked. The directory
`releases/` holds the build output and stays out of git.

## 1. Baseline

A release baseline is a signed tag on `main`. The tag name is `v<version>`.
The version follows Semantic Versioning. The change set follows Keep a
Changelog.

The version lives in `addons/lib/script_version.hpp`. HEMTT reads that
file, because `.hemtt/project.toml` names it in `[version] path`.

## 2. Steps

1. Merge every intended change to `main`.
2. Set the version in `addons/lib/script_version.hpp`.
3. Move the `CHANGELOG.md` entries under the new version heading.
4. Run the gate set. Every gate must exit 0.
5. Commit the version and the changelog together.
6. Tag the commit with a signed tag: `git tag -s v<version>`.
7. Push the commit and the tag.
8. Run `make release`. HEMTT builds, signs, and archives the PBO set.
9. Write the baseline record in this directory.

The release command reads `.hemtt/project.toml`. The section
`[hemtt.release]` sets `sign = true` and `archive = true`. The release
signs the PBO set with an ephemeral key. The signing authority is `aee`.

## 3. Gate set

| Gate | Command |
|---|---|
| Build check | `hemtt check -p -e` |
| Local gate set | `make lint` |
| Unit and physics | `python3 tools/run_tests.py --fast` |
| Oracle validation | `python3 tools/validation/validate_oracles.py` |
| Library audit | `python3 rules/audit.py` |

A gate that fails blocks the release. A recorded deviation is the only
exception. A deviation names the reason and the review date.

## 4. Automated release records

Three workflows support the release.

- `release-body.yml` copies the `CHANGELOG.md` section into the published
  release body on a `v*` tag. The changelog is the source of truth for the
  release notes.
- `sbom.yml` generates a CycloneDX software bill of materials with
  `tools/make_sbom.py` and uploads it as an artefact.
- `publish.yml` renders and deploys the wiki under `docs/wiki/`.

## 5. Baseline record format

A baseline record names the version, the tag, the date, the change set,
and the audit evidence.

| Field | Holds |
|---|---|
| Version | The version in `script_version.hpp`. |
| Tag | The signed tag. |
| Date | The release date. |
| Change set | The `CHANGELOG.md` section. |
| Functional audit | The test and validation result at the tag. |
| Physical audit | The built version against the version file and the SBOM. |

## 6. Records

| Version | Record |
|---|---|
| 1.1.1 | [v1.1.1.md](v1.1.1.md) |
