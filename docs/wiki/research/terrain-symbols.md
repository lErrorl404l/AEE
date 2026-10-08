# Terrain and map-feature symbol source register

Read-only record of the standards behind the AEE map terrain layer. The
terrain kernels and the generators read this register. No code changed to
produce it.

- Repo: AEE. The register cites public sources only and embeds no local path.
- Method: the DGIWG and ASSIST records, the FM 21-31 and USGS public-domain
  descriptions, and the local MIL-STD-2525D copy.
- Every row carries a grade. A **sourced** row is a published value. A
  **derived** row follows the standard's described shape with AEE-chosen
  coordinates. An **UNSOURCED** row is a model choice that no source supports.

The unit symbols already follow NATO APP-6. Terrain is a different standard
family. APP-6 does not cover natural ground, so this register uses the
topographic standard.

## 1. Standards

| Standard | Edition | Date | Status | Licence | Grade | Source |
|---|---|---|---|---|---|---|
| STANAG 3675 | Edition 2 | 15 June 2000 | Being retired; DGIWG succeeds it | Distribution-controlled; do not ship the document | sourced | `https://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=97059` |
| DGIWG Symbol Register | current | live portal | Live successor to STANAG 3675 | Graphics terms UNKNOWN; draw the geometry | sourced | `https://portal.dgiwg.org/public_dgiwg/portrayal/sdl.php` |
| DGIWG 252-3 DTM50 | current | DGIWG standard | Defence Topographic Map product | DGIWG standard | sourced | `https://portal.dgiwg.org/files/73419` |
| DGIWG 130 Web Symbology | current | DGIWG standard | Web portrayal product | DGIWG standard | sourced | `https://dgiwg.org/documents/dgiwg-standards` |
| FM 21-31 | 19 June 1961, Change 1 31 December 1968 | 1961 | US Army field manual | US Government work, public domain | sourced | `https://www.globalsecurity.org/military/library/policy/army/fm/21-31/index.html` |
| FM 3-25.26 | 2005 | 2005 | US Army field manual | US Government work, public domain | sourced | `https://archive.org/details/Fm32526MAPREADINGANDLANDNAVIGATION` |
| TM 5-248 | 1946, reprinted 1956 | 1946 | US Army technical manual | US Government work, public domain | sourced | `https://digitalcommons.unl.edu/usarmyfieldmanuals/56/` |
| USGS Topographic Map Symbols | GIP, 4 pages | 2005 | US civil sheet | US Government work, public domain | sourced | `https://pubs.usgs.gov/gip/TopographicMapSymbols/` |
| MIL-DTL-89045 GeoSym | Rev A, Am 1 2009 | 2007 | NGA digital display symbols | US Government work, public domain | sourced | `https://everyspec.com/MIL-SPECS/MIL-SPECS-MIL-DTL/MIL-DTL-89045A_14251/` |
| STANAG 2211 | Edition 7 | 2016 | Geodetic datums, projections, grids | Not the terrain standard | sourced | `https://nisp.nw3.dk/standard/nato-ageop-21-ed.a-v1.html` |

The terrain symbol authority is STANAG 3675, succeeded by the DGIWG Symbol
Register with the DTM50 product. STANAG 2211 fixes the coordinate frame. It
defines no terrain symbol. APP-6 and MIL-STD-2525 define units, equipment and
military obstacles. They do not define natural terrain.

## 2. FM 21-31 section vocabulary

| Section | Feature group | Contents | Grade | Source |
|---|---|---|---|---|
| 9 | Drainage | Perennial, intermittent, dry, wash. Rivers, streams, lakes, ponds, marshes, swamps. | sourced | FM 21-31 |
| 10 | Relief | Contours (index, intermediate, supplementary), form lines, hachures, hill shading. Spot heights. | sourced | FM 21-31 |
| 11 | Vegetation | Woodland, deciduous, coniferous, brushwood, orchards, vineyards. | sourced | FM 21-31 |
| 12 | Coastal hydrography | Foreshore, depths, rocks, wrecks, navigational marks. | sourced | FM 21-31 |
| 13 | Roads, US | Hard-surface heavy and medium duty, improved light duty, dirt, trails. | sourced | FM 21-31 |
| 14 | Roads, foreign | All-weather, loose surface, tracks, trails. | sourced | FM 21-31 |
| 15 | Roads, small scale | Dual highways, main, secondary, other roads. | sourced | FM 21-31 |
| 16 | Related road features | Tunnels, cuttings, embankments. | sourced | FM 21-31 |
| 17 | Railroads | Normal, broad and narrow gage. Multiple track, dismantled, electrified. | sourced | FM 21-31 |
| 18 | Crossings | Overpasses, underpasses, bridges, viaducts, drawbridges, ferries, fords. | sourced | FM 21-31 |
| 19 | Buildings and places, large scale | Built-up areas, buildings, schools, churches, ruins. | sourced | FM 21-31 |
| 20 | Buildings and places, small scale | Place circles, tinted areas, name type sizes. | sourced | FM 21-31 |
| 21 | Industrial and public works | Factories, works, power and public structures. | sourced | FM 21-31 |
| 22 | Control points and elevations | Triangulation points, spot heights, benchmarks. | sourced | FM 21-31 |
| 23 | Boundaries | International, provincial and administrative. | sourced | FM 21-31 |

