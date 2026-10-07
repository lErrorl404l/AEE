# ADR-023: MGRS and positioning - the sourced anchor, the MGRS kernel and the tracker ceiling

Status: Accepted

## Context

Arma 3 has no native MGRS. The engine draws the map grid as numbers only.
The vanilla GPS readout is engine-hardcoded. Before this change AEE read one
latitude in one place, and no longitude and no zone at all. The shipped world
keys are not always correct. Altis ships a stale latitude of 35.152 N and a
stale longitude of 16.661 E, while its `mapArea[]` box gives a true centre of
39.906515 N and 25.246742 E.

Two work items followed. First, a sourced geographic anchor and a real MGRS
conversion layer. Second, an honest tracker. The tracker carries satellite
error, canopy and urban degradation, jamming, fix lag and datalink falloff.
It replaces the exact arcade position.

The conversion needs published standards. The projection uses DMA TM 8358.2
with the WGS84 ellipsoid of NIMA TR8350.2. The letter tables use DMA TM 8358.1
and the NGA MGRS guidance of 2009. The GNSS error uses the GPS Standard
Positioning Service Performance Standard, 5th edition, April 2020 (gps.gov).

## Decision

### The geographic anchor

One pure builder, `fnc_buildGeoAnchor`, takes the raw world values and returns
a stable 9-element anchor. One reader, `fnc_getGeoAnchor`, reads `mapArea[]`,
`mapSize` and `mapZone` from `CfgWorlds`, falls back to the `latitude` and
`longitude` keys, caches the result and publishes `aee_core_geoAnchor`.

The `mapArea[]` element order is `[lonWest, latSouth, lonEast, latNorth]`.
The BIS file `fn_posDegtoWorld.sqf` proves the order. The reader corrects the
BIS latitude sign, because the raw key marks positive as south. A box is
usable only when it holds four numbers that form a positive-area rectangle
inside valid geographic bounds. Tanoa stores latitude in the longitude slots.
Enoch ships an empty box. Both fall back to 40 N and 0 E.

### The MGRS kernel

`fnc_latLonToUtm` and `fnc_utmToLatLon` are pure and argument-driven. They use
the transverse Mercator series of DMA TM 8358.2, the WGS84 ellipsoid
(a = 6378137 m, 1/f = 298.257223563), k0 = 0.9996, false easting 500000 m and
false northing 10000000 m in the south.

`fnc_formatMgrs` emits the zone, the band, the 100 km square and the digits.
`fnc_parseMgrs` reverses it. The band letter is a function of latitude, so the
format kernel takes the latitude as a fifth argument. The digits are
truncated, and they label the south-west corner of the square. The letter
tables are generated into `addons/core/data/mgrs_tables.sqf`. The generator
`tools/validation/gen_mgrs_tables.py` and the validator
`tools/validation/validate_mgrs.py` check them.

`fnc_worldToMgrs` and `fnc_mgrsToWorld` map a world position through the
anchor box. The box maps the world square linearly to the geographic box.
When no box exists, the kernel uses a local tangent plane at the anchor
centre.

### The geolocation migration

`fnc_getWorldLocation` now reads the latitude, the longitude and the zone from
`fnc_getGeoAnchor`. The return contract
`[latSignedTrue, magnitudeDeg, lonDeg, mapZone]` does not change.

### The anchor correction and its blast radius

The corrected anchor replaces the stale keys in `fnc_getWorldLocation`.
Fourteen call sites read the corrected values. They are the ballistics
Coriolis kernel, the maritime compass and sea-surface kernels, the
environmental astronomy, solar, milky-way, meteor, sky-log and space-weather
kernels, the two biome kernels, the world lighting kernel and the core init.

On Altis the Coriolis term moves by about 14 percent, the star altitude by
4.75 degrees and the solar noon by about 137 minutes. Every consumer keeps the
same return shape, so each reads a consistent, sign-corrected anchor. On a
world with no usable `mapArea[]` the values are unchanged.

### The tracker

Three pure kernels model the signal. `fnc_gnssErrorEllipse` returns the error
ellipse, the semi axes, the orientation, CEP and R95. `fnc_gnssFixState`
returns the fix quality, the time since the last fix, the re-acquisition
progress, the lag offset and the stutter envelope. `fnc_datalinkState` returns
the link state, the update interval, the track age and the added position
error.

`fnc_trackerProject` maps the three kernels onto an exact position and
returns the displayed position. The driver `fnc_trackerUpdate` reads
`group _player`, surveys the canopy, the urban cover and the terrain, calls
the three kernels and then the projector. It suppresses the engine friendly
map indicators with `disableMapIndicators [true, false, false, false]` where
the difficulty exposes extended map content.

### The per-constant register

Every new numeric is sourced, derived, or marked UNSOURCED. The table records
the register. The evidence holds the same register with the full detail.

