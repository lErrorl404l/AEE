# ADR-029: Map legibility - location inheritance, object names, grid reference and MGRS contrast

Status: Accepted

## Context

The operator reported four map defects on a live run:

1. Terrain markers such as water towers and radio towers "stay the same and
   are not updated".
2. The map texture and contour treatment does not match the two mods the
   operator named, Enhanced Map (2467589125) and BHC Map Contour (1364777346).
3. The vanilla grid reference is gone.
4. The AEE MGRS lines are grey and very hard to see.

A live RPT also showed a fifth defect. For each engine location class it
logged, 128 times:

```
Warning Message: No entry 'bin\config.bin/CfgLocationTypes/NameCityCapital.drawStyle'
Warning Message: '/' is not a value
Wrong location draw style - ""
```

## Decision

### Defect 1 - the water towers and the radio towers

Root cause. The engine declares the `RscMapControl` object icon classes in two
name sets that differ in case for eight of them. The engine core,
`Dta/bin.pbo` (`bin_raw/bin/config.cpp:20264`), names them `Church`,
`Lighthouse`, `Quay`, `Fuelstation`, `Hospital`, `BusStop`, `Transmitter` and
`Watertower`. `ui_f.pbo` (`ui_f_x2/config.cpp:1458`) uses the lowercase forms.
Arma config class names are case sensitive, so the two sets are distinct
classes and the engine's object routing reads one of them. AEE re-declared
only the `ui_f` set, so an object the engine routes through the core name kept
its vanilla icon.

Fix. `addons/optics/config_mapicons.hpp` re-declares the eight engine-core
names with the same AEE topographic texture, beside the eight `ui_f` names.
The re-texture now reaches the object whichever name the routing uses.
Source: the engine configs, read from `Dta/bin.pbo` and `ui_f.pbo`.

### Defect 2 - the location classes lose their inherited values

Root cause. `config_locationtypes.hpp` re-declared each class with a bare
`class <cls> { ... }`, which invokes the engine Empty syntax and drops the
`drawStyle`, the base `texture` and every other value the class inherited from
its parent. That produced the RPT warnings above.

Fix. Every re-declared class restates its vanilla parent, read from the
engine's own config. The parent graph is: `Mount` and `Name` are the two
parentless roots. `Strategic` derives from `Name`. `StrongpointArea`,
`FlatArea`, `CityCenter` and `Airport` derive from `Strategic`. `FlatAreaCity`
derives from `FlatArea` and `FlatAreaCitySmall` from `FlatAreaCity`.
`NameMarine`, `NameCityCapital`, `NameCity`, `NameVillage`, `NameLocal` and
`fakeTown` derive from `Name`. `Hill` derives from `Name`. `ViewPoint`,
`RockArea`, `BorderCrossing`, the four vegetation classes and `Flag` derive
from `Hill`. `Area` is parentless. The three parentless roots stay bare, as
`ui_f` declares them, because they have no parent to restate.

### Defect 3 - the grid reference and the MGRS contrast

Root cause. ADR-028 removed the engine numeric grid on every map target to
leave exactly one grid, the AEE MGRS overlay. The MGRS overlay then drew light
cyan at alpha 0.30 on a light map, so the operator read no grid reference and
the lines looked grey.

Decision - how the two grids coexist. The engine numeric grid supplies the
NUMBERS and the AEE overlay supplies the LINES.

- The engine numeric LINES stay off: `colorGrid[]` and `colorGridMap[]` keep
  alpha 0 on `RscMapControl`, `RscDisplayStrategicMap >> controlsBackground >>
  Map` and the Eden `ctrlMap`.
- The engine NUMBERS return: `sizeExGrid` returns to the engine default 0.02
  on the same three targets. That is the familiar vanilla numeric grid
  reference the operator asked for.
- The AEE MGRS overlay is the only line grid, and its linework is now DARK and
  high contrast: the minor line is `{0.08, 0.08, 0.10, 0.55}`, the major line
  `{0.03, 0.03, 0.05, 0.90}`, and the labels `{0.05, 0.05, 0.05, 1}`. The old
  light cyan at alpha 0.30 read as grey. The dark colour matches the map label
  colour `colorNames` `{0.10, 0.10, 0.10, 0.90}`. Source: AEE's own palette.

The player, marker and cursor labels use the same dark colour.

### Defect 4 - the map texture and contour treatment

AEE adopts the IDEAS of the two named mods. It copies no mod config, config
value, texture or code.

- `maxSatelliteAlpha` moves from 0.35 to 0.5. The idea is the operator's
  (both mods expose the lever). Enhanced Map uses 1.0 and BHC Map Contour uses
  0.5. The number is AEE's own, between AEE's old 0.35 and the Enhanced Map
  1.0, so the satellite reads while the MGRS linework stays legible.
- `drawShaded` is 0.15. That is the Enhanced Map idea, a small hillshade for
  the topographic look. It is a real `RscMapControl` field
  (`ui_f_x2/config.cpp:50344` sets it on the minimap override). The value is
  AEE's own.
- The contour colours stay AEE's standard brown (FM 21-31). The mods use
  ad-hoc colours with no standard, so AEE does not copy them.

## Ceilings

- The object-to-icon routing is engine-internal. No config field names the
  mapping. Bohemia ticket T157884 records that a custom object map icon does
  not show even when `RscMapControl` is updated, so a re-texture reaches only
  an object the engine already routes to a class. AEE covers both engine name
  sets and no more.
- `CfgLocationTypes` `drawStyle` is a fixed enum (`name`, `icon`, `area`,
  `mount`). A mod changes the texture, colour, size, font, shadow and
  importance only.
- The engine grid numbers have no separate config colour field. AEE restores
  `sizeExGrid` and keeps `colorGrid` alpha 0.
- The contour geometry and the contour interval are engine-derived from the
  elevation data. No config field sets either.
- The satellite land texture is baked into the map layers. Only
  `maxSatelliteAlpha` and `drawShaded` temper it.
- `shadedSea` is not set. The base `RscMapControl` does not carry it and AEE
  has no verified source, so AEE leaves it to the engine.

## Consequences

- The RPT no longer logs `No entry CfgLocationTypes/*` or `'/' is not a
  value`.
- The operator reads the engine numeric grid reference beside the AEE MGRS
  line grid.
- The AEE MGRS linework reads against the light topographic ground.
- `tools/tests/test_terrain.py` locks the inheritance, the object names, the
  grid contract and the MGRS contrast. The live probe `aee_p121` reads the
  merged config. `aee_p117` defect 1 now asserts lines off and numbers on.