The operator's named features map as follows. Radio towers and masts fall
under industrial and public works, and under the DGIWG DTM communications
point symbols. Trees fall under vegetation. Hills and mountains fall under
relief.

## 3. Geometry rules

The symbols are point, line or area, chosen by the size and extent of the
feature. USGS states this directly.

| Rule | Grade | Source |
|---|---|---|
| A contour joins points of equal elevation above a datum. | sourced | FM 21-31 section 10 |
| Every fifth contour is heavier. It is the index contour. | sourced | FM 21-31 section 10 |
| Supplementary half-interval contours are added where the interval is too large. | sourced | FM 21-31 section 10 |
| Hachures show promontories where data do not support contours. | sourced | FM 21-31 section 10 |
| Relief lines print in brown at large and medium scale. | sourced | FM 21-31 section 10 |
| Only perennial growth is mapped. | sourced | FM 21-31 section 11 |
| The continuous-cover symbol means 20 to 35 percent canopy. | sourced | FM 21-31 section 11 |
| A bridge passes over water. A viaduct passes over land. | sourced | FM 21-31 section 18 |
| Road class is by load and all-weather use, not by appearance. | sourced | FM 21-31 section 13 |
| Relief is drawn as contours, form lines, hachures and shading. It is not one glyph. | sourced | FM 21-31 section 10 |
| The AEE icon geometry is a vector approximation of the described shape. | derived | AEE |

## 4. Licence table

| Source | Licence | Reuse in AEE | Grade |
|---|---|---|---|
| STANAG 3675 | Distribution-controlled | Do not ship the document | sourced |
| DGIWG Symbol Register | Graphics terms UNKNOWN | Draw the standard geometry; ship no graphic | sourced |
| FM 21-31, FM 3-25.26, TM 5-248 | US public domain | Free | sourced |
| USGS Topographic Map Symbols | US public domain | Free | sourced |
| MIL-DTL-89045 GeoSym | US public domain | Free | sourced |
| Ordnance Survey | Crown copyright, OGL v3 for open data | Attribution for open data | sourced |
| IHO S-4 and ICAO Annex 4 | Purchased | Not used | sourced |

The symbol designs are a standard, not an artwork. AEE draws the standard's
geometry from the public-domain descriptions. No restricted document and no
third-party graphic ships.

## 5. The engine surfaces and the ceilings

| Surface | Config path | Override | Engine ceiling |
|---|---|---|---|
| Location symbols | `CfgLocationTypes >> <type>` | Load-time re-declare | `drawStyle` is a fixed engine enum |
| Object map icons | `RscMapControl >> <object>` | Load-time re-declare | The object-to-icon routing is engine-internal (BI ticket T157884) |
| Contours | `RscMapControl >> color*` | Load-time re-declare | The contour geometry and interval are engine-derived |
| Roads, rail, power | `RscMapControl >> color*` | Load-time re-declare | The geometry is a SHP file and terrain data |
| Fills and satellite | `RscMapControl >> color*`, `maxSatelliteAlpha` | Load-time re-declare | The satellite texture is baked into the map data layers |

WHY each ceiling holds. The engine owns the draw routine, so a mod changes the
texture, colour, size, font, shadow and importance, not the drawing behaviour.
The object routing has no config surface, so a re-texture reaches only the
objects the engine already routes to a class. The contours come from the WRP
elevation data, so the interval is not a config field. The road geometry lives
in the map PBO. The satellite texture is baked into the data layers, so only
its opacity is a surface.

## 6. Reconciliation with APP-6

Terrain is a separate family from APP-6. Terrain is not drawn as an APP-6
frame. An APP-6 frame is a unit or equipment symbol. The terrain layer is a
load-time config re-declare of the engine location and object classes. The
APP-6 marker layer, the `CfgMarkers` block, the MGRS overlay and the world
`Names` are unchanged.

