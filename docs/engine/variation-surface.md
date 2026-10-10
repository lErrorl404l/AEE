# The AEE dynamic variation surface

The mechanism is general. A family declares named options. One resolver maps a
selected value combination to one concrete artifact. AEE shows the family as ONE
engine entry, and the operator switches the active value in game. The marker
family is the first user; the generalisation is recorded in
[variation-model.md](variation-model.md) and in the reuse section below.

## The engine surface

| Surface | Real engine fact |
|---|---|
| `CfgMarkers` `scope` | 0 hides a class from the picker, 2 shows it.  A hidden class still places through `setMarkerTypeLocal` (probe P143). |
| `CfgMarkerClasses` | The picker groups.  `AEE_Variation` is the one visible AEE group the family adds. |
| `createDialog` / `RscDisplay` | The selector is `RscDisplayAEEVariation`, opened by a CBA keybind. |
| `setMarkerTypeLocal` / `setMarkerColorLocal` | The apply layer re-types a marker client-locally.  No global marker command is called. |
| CBA keybind | Category "AEE" opens the selector. |
| CBA LIST settings | Five settings under AEE HUD > Symbology are the headless and no-UI route. |

## The picker collapse

`tools/gen_variation_families.py` and the four marker generators emit the
AEE-produced concrete variants at `scope = 0` through the one flag
`VARIATION_HIDDEN_SCOPE` in `tools/symbology_categories.py`. The engine
re-point classes restate their engine parent and set no scope, so they stay
picker-visible. Set the flag to 2 to revert the collapse in one line.

## The operator-only rows

These need one operator run each. A headless server renders no picker and no
dialog, so the probe cannot prove them.

1. **The visible picker collapse.** Open the editor marker picker: it lists ONE
   AEE group (`AEE Symbol`, the `AEE_Variation` entry) in place of the flat AEE
   variant list. Probe P143 proves a hidden-scope class still places, so the
   collapse is safe; the visual result is operator-only.
2. **The selector dialog look.** Open the map and press the AEE Variation
   Selector keybind: `RscDisplayAEEVariation` shows one row per option, one
   button per value, the active value highlighted. The layout is operator-only.
3. **The live keybind switch.** With an `AEE_Variation` marker placed, select a
   different value in the dialog: the marker re-types live. Probe P143 proves
   the re-type for each of the five option states; the visible result is
   operator-only.

## The ceiling

- Per placed marker variation is a later enhancement. The active variation is a
  single global state per family.
- The engine marker picker is fixed: a mod cannot group N classes under one
  entry. The collapse is achieved by scope, not by a picker API.
- A headless server renders no picker and no dialog.
