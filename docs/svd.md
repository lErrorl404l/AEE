# Software Version Description

This description identifies one version of AEE. It follows the SVD content
of MIL-STD-498 and DI-IPSC. MIL-STD-498 is a United States standard. AEE
uses its document content as a reference. AEE cites no standard as a
certified status.

## 1. Version identity

| Field | Value | Source |
|---|---|---|
| Name | ACE Environment Extended | `mod.cpp`, `.hemtt/project.toml` |
| Prefix | `aee` | `.hemtt/project.toml` |
| Version source | `addons/lib/script_version.hpp` | `.hemtt/project.toml` `[version] path` |
| Version in source | 1.1.0.0 | `addons/lib/script_version.hpp` |
| Latest released version | 1.1.1 | `CHANGELOG.md`, tag `v1.1.1` |
| Version suffix | none (`git_hash = 0`) | `.hemtt/project.toml` |
| Protocol | 1 | `mod.cpp` |

The version in source is 1.1.0.0. The latest released version is 1.1.1.
The two disagree. The tag `v1.1.1` and the `CHANGELOG.md` section `[1.1.1]`
record the release. The source file was not bumped at that release. This
is a recorded defect, not a silent gap.

## 2. Configuration items

The version carries the software CIs named in `docs/cmp.md` section 2. The
addon tree holds 45 addons. The addon set is in
`docs/architecture/addon-map.json`.

## 3. Third-party components

The only third-party code is the vendored CBA header set under
`include/x/cba`. The header set is pinned to the CBA_A3 commit
`6b37925af487eda786ca360300b8fe48ae9c7e33`. The generator
`tools/make_sbom.py` reads that pin and writes a CycloneDX software bill of
materials.

The build toolchain is HEMTT. The AEE tooling uses the Python standard
library only.

## 4. Build

The build command is `hemtt build`. The release command is
`hemtt release`. The file `.hemtt/project.toml` sets the release to sign
and to archive. The release signs the PBO set with an ephemeral key. The
signing authority is `aee`.

The build output is a PBO set under `releases/`. The directory is not
tracked, because a build product is not a source.

## 5. Change set

The change set of a released version is the matching `CHANGELOG.md`
section. The format follows Keep a Changelog. The version numbering
follows Semantic Versioning.

The workflow `release-body.yml` copies the changelog section into the
published release body on a `v*` tag. The changelog is the source of truth
for the release notes.

## 6. Related records

- `CHANGELOG.md` - the change set of each version.
- `docs/release-records/README.md` - the release process.
- `docs/release-records/` - one baseline record per release.
- `docs/cmp.md` - the Configuration Management Plan.