| Kernel | Constant | Value | Source | Grade |
|---|---|---|---|---|
| UTM | semi-major a | 6378137 m | WGS84 (NIMA TR8350.2) | sourced |
| UTM | inverse flattening 1/f | 298.257223563 | WGS84 | sourced |
| UTM | scale factor k0 | 0.9996 | DMA TM 8358.2 | sourced |
| UTM | false easting | 500000 m | DMA TM 8358.2 | sourced |
| UTM | false northing south | 10000000 m | DMA TM 8358.2 | sourced |
| UTM | transverse Mercator series | forward and inverse | DMA TM 8358.2 | sourced |
| UTM | zone number from longitude | floor((lon+180)/6)+1 | DMA TM 8358.2 | sourced |
| UTM | zone clamp | 1 to 60 | UTM definition | derived |
| MGRS | latitude band letters | 8 degree steps | NGA MGRS 2009, TM 8358.1 | sourced |
| MGRS | band X height | 12 degrees | NGA MGRS 2009 | sourced |
| MGRS | column letter sets | 3 sets of 8 | NGA MGRS 2009, TM 8358.1 | sourced |
| MGRS | row letters | 20 rows | NGA MGRS 2009, TM 8358.1 | sourced |
| MGRS | even-zone row offset | 5 | NGA MGRS 2009, TM 8358.1 | sourced |
| MGRS | digits | truncated, south-west corner | NGA MGRS 2009 | sourced |
| MGRS | northing cycle | 2000000 m | NGA MGRS 2009 | sourced |
| MGRS | valid precision | 2, 4, 6, 8, 10 | NGA MGRS 2009 | sourced |
| world to MGRS | semi-major a, 1/f | WGS84 | WGS84 | sourced |
| world to MGRS | meridian radius M | a(1-e2)/(1-e2 sin2)^1.5 | WGS84 ellipsoid | derived |
| world to MGRS | longitude scale | cos(latitude) | local tangent plane | derived |
| world to MGRS | anchor-box mapping | linear | none | UNSOURCED |
| world to MGRS | tangent-plane fallback | none | none | UNSOURCED |
| GNSS ellipse | UERE | 3.6 m RMS | GPS SPS PS 5th ed | sourced |
| GNSS ellipse | accuracy at 95 percent | 8 m H, 13 m V | GPS SPS PS 5th ed | sourced |
| GNSS ellipse | vertical to horizontal ratio | 13/8 = 1.625 | derived from SPS | derived |
| GNSS ellipse | sigma | DOP x UERE | GPS SPS PS 5th ed | sourced |
| GNSS ellipse | R95 factor | 2.0 | GPS SPS PS 5th ed | sourced |
| GNSS ellipse | atmosphere gain | 0.5 per index | none | UNSOURCED |
| GNSS ellipse | canopy gain | 1.0 per fraction | none | UNSOURCED |
| GNSS ellipse | urban gain | 1.5 per fraction | none | UNSOURCED |
| GNSS ellipse | urban anisotropy | 2 | none | UNSOURCED |
| GNSS ellipse | jam gain | 20, on jammer^1.5 | none | UNSOURCED |
| GNSS ellipse | receiver penalty | 2 | none | UNSOURCED |
| GNSS ellipse | CEP coefficient | 0.589 | none | UNSOURCED |
| GNSS fix | continuity | availability then re-acquisition | GPS SPS PS 5th ed | sourced |
| GNSS fix | acquire floor | 0.3 | none | UNSOURCED |
| GNSS fix | re-acquisition rate | 0.25 per second | none | UNSOURCED |
| GNSS fix | decay rate | 1.0 per second | none | UNSOURCED |
| GNSS fix | jamming effect | removes the signal | none | UNSOURCED |
| GNSS fix | lag per second | 2 m | none | UNSOURCED |
| GNSS fix | lag at zero progress | 40 m | none | UNSOURCED |
| GNSS fix | stutter envelope | 0.5 | none | UNSOURCED |
| datalink | FSPL shape | 20log10(d)+20log10(f)-147.55 | Friis, from the radio module | derived |
| datalink | reference range | 5000 m | none | UNSOURCED |
| datalink | reference carrier | 3e8 Hz | none | UNSOURCED |
| datalink | terrain range fraction | 0.6 | none | UNSOURCED |
| datalink | urban range fraction | 0.3 | none | UNSOURCED |
| datalink | jamming range fraction | 0.9 | none | UNSOURCED |
| datalink | terrain loss | 12 dB | none | UNSOURCED |
| datalink | urban loss | 6 dB | none | UNSOURCED |
| datalink | jamming loss | 30 dB | none | UNSOURCED |
| datalink | base interval | 1.0 s | none | UNSOURCED |
| datalink | reference bandwidth | 100 | none | UNSOURCED |
| datalink | track age at zero signal | 30 s | none | UNSOURCED |
| datalink | error at zero signal | 25 m | none | UNSOURCED |
| datalink | lost-link error penalty | 15 m | none | UNSOURCED |
| tracker | error composition | R95 + datalink + lag | the three kernel outputs | derived |
| tracker | phase step | 137.508 degrees (golden angle) | none | UNSOURCED |
| tracker | displacement sum and bearing | none | none | UNSOURCED |
| tracker driver | humidity to atmosphere index | humidity / 100, default 50 | none | UNSOURCED |
| tracker driver | canopy probe height | +40 m vertical ray | none | UNSOURCED |
| tracker driver | urban survey radius | 50 m | none | UNSOURCED |
| tracker driver | urban saturation | 8 buildings | none | UNSOURCED |
| tracker driver | canopy signal gain | 0.5 per fraction | none | UNSOURCED |
| tracker driver | urban signal gain | 0.3 per fraction | none | UNSOURCED |
| tracker driver | DOP | 1.0 | none | UNSOURCED |
| tracker driver | receiver quality | 1.0 | none | UNSOURCED |
| anchor | mapArea element order | lon, lat pairs | BIS fn_posDegtoWorld.sqf | sourced |
| anchor | latitude sign inversion | positive is south | BIS CfgWorlds convention | sourced |
| anchor | fallback centre | 40 N, 0 E | prior reader fallback | UNSOURCED |

