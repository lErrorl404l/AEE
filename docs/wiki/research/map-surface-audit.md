# Map-surface audit

The AEE topographic surface is one include, `addons/cartography/config_mapcolors.hpp`.
Three map controls carry it. Other map displays keep their own control and
override part of the palette. This record states where the AEE surface reaches
and where it stops. The live probe `P142` reads the merged config on every
surface named here.

Source of the AEE values: `addons/cartography/config_mapcolors.hpp`.
Source of the engine overrides: the vanilla `Addons/ui_f.pbo` config.

## The AEE field set

| Field | AEE value | Source |
|---|---|---|
| `colorBackground` | `0.90, 0.88, 0.80, 1` | FM 21-31; USGS |
| `colorSea` | `0.55, 0.70, 0.85, 1` | DGIWG water blue |
| `colorForest` | `0.55, 0.74, 0.44, 1` | FM 21-31; DGIWG green |
| `colorMainCountlines` | `0.45, 0.26, 0.12, 1` | FM 21-31 brown |
| `colorCountlines` | `0.62, 0.42, 0.22, 1` | FM 21-31 brown |
| `maxSatelliteAlpha` | `0.5` | AEE model choice |
| `drawShaded` | `0.15` | Enhanced Map idea |
| `shadedSea` | `1` | Enhanced Map idea |
| `sizeExLevel` | `0.04` | doubled from the vanilla `0.02` |
| `colorGrid`, `colorGridMap` | alpha `0` | engine grid off; AEE MGRS is the ruler |
| `sizeExGrid` | `0.04` | AEE MGRS label size |

## Reach per surface

| Surface | Config class | AEE re-declare | Engine override | AEE reach |
|---|---|---|---|---|
| Main map, briefing, GPS | `RscMapControl` | `config.cpp:65` | none | All eleven fields. |
| Strategic map | `RscDisplayStrategicMap >> controlsBackground >> Map` | `config_mapdisplays.hpp:22` | its own class re-declares the surface | All eleven fields. |
| Eden map | `ctrlMap` | `config_mapdisplays.hpp:39` | `ctrlMapMain` and `ctrlMapEmpty` inherit | All eleven fields. |
| Curator map | `RscDisplayCurator >> ControlsBackground >> Map` | none; inherits `RscMapControl` | none found | Full. The probe reads `maxSatelliteAlpha=0.5`, `drawShaded=0.15`, `shadedSea=1`, `sizeExLevel=0.04` and grid alpha `0`, all the AEE values. |
| Minimap | `RscCustomInfoMiniMap >> controls >> MiniMap >> Controls >> CA_MiniMap` | none | `colorBackground`, `colorSea`, `colorForest`, `colorMainCountlines` (alpha 0.6), `colorCountlines` (alpha 0.2), `maxSatelliteAlpha` (0), `drawShaded` (0.1), `colorGrid` (alpha 0.3), `alphaFade*`, `ptsPerSquare*` | Partial. The engine override wins for the fields it names. Only `shadedSea` and `sizeExLevel` inherit the AEE surface. |
| Airborne minimap | `RscCustomInfoAirborneMiniMap >> controls >> MiniMap >> Controls >> CA_MiniMap` | none | the minimap set plus its own `colorSea`, `colorForest`, `drawShaded` and the altitude ramp | Partial, as the minimap. |

The briefing map and the GPS panel inherit `RscMapControl`, so they read the
same config entry. The probe asserts the `RscMapControl` values once and
records that the two displays inherit them.

## The marker set

`CfgMarkers >> AEE_FL_Friendly_Unit_Infantry` resolves. It is one class of the
real Commons-derived APP-6 set under `addons/symbology/data/markers/`. The
AEE marker-apply function `aee_symbology_fnc_symbologyMarkersApply` is
compiled at load. Its `disableMapIndicators [true, true, true, true]` call is
pinned at `tools/tests/test_symbology.py:623`.

## The gap

AEE does not re-declare the minimap or the airborne minimap. The engine keeps
its own sea and forest fill and its satellite fade on those two displays. The
engine minimap surface is the subject of a later todo in the plan
(`aee-map-realism-polish.md`, todo 10).
