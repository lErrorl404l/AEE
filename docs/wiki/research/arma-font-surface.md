# Arma 3 Font Surface and the AEE Font Register

This register records the engine font surface and the AEE font choice. The
AEE symbology layer draws labels on the map, in the 3D view and on the HUD.
Each label names a font. This register records what the engine accepts, what
AEE ships and what AEE cannot ship.

Grade key:

- **S** sourced to a shipped config or a published page.
- **R** derived by a formula or a tool run from a sourced value.
- **U** unsourced. It is stated so the register holds it.

Sources are listed at the end. The shipped engine config was read from this
machine under `/ext/SteamLibrary/steamapps/common/Arma 3/`.

## 1. The engine font surface

| Item | Fact | Grade |
|---|---|---|
| Font class | Arma 3 uses `CfgFontFamilies`. | S |
| `CfgFonts` | `CfgFonts` exists as a named class. It is an empty stub. Do not use it. | S |
| `fonts[]` | One entry per point size. An entry is a path string, or a three-element array of Latin, CJK and fallback paths. The path has no extension. | S |
| `spaceWidth` | Optional. It sets the space glyph width. `spacing` also exists. Only one shipped family sets them. | S |
| Converted format | The engine loads a `.fxy` glyph index plus one or more `.paa` glyph atlases. It does not load a `.ttf` or a `.otf` at run time. | S |
| Atlas format | The `.paa` glyph atlases are DXT5. They set `Max Color: FFFFFFFF` and `AlphaFlag: 1`. | S |
| `FontToTGA` route | The official tool converts an installed TTF into a `.tga` sheet set plus a `.fxy`. It is a Windows application in Arma 3 Tools, Steam app 233800. | S |
| `hemtt utils paa convert` route | `hemtt utils paa convert <src> <dest>` converts an image to a PAA. A TGA input is accepted. An alpha input yields a DXT5 PAA. The command is in-repo, on Linux and in CI. | R |
| Apply keys | A control sets `font` to a `CfgFontFamilies` class name and `sizeEx` to a text height. | S |
| Map grid labels | `RscMapControl` exposes `fontGrid` and `sizeExGrid`. A mod repoints the grid labels by overriding the class in its config. | S |
| Runtime command | The command is `ctrlSetFont`. Its parameter is a `CfgFontFamilies` class name. No `setFont` command exists. | S |
| `drawIcon` | The `font` parameter is a `CfgFontFamilies` class name. | S |
| `drawIcon3D` | The `font` parameter is a `CfgFontFamilies` class name. | S |
| Fixed-size ceiling | Fonts are bitmap atlases. They do not scale. One `.fxy` plus `.paa` set exists per point size. A custom family renders only at the sizes generated. | S |
| Character set | A `.fxy` holds Latin `x20` to `x17F`, Cyrillic `x400` to `x45F` and specials `x2010` to `x201F`. Any glyph not generated is missing. MGRS uses A to Z and 0 to 9, so this ceiling does not bite the MGRS readout. | S |
| `.fxy` structure | The `.fxy` structure is officially undocumented. Build it only with `FontToTGA`. | S |
| Grid font at run time | No script command repoints `fontGrid`. It is a load-time config override only. | S |

The shipped family block has this shape.

```cpp
class CfgFontFamilies {
    class AEEFont {
        fonts[] = {
            {"aee\\data\\fonts\\AEEFont9",  "aee\\data\\fonts\\cjk9",  ""},
            {"aee\\data\\fonts\\AEEFont10", "aee\\data\\fonts\\cjk10", ""}
        };
        spaceWidth = 0.9;
    };
};
```

## 2. The AEE font choice

AEE ships two freely licensed families. Each family is SIL OFL 1.1. The
licence text ships beside the font.

| Family | Use | Designer | Licence | Official source | Shipped OFL text |
|---|---|---|---|---|---|
| Rajdhani | HUD and map labels | Indian Type Foundry | SIL OFL 1.1 | fonts.google.com/specimen/Rajdhani | `addons/cartography/data/fonts/rajdhani/OFL.txt` |
| B612 Mono | MGRS coordinate readout | Airbus, polarsys | SIL OFL 1.1 | github.com/polarsys/b612 | `addons/cartography/data/fonts/b612mono/OFL.txt` |

Rajdhani reads as military and technical signage. It is condensed and it has
five weights. It covers A to Z, 0 to 9 and punctuation, so it covers the
MGRS letters and digits.

B612 Mono is a cockpit display face with a monospaced twin. A monospaced
face keeps the coordinate columns steady as the digits change.

OFL 1.1 clause 2 permits a bundle and a format change. A TTF to `.fxy`
conversion is therefore permitted. Neither family declares a Reserved Font
Name. Keep the copyright notice and the OFL text with the shipped font.

## 3. The conversion procedure

The engine needs a `.fxy` and a `.paa` set. AEE cannot produce these in this
repository. The `FontToTGA` step is a Windows GUI application. It is the one
operator step. Until the operator runs it, the engine keeps its default
font.

Procedure:

1. On Windows, run `FontToTGA` on the source TTF. Generate the `.fxy` and
   the `.tga` sheet set for each point size the family needs. The GUI
   generates sizes 6 to 31, 34, 35, 37 and 46.
2. For each `.tga` sheet, run this command on Linux:

   ```
   hemtt utils paa convert <name>.tga <name>.paa
   ```

   The command writes a DXT5 PAA when the sheet carries an alpha channel. A
   font sheet carries an alpha channel, so the output is DXT5.

3. Place the `.fxy` and the `.paa` set under `addons/cartography/data/fonts/`.
   The `CfgFontFamilies` paths in `addons/optics/config.cpp` point at them
   with no extension.

`hemtt utils paa compress` is optional. It reduces the size of an
uncompressed PAA. `hemtt utils paa convert` writes an uncompressed PAA by
default. `hemtt utils paa cxam-fix` repairs a wrong `CXAM` tag. A fresh
`convert` writes a correct `CXAM` tag, so `cxam-fix` is not needed here.

Probe evidence: a 32-bit TGA with alpha converted to a DXT5 PAA, and
`hemtt utils paa inspect` reported `Format: DXT5`. See the task 12 evidence
file.

## 4. What AEE ships and what AEE does not

AEE commits the source TTF and the OFL text for each family. AEE does not
commit a `.fxy`, a `.tga` or a `.paa`. Those files need the operator step in
section 3, so AEE cannot produce them here.

The wiring in `addons/optics/config.cpp` names the `AEEFont` and
`AEEFontMono` families. The draw code names the family when the family
exists and the `symbologyFont` setting is on. The engine falls back to its
default font when the family is unavailable. The default font is the
zero-risk state.

## Sources

Shipped Arma 3 config, read on this machine:

- `Dta/bin.pbo` >> `config.cpp:9326` (`CfgFontFamilies`), `:9335`
  (`CfgFonts` stub), `:19764-19765` (`fontGrid`).
- `Addons/uifonts_f.pbo` >> `config.cpp:12` (the main family set).
- `Addons/ui_f.pbo` >> `config.cpp:1324-1325` (`fontGrid`).

Published pages, read through the Wayback Machine because the live site
returns HTTP 403:

- FXY File Format.
- FontToTga.
- ctrlSetFont.
- drawIcon.
- drawIcon3D.

Font licences, verified from the upstream `google/fonts` `OFL.txt` files:

- `raw.githubusercontent.com/google/fonts/main/ofl/rajdhani/OFL.txt`.
- `raw.githubusercontent.com/google/fonts/main/ofl/b612mono/OFL.txt`.
