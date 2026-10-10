# ADR-029: Derive the engine marker mapping from the engine config

Status: Accepted (2026-10-08)

## Context

The AEE map marker layer re-textures the engine's own `CfgMarkers` classes so
the vanilla `b_`/`o_`/`n_` markers render the APP-6 symbol. The first cut
re-declared each engine class as a bare `class b_inf { icon = ...; texture =
...; };`. The operator reported two symptoms from a live run: the friendly
markers fell under the Unknown category, and the re-pointed base markers
defaulted to a wrong or unknown symbol.

A live RPT (`Arma3_x64_2026-10-08_17-51-36.rpt`) showed the cause:

* 117 `Warning Message: No entry 'bin\config.bin/CfgMarkers/<class>.scope'`.
* For every engine family: `Updating base class 'b_unknown'->'', by
  'z\aee\...\CfgMarkers/b_inf/' (original 'a3\ui_f\config.bin')`.

A bare reopen sets the class parent to nothing, so the engine discards every
inherited value (scope, size, colour, markerClass). The marker then has no
scope for the picker and no category. Separately, the category generator keyed
the affiliation map on `"Friendly"` while the catalogue stores `"Friend"`, so
`marker_category("Friend", ...)` fell through to Unknown.

## Decision

1. Derive the map. The engine's own `CfgMarkers` tree is resolved once from
   the installed game config and committed to
   `data/symbology/engine_markers.json` (the `class_parents.json` pattern).
   The three engine configs that define the touched classes are read:
   `a3\ui_f`, `a3\ui_f_enoch` and `a3\missions_f_heli`. Resolve with
   `python3 tools/gen_symbology_catalogue.py --resolve-engine <config.cpp>...`.

2. Restate the real parent. Every re-declared engine class is emitted as
   `class <cls>: <real parent> { icon = ...; texture = ...; };` so the
   inherited scope, size, colour and markerClass survive and only the texture
   is AEE's. A class the engine config records with no parent is emitted bare;
   that is the only bare form allowed.

3. Classify from the catalogue. Each AEE runtime family alias
   (`AEE_<family>_<glyph>`, returned by `fnc_symbologyMarkerType`) inherits the
   real APP-6 catalogue symbol that resolves to the same affiliation,
   dimension and function. The `markerClass` of every catalogue marker is
   `marker_category(affil, dim)` of its own catalogue row, so the Friendly
   markers carry `AEE_Friend_*`, never Unknown.

4. Real textures only. Every AEE marker texture is a `.paa` under
   `addons/symbology/data/markers`. No AEE marker points at an engine texture.

5. No invented engine classes. Engineer, signal and supply are not engine
   classes (`b_eng`/`b_sig`/`b_sup` do not exist in any engine config). They
   are AEE runtime family aliases, not engine overrides.

## Consequences

* The engine marker picker keeps the vanilla scope, size, colour and category
  for every re-pointed class; the load log carries no
  `Updating base class ...->''` and no `No entry ...scope`.
* The mapping is reproducible: `--check` fails when the emitted config drifts
  from the cache and the catalogue, and `tools/tests/test_marker_derivation.py`
  fails on a bare reopen, a markerClass that disagrees with its catalogue row,
  or a texture that is not a real `data/markers` file.
* `docs/wiki/research/marker-mapping-register.md` records, per engine class,
  its real parent and the symbol it is pinned to, with every deviation and the
  reason.
* Live probe P119 (`aee_p119_marker_inheritance_probe.sqf`) asserts, on the
  merged config, that the engine classes keep a non-zero scope, draw a real
  AEE texture, and that the friendly markers carry `AEE_Friend_Land`.

## Ceiling

The engine still owns the marker geometry, the picker order and any class AEE
does not re-declare (for example the national flags `flag_`, the location
markers `loc_`, and `Empty`/`EmptyIcon`). AEE re-points the icon only.
