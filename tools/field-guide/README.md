# Field-guide extraction harness

This directory holds the tools that build the field-guide corpus and the
generated citation index.

## `extract.py`

`extract.py` reads the cited corpus from the game install. It names each
source by its PBO and entry, never by a path on one machine. It writes a
scratch tree and `manifest.json`.

The game install root comes from `ARMA3_GAME_ROOT`. The scratch tree comes
from `AEE_FG_SCRATCH`, default `/tmp/opencode/fg-scratch`.

Run from the repo root:

```bash
export ARMA3_GAME_ROOT="/path/to/Arma 3"
python3 tools/field-guide/extract.py build        # write manifest.json
python3 tools/field-guide/extract.py --check      # re-run and compare
```

Modes:

| Mode | Action |
|---|---|
| `build` | Build `manifest.json` from the target list. |
| `--check` | Re-run the extraction and report drift against `manifest.json`. |
| `pbo <pbo> <entry>` | Extract one entry and print its byte size. |
| `derapify <pbo> <entry>` | Derapify a config entry to the scratch tree. |
| `strings <binary> <regex>` | Count the distinct matching strings. |
| `decomp <binary> <function>` | Decompile one named function. |

The `decomp` mode uses the targeted `r2` route (`s <addr>; af; pdg`). A full
`decomp -a` on the engine binary is too slow, so the tool never runs it.

The target list is the cited corpus. `manifest.json` records the PBO, the
entry, the byte size, the line count, the content hash and the extraction
command for each target. `--check` compares the live extraction with the
record and exits non-zero on drift.

## `citations.py`

`citations.py` reads every field-guide page, collects the `{src:<kind>:<ref>}`
tokens and the `## Sources` rows, and writes
`docs/wiki/field-guide/citations.qmd`.

```bash
python3 tools/field-guide/citations.py            # write the index
python3 tools/field-guide/citations.py --check    # compare, no write
```

The `--check` mode is registered in the `Makefile` lint target and CI. The
`extract.py` modes are not, because they need the game install.
