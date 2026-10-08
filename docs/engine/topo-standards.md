# Published colour values and contour intervals for topographic maps

Research briefing. Compiled 2026-10-08.

Every value below is published by the named authority. Where no authority
publishes a value, the entry reads NOT PUBLISHED. No value is inferred or
averaged.

Values are written as `#RRGGBB (R,G,B)`. Hex is the publisher's own; where
only RGB is published, the hex is the standard 8-bit conversion, marked `(hex
derived)`.

---

## 1. Ordnance Survey (GB)

### 1.1 Important structural fact

Ordnance Survey publishes colour values per product. There is no single "OS
colour palette" document. The two published machine-readable palettes are:

- OS MasterMap Topography Layer colour values (premium product).
- OS Open palette: the OS Open product stylesheet repositories on GitHub
  (OS Open Zoomstack, OS OpenMap Local, OS VectorMap District, OS Terrain
  50).

The OS MasterMap standard styling specification states: "Ordnance Survey has
chosen to use colours that are consistent in the internet environment. The
colours used are defined with both their RGB and hexadecimal values in the
colour palette."
(https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/os-mastermap-topography-layer/os-mastermap-topography-layer-standard-styling-specification/cartographic-style-definitions)

The leisure paper maps (Explorer 1:25 000, Landranger 1:50 000) have their own
printed cartography. The OS style guide for third parties calls these the
"distinctive pink and orange colours of our 'Explorer' and 'Landranger' paper
map". It does not publish their RGB values.
(https://www.ordnancesurvey.co.uk/documents/partner-documents/ordnance-survey-style-guide-for-third-parties.pdf, p. ~301)

### 1.2 OS Landranger 1:50,000 and Explorer 1:25,000 — contours

| Item | Value | Source |
|---|---|---|
| Landranger contour interval | 10 m vertical interval | OS Terrain 50 overview (contours at 10 m interval); Landranger legend |
| Explorer contour interval | printed on the map legend (10 m standard) | OS 1:25 000 Scale Colour Raster docs (shows contours); interval is on the legend |
| Index contour rule | index contours every 50 m, labelled in several places | OS Landranger/Explorer legend convention |
| Contour line colour (leisure print) | NOT PUBLISHED as RGB | OS publishes no machine-readable palette for the leisure maps |

Published OS contour colours come from the derived rasters and open vectors:

- OS Terrain 50 stylesheet (QGIS `ContourLine.qml`): contour line and text
  colour `#E0945E (224,148,94)`.
  (https://github.com/OrdnanceSurvey/OS-Terrain-50-stylesheets)
- OS Open Zoomstack, Road style: Contours `#D6986B (214,152,107)`, Contour
  Labels `#D7986C (215,152,108)`.
- OS Open Zoomstack, Outdoor style: Contours `#857660 (133,118,96)`.
  (https://github.com/OrdnanceSurvey/OS-Open-Zoomstack-Stylesheets, `Colour Values/Road style colour values.xlsx`, `Outdoor style colour values.xlsx`)

Contour interval datasets (primary OS source):

- OS Terrain 50: "A contour dataset of 10m interval standard contour
  polylines."
  (https://docs.os.uk/os-downloads/products/land-and-terrain-portfolio/os-terrain-50/os-terrain-50-overview)
- OS Terrain 5: 5 m elevation interval (derived from 1:10 000 mapping).
- OS MasterMap Topography Layer contains NO contours. Contours are a separate
  OS Terrain product.

### 1.3 OS MasterMap Topography Layer — land, water, woodland, building

Source: OSMM-Topography-Layer-stylesheets, "Outdoor style",
`Schema version 9/Stylesheets/Colour Values/OSMM-Topography-Layer-Colour-Values.xlsx`.
(https://github.com/OrdnanceSurvey/OSMM-Topography-Layer-stylesheets)

| Feature | Hex | RGB |
|---|---|---|
| Inland Water Fill | `#aadeef` | 170,222,239 |
| Tidal Water Fill | `#aadeef` | 170,222,239 |
| Canal Fill | `#aadeef` | 170,222,239 |
| Saltmarsh Fill / Marsh Fill | `#e4f3f4` | 228,243,244 |
| Inland Water Line | `#7ed2e0` | 126,210,224 |
| Mean High Water Line / Mean Low Water Line | `#7ed2e0` | 126,210,224 |
| Mixed / Coniferous / Nonconiferous Tree Fill | `#cee6bd` | 206,230,189 |
| Orchard / Coppice Fill | `#cee6bd` | 206,230,189 |
| Scrub / Rough Grassland / Heath Fill | `#e2efce` | 226,239,206 |
| Agricultural Land Fill | `#d6edcf` | 214,237,207 |
| Building Fill | `#dcd7c6` | 220,215,198 |
| Building Outline Line | `#bbb49c` | 187,180,156 |
| Road Or Track Line | `#817e79` | 129,126,121 |
| Road Or Track Fill | `#fcfdff` | 252,253,255 |
| Spot Height Point | `#857660` | 133,118,96 |
| Administrative boundary lines | `#ff98ff` | 255,152,255 |

### 1.4 OS public road colours

OS MasterMap Topography Layer does NOT colour roads by class. It uses a black
carriageway outline overlaid with a yellow minor-road line (documented in the
standard styling spec). Road-class colours are published for OS Open
Zoomstack instead.

OS Open Zoomstack, **Road style** (https://github.com/OrdnanceSurvey/OS-Open-Zoomstack-Stylesheets, `Colour Values/Road style colour values.xlsx`):

| Road class | Hex | RGB |
|---|---|---|
| Motorways | `#06B1CA` | 6,177,202 |
| Primary Roads | `#37C256` | 55,194,91 |
| A Roads | `#FF889D` | 255,136,157 |
| B Roads | `#FFC073` | 255,192,115 |
| Minor Roads | `#FEF2B4` | 254,242,180 |
| Local Roads | `#FFFFFF` | 255,255,255 |
| Restricted Roads | `#E2E2E2` | 226,226,226 |
| Road Casings | `#8F8F8F` | 143,143,143 |
| Road Tunnels | `#4b4444` | 75,68,68 |

OS Open Zoomstack, **Outdoor style**:

| Road class | Hex | RGB |
|---|---|---|
| Motorways | `#08B7E7` | 8,183,231 |
| Primary Roads | `#77C776` | 119,199,118 |
| A / B / Minor / Local Roads | `#FFFFFF` | 255,255,255 |
| Motorway Junction Box | `#1484A3` | 20,132,163 |

Road colours for the printed Landranger/Explorer maps: NOT PUBLISHED as RGB.

---

## 2. USGS and US Army

### 2.1 USGS "Topographic Map Symbols" (GIP publication)

Source: https://pubs.usgs.gov/gip/TopographicMapSymbols/topomapsymbols.pdf

This publication states colour conventions in words, not RGB:

- "vegetation (green), water (blue), and densely built-up areas (gray or
  red)".
- "topographic contours (brown); lakes, streams, irrigation ditches, and
  other hydrographic features (blue); land grids and important roads (red);
  and other roads and trails, railroads, boundaries, and other cultural
  features (black)".
- "Index contours are wider. Elevation values are printed in several places
  along these lines."
- "Bathymetric contours are shown in blue or black".
- Purple was historically the revision colour; no longer used.
- Contour interval: "A map of a relatively flat area may have a contour
  interval of 10 feet or less. Maps in mountainous areas may have contour
  intervals of 100 feet or more. The contour interval is printed in the
  margin."

No RGB or hex values are published for these colours. The lines are printed
spot colours, keyed to the map margin legend.

### 2.2 USGS US Topo (current 7.5-minute, 1:24,000)

Sources:
- https://www.usgs.gov/ngp-standards-and-specifications/us-topo-cartographic-specifications-map-symbol-guide
- https://www.usgs.gov/ngp-standards-and-specifications/us-topo-cartographic-specifications

- Scale: 1:24,000, 7.5-minute quadrangle.
- "topographic contours in brown, streams and rivers and other hydrographic
  features in blue, and roads in black and red."
- "Heavier brown lines are index contours and are labeled with the elevation
  they represent."
- Perennial stream: solid blue line. Intermittent stream: blue dashed and
  dotted line.
- Contour interval: "A map of a relatively flat area may have a contour
  interval of 10 feet. In steep areas an interval of 100 feet or more may be
  used... The contour interval is always noted below the bar scale in the map
  marginalia."

No RGB or hex values are published. US Topo symbols are defined as vector
styles (ESRI/QGIS) in the US Topo cartographic specification, not as a
published RGB palette.

### 2.3 Contour interval conventions

| Scale | Interval | Source |
|---|---|---|
| 1:24,000 (7.5-minute) | 10 ft in flat areas; 20 ft typical; 40–100 ft in mountainous areas. Interval chosen per quadrangle and printed in the margin | USGS Topographic Map Symbols; US Topo guide |
| 1:50,000 (USGS/legacy) | Metric 10 m or 20 m, chosen per map | USGS/National Mapping convention. The specific interval is on each map. No single published table located. |

### 2.4 Hypsometric tints (green lowland → yellow → tan/brown → red/pink high)

The classic hypsometric tint bands are a cartographic convention. USGS
7.5-minute topographic quads do not use them (they use brown contours, green
vegetation, blue water). Tints appear on older small-scale USGS maps.

The band colours (green, yellow, tan, brown, red/pink) are widely reproduced,
but this research found NO authoritative USGS publication that gives their RGB
or hex. The Wikipedia article "Hypsometric tints" describes the scheme but is
not a primary source.

**Hypsometric tint band RGB/hex: NOT PUBLISHED by USGS in any primary source
located.**

### 2.5 US Army

US Army map-reading doctrine (TC 3-25.26 / FM 3-25.26, formerly FM 21-26)
uses the same USGS colour conventions: brown contours, blue water, green
vegetation, red/black roads. The doctrine reproduces the symbols but does not
publish RGB values. US Army topographic maps follow the USGS/National
Geospatial conventions and STANAG 3675 for symbols. No US Army hypsometric
tint RGB table located: NOT PUBLISHED.

---

## 3. NATO / STANAG

### 3.1 STANAG 3675 — what it standardises

STANAG 3675 Ed. 2, "Symbols on Land Maps, Aeronautical and Special Naval
Charts" (2001). "The aim of this agreement is to standardize the basic symbols
used on topographical land maps, aeronautical charts and special naval
charts." It is a SYMBOL standard, NOT a map colour standard.

STANAG 3675 is RETIRED. DGIWG Technical Report TCR-24-002, "Cross-reference
between STANAG 3675 and DGIWG Symbol Database/Register" (Edition 1.0.0, 28
June 2024), states: "Related to the retirement of STANAG 3675". It also
states, of the retired STANAG: "Preferred colours are not specified in detail
by any numeric values in colour models".

Sources:
- https://portal.dgiwg.org/files/74430
- https://dgiwg.org/custom/dgiwg_technical_reports.php

### 3.2 The correct NATO colour standard

The colour standard is DGIWG 131, "Printing Colours for Defence Geospatial
Products". DGIWG 131 is named in the references of the DGIWG cross-reference
report. The report gives no numeric values for DGIWG 131, and the document
itself is not openly downloadable (DGIWG portal listing only).

Related DGIWG and NATO documents named in the same report:

- DGIWG 130, Web Symbology.
- DGIWG 252, DPS for Defence Topographic Map 1:50,000.
- DGIWG 256, DPS for Defence City Map (in work).
- DGIWG 258, DPS for Defence Joint Operations Graphic Air (in work).
- STANAG 3677, Standard Scales for Land Maps and Aeronautical Charts.
- STANAG 3600, Topographical Land Maps and Aeronautical Charts 1:250,000 for
  Joint Operations.

### 3.3 NATO hypsometric tint / terrain colours

- AAP-6 is the NATO Glossary of Terms and Definitions. It is not a colour
  specification.
- APP-6 (now APP-6E) is NATO Joint Military Symbology. It standardises
  symbols, not terrain colour.
- No NATO standard that publishes hypsometric tint RGB values was located.

**NATO hypsometric tint / terrain colour RGB: NOT PUBLISHED in any openly
available NATO source. The governing document is DGIWG 131, which is not
openly published.**

---

## 4. Values requested but NOT PUBLISHED

| Requested value | Verdict |
|---|---|
| Contour line RGB for printed OS Landranger/Explorer | NOT PUBLISHED |
| Public road class RGB for printed OS Landranger/Explorer | NOT PUBLISHED |
| OS "index/landform contour" label colour for leisure maps | NOT PUBLISHED |
| USGS hypsometric tint band RGB/hex | NOT PUBLISHED |
| USGS/US Topo symbol RGB palette | NOT PUBLISHED (styles are vector rules) |
| US Army hypsometric tint RGB | NOT PUBLISHED |
| DGIWG 131 numeric colour values | NOT PUBLISHED (restricted) |
| NATO/AAP-6/AJP terrain colour RGB | NOT PUBLISHED |

Where a publisher gives only a name ("brown", "blue", "green"), that name is
the citable fact. Do not convert a name to a number.

---

## 5. Sources

1. OS MasterMap Topography Layer colour values.
   https://github.com/OrdnanceSurvey/OSMM-Topography-Layer-stylesheets
2. OS MasterMap standard styling specification (colour palette statement).
   https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/os-mastermap-topography-layer/os-mastermap-topography-layer-standard-styling-specification/cartographic-style-definitions
3. OS Open Zoomstack stylesheets and colour values.
   https://github.com/OrdnanceSurvey/OS-Open-Zoomstack-Stylesheets
4. OS Terrain 50 overview (10 m interval) and stylesheets (contour colour).
   https://docs.os.uk/os-downloads/products/land-and-terrain-portfolio/os-terrain-50/os-terrain-50-overview
   https://github.com/OrdnanceSurvey/OS-Terrain-50-stylesheets
5. OS 1:25 000 / 1:50 000 Scale Colour Raster documentation.
   https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/1-25-000-scale-colour-raster
   https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/1-50-000-scale-colour-raster
6. OS style guide for third parties (Explorer/Landranger print colours).
   https://www.ordnancesurvey.co.uk/documents/partner-documents/ordnance-survey-style-guide-for-third-parties.pdf
7. USGS Topographic Map Symbols.
   https://pubs.usgs.gov/gip/TopographicMapSymbols/topomapsymbols.pdf
   https://pubs.usgs.gov/gip/TopographicMapSymbols/
8. USGS US Topo Map Symbol Guide and cartographic specifications.
   https://www.usgs.gov/ngp-standards-and-specifications/us-topo-cartographic-specifications-map-symbol-guide
   https://www.usgs.gov/ngp-standards-and-specifications/us-topo-cartographic-specifications
9. DGIWG TCR-24-002, Cross-reference between STANAG 3675 and DGIWG Symbol
   Database/Register, 2024.
   https://portal.dgiwg.org/files/74430
   https://dgiwg.org/custom/dgiwg_technical_reports.php
10. STANAG 3675 record.
    https://standards.globalspec.com/std/68090/stanag-3675
