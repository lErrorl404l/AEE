# Symbology catalogue schema

The catalogue is `data/symbology/nato_catalogue.json`. It records one NATO /
APP-6 map symbol per entry, with its affiliation, battle dimension, function,
frame, licence, author and source URL. `data/symbology/dropped.json` records
every image the first pull admitted and this corpus rejected, with the reason.

The catalogue publishes the extracted data and its citations. It does not
publish the captured drawings or the renders: they belong to their uploaders.

## What the cache holds

The bytes live in the machine-local source cache that
`tools/validation/source_cache.py` names, normally
`$HOME/.local/share/aee/source-cache/symbology/`:

| Path | Count | What it is |
|---|---|---|
| `svg/ccbysa/` | 917 | Wikimedia Commons traces, CC BY-SA 4.0 |
| `svg/ccby/` | 3 | Wikimedia Commons traces, CC BY 2.0 |
| `svg/pd/` | 172 | Public-domain traces |
| `render/` | 903 | The held 64 px RGBA canvas for each marker `.paa` |

`data/symbology/sources/` holds no capture. Only JSON may be tracked under a
`sources/` directory, and `tools/tests/test_source_capture_policy.py` fails,
naming the path, when a tracked file has any other extension.

The generator `tools/gen_symbology_catalogue.py` maps one entry to one marker
name. Its `--check`, `--verify-svg` and `--render` modes read the cache and
report a skip when the cache is absent, so a clean clone passes.

## Why the renders are held

The render is not reproducible across machines.

1. librsvg encodes the same pixels into different PNG bytes, so a byte compare
   of a render crosses no version. The shipped `.paa` were cut with librsvg
   2.62.4. No distribution ships 2.62.4 (Debian forky ships 2.62.1, Ubuntu
   25.10 and Debian trixie ship 2.60.0, Ubuntu 24.04 ships 2.58.0).
2. 166 of the source drawings carry `<text>` with a `font-family`. The glyph
   then depends on the installed font. The machine that cut the textures
   resolves `sans-serif` to Noto Sans. A bare runner resolves it to DejaVu
   Sans, and 162 of 903 markers differ.

The renderer stack can therefore not be pinned exactly. The render OUTPUT is
pinned instead. The held 64 px canvas is the source of truth for the texture,
and a machine that holds the cache reproduces each `.paa` from it byte for
byte with no renderer dependency. The SVG to render step is proved
structurally by `--verify-svg`.

## Licence

The symbol designs are a standard. MIL-STD-2525 is a US Government work and
NATO APP-6 is its equivalent, so the frame shapes and the function glyphs are
not owned. The licence tag on each file is the uploader's licence on their own
SVG trace. Each converted `.paa` of a CC BY-SA file remains CC BY-SA 4.0. AEE
is GPL-2.0-or-later, and CC BY-SA 4.0 is one-way compatible with GPLv3, so the
combined distribution is GPLv3 by the "or later" route. The per-asset
attribution is written to `addons/symbology/data/markers/ATTRIBUTION.md`.

## Commands

```sh
# Cut each .paa from the held render, and check it byte for byte.
python3 tools/gen_symbology_catalogue.py --check

# Prove each held render is the render of its held source SVG.
python3 tools/gen_symbology_catalogue.py --verify-svg

# Re-cut the held renders from the held source SVGs.  This is the only step
# that needs rsvg-convert and the render font, so it runs on the machine that
# cuts the textures.
python3 tools/gen_symbology_catalogue.py --render
```

The render command is:

```sh
rsvg-convert -w 256 -h 256 --keep-aspect-ratio -o OUT.png IN.svg
```

The generator then reduces the 256 px render to a 58 px art box on a 64 px
transparent canvas. It keeps the source's own colours, because the frame
carries the affiliation colour and the glyph stays black.
