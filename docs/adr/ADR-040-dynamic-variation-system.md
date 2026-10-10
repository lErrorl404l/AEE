# ADR-040: The dynamic variation system

## Status

Accepted.

## Context

AEE resolves a symbol from five axes through `fnc_symbolResolve`, and generates
every concrete marker from `data/symbology/symbology_tables.json`. The marker
picker therefore showed a flat list of thousands of AEE variants. The operator
asked for ONE option-driven entry with an in-game switch, in place of the flat
list. The idea comes from AceArsenalExtended's `XtdGearModels` config; AEE
reimplements the idea in its own shape and copies none of it.

## Decision

A variation family declares named options and one resolver. AEE shows the family
as ONE engine entry and the operator switches the active value in game. The
option values are DERIVED from the shipped tables by
`tools/gen_variation_families.py`, so a new symbol in a shipped table becomes a
new option value with no hand-editing. The declaration is
`data/symbology/variation_families.json` (schema
`aee.symbology.variation_families/1`).

The marker application:

- The family entry `AEE_Variation` is one `CfgMarkers` class with `scope = 2`.
- The AEE-produced concrete variants move to `scope = 0` through the one flag
  `VARIATION_HIDDEN_SCOPE` in `tools/symbology_categories.py`, so the picker
  shows the family entry. Probe P143 proves a scope-0 class still places through
  `setMarkerTypeLocal`, so the collapse is safe. The flag reverts the collapse in
  one line.
- The engine re-point classes restate their engine parent and set no scope, so
  they inherit scope 2 and stay picker-visible.

The in-game switch: a CBA keybind (category AEE) opens the generated
`RscDisplayAEEVariation`; five CBA LIST settings under AEE HUD > Symbology are
the headless and no-UI route. The settings are the source of truth and the
dialog writes through to them, so the two never diverge. A change re-types the
placed `AEE_Variation` markers live through `fnc_variationApply`, client-local
only. `fnc_symbolResolve` and `fnc_symbologyMarkerType` are unchanged and stay
the single source of truth for the symbol.

## Consequences

- The picker shows ONE option-driven AEE entry; the concrete variants are hidden
  but still script-resolvable.
- The resolver only selects the inputs to `fnc_symbolResolve`; it duplicates no
  composition.
- The active variation is a single global state per family. Per placed marker
  variation is a later enhancement.

## The engine surface and the ceiling

The surface is real: `CfgMarkers` scope, `CfgMarkerClasses`, `createDialog` /
`RscDisplay` / `displayCtrl`, `setMarkerTypeLocal` / `setMarkerColorLocal`, CBA
keybinds and CBA settings. The engine marker picker is fixed: a mod cannot group
N classes under one entry, so the collapse is achieved by scope, not by a picker
API. A headless server renders no picker and no dialog, so the visible picker,
the dialog look and the live keybind switch are operator-only rows.

## The licence boundary

AEE is GPL-2.0-or-later. The marker art is the real Commons-derived APP-6 set,
unchanged, attributed in `addons/symbology/data/markers/ATTRIBUTION.md`. The
AceArsenalExtended mechanism is reimplemented from its idea only: arsenal is
GPL-2.0, gearinfo and ingame are MIT, and no code, config or art is copied.