## 7. Map colour palette

The palette follows the USGS and FM 21-31 standard. The values are RGBA in the
range 0 to 1. `data/symbology/terrain_symbols.json` holds them and
`addons/optics/config_mapcolors.hpp` applies them.

| Field | RGBA | Meaning | Grade |
|---|---|---|---|
| `colorLevels` | 0.70, 0.48, 0.32, 1 | relief level line, brown | derived |
| `colorCountlines` | 0.70, 0.48, 0.32, 1 | intermediate contour, brown | derived |
| `colorMainCountlines` | 0.55, 0.35, 0.20, 1 | index contour, darker brown | derived |
| `colorMainCountlinesWater` | 0.00, 0.50, 0.75, 1 | water contour, blue | derived |
| `colorCountlinesWater` | 0.30, 0.60, 0.80, 1 | water contour, light blue | derived |
| `colorRoads` | 0.80, 0.10, 0.10, 1 | road, red | derived |
| `colorRoadsFill` | 0.95, 0.90, 0.80, 1 | road fill, cream | derived |
| `colorMainRoads` | 0.70, 0.00, 0.00, 1 | main road, dark red | derived |
| `colorMainRoadsFill` | 0.95, 0.90, 0.80, 1 | main road fill, cream | derived |
| `colorRailWay` | 0.00, 0.00, 0.00, 1 | railway, black | derived |
| `colorPowerLines` | 0.00, 0.00, 0.00, 1 | power line, black | derived |
| `colorTracks` | 0.40, 0.30, 0.20, 1 | track, brown | derived |
| `colorTracksFill` | 0.90, 0.85, 0.75, 1 | track fill, sand | derived |
| `colorTrails` | 0.40, 0.30, 0.20, 1 | trail, brown | derived |
| `colorTrailsFill` | 0.90, 0.85, 0.75, 1 | trail fill, sand | derived |
| `colorSea` | 0.55, 0.70, 0.85, 1 | sea, light blue | derived |
| `colorForest` | 0.65, 0.80, 0.60, 1 | forest, light green | derived |
| `colorForestBorder` | 0.00, 0.50, 0.00, 1 | forest border, green | derived |
| `colorRocks` | 0.75, 0.70, 0.60, 1 | rock, tan | derived |
| `colorRocksBorder` | 0.50, 0.45, 0.40, 1 | rock border, grey | derived |
| `colorBackground` | 0.90, 0.88, 0.80, 1 | map ground, paper | derived |

Two display levers are model choices with no standard. `maxSatelliteAlpha`
(0.35) fades the baked satellite texture so the vector linework reads.
`showCountourInterval` (1) shows the contour interval label. Both carry the
UNSOURCED grade.

## 8. Eden and Zeus surfaces

Eden and Zeus carry the layer through the shared map control and two extra
targets. The evidence is the shipped `ui_f_curator` and `3den` configs.

| Surface | Config path | Reached by | Grade |
|---|---|---|---|
| In-game and briefing map | `RscDisplayMainMap >> CA_Map` | one `RscMapControl` re-declare | sourced |
| Strategic map | `RscDisplayStrategicMap >> controlsBackground >> Map` | separate target | sourced |
| GPS and airborne minimap | `RscCustomInfoMiniMap` | `RscMapControl` (overrides some colours) | sourced |
| Zeus map | `RscDisplayCurator >> Map` | `RscMapControl` | sourced |
| Zeus entity icons | `CfgCurator >> DrawGroup >> texture*` | separate `CfgCurator` re-declare | sourced |
| Eden map | `Display3DEN >> Map: ctrlMap` | separate `ctrlMap` re-declare | sourced |
| Location and object symbols | `CfgLocationTypes`, `RscMapControl` | class lookup, reaches every map | sourced |

The engine ceiling: the Zeus unit and group tree rows are engine-filled from
the object class, the Eden asset-browser rows follow
`CfgVehicles >> editorPreview`, and the Zeus side-filter colours read the
profile variables `Map_*_R/G/B`, not `CfgMarkerColors`. A mod cannot set a
single tree row icon. WHY: the row fill is engine-internal.

## 9. Unknowns

- The exact UK military map-symbol publication number: UNKNOWN.
- The DGIWG Symbol Register graphics licence terms: UNKNOWN. Verify before
  shipping a graphic. AEE draws the geometry instead.
- The full DTM50 vegetation, water and relief symbol id list: not transcribed
  here. It is in the register.