The register holds 69 constants. Twenty-three are sourced, 6 are derived and
40 are UNSOURCED. The register covers the pure kernels and the tracker driver
(`${PREFIX}optics_fnc_trackerUpdate`). The UNSOURCED group is the canopy, urban
and jamming gains, the fix lag and stutter, the datalink masks and losses, the
tracker phase step, the tracker driver sampling constants (the
humidity-to-atmosphere index, the canopy probe height, the urban survey radius
and saturation, the canopy and urban signal gains, the DOP and the receiver
quality) and the tangent-plane fallback. Each UNSOURCED shape is marked in its
kernel header and in the sensor value audit.

### The map grid overlay and the cursor readout

The engine map draws its own grid lines and labels them with numbers. The
`CfgWorlds` `Grid` class formats numbers only (`format = "XY"`, numeric
`formatX` and `formatY`), no script command writes it, and the override is a
config patch at load. So the engine lines cannot be relabelled in place. AEE
draws its own MGRS grid over them: the map control is hookable
(`findDisplay 12 displayCtrl 51`, `ctrlAddEventHandler ["Draw", ...]`), and
`drawLine` and `drawIcon` are valid on it. One pure kernel,
`fnc_mgrsGridLines`, plans the lines and their labels from the visible world
rectangle, reusing the core `worldToMgrs`, `utmToWorld` and `formatMgrs`
kernels. The interval follows the zoom.

The vanilla map cursor tooltip shows a six-figure grid and the elevation. It
is engine-side and no command or config field repoints it. AEE draws its own
readout adjacent to the cursor instead: `fnc_mgrsCursorText` joins the MGRS
reference and the terrain elevation, and the draw handler places it near the
cursor. The engine tooltip stays.

The map control is not fullscreen, so the visible rectangle comes from
`ctrlMapScreenToWorld` at the control corners (`ctrlPosition`), not from the
screen corners. The grid plan is cached on the rounded rectangle, so a static
map does not re-run the conversion on every draw.

## Alternatives rejected

- A second latitude read in the new code. It repeats the defect of issue #154.
- The stale `CfgWorlds` `latitude` and `longitude` keys as the primary source.
  Altis proves them wrong.
- A native MGRS map grid. The engine `Grid` class formats numbers only, with
  `format = "XY"`.
- A change to the vanilla GPS readout. `ItemGPS` is engine-hardcoded with no
  config surface.
- `setGroupIconsVisible` for the default engine markers. It affects only
  `addGroupIcon` High Command icons.
- An invented constant. A stated ceiling is honest and an invented value is
  not.

## Consequences and ceiling

- **No native MGRS.** Arma 3 has no MGRS. AEE shows MGRS on its own HUD
  readout, its map overlay and its marker labels. The vanilla GPS readout
  cannot change.
- **The map grid stays numeric.** The engine `CfgWorlds` `Grid` class formats
  numbers only. The grid lines cannot show a band letter or a 100 km letter.
  MGRS is a text overlay.
- **The marker suppression is partial.** `disableMapIndicators
  [true, false, false, false]` suppresses the engine friendly map indicators
  locally, and only where the difficulty exposes extended map content.
  `setGroupIconsVisible` affects only High Command `addGroupIcon` icons. The
  tracker is a model and an overlay regardless.
- **The anchor is an approximation.** It is a local tangent plane over the
  world square. On a 30 km world the error is small. The map is a flat square,
  so the model does not curve.
- **The correction reaches two worlds.** Only Altis and Malden ship a usable
  `mapArea[]`. Other worlds fall back to the stale `CfgWorlds` keys. Their
  geography is not corrected.
- **The visual rows are operator-only.** A headless server has no local
  player. The Docker probes test the pure kernels with fixtures. The visible
  HUD, map and marker result needs one operator run.
