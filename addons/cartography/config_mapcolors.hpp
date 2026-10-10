/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * The map colour palette and the topographic render surface
 * (RscMapControl re-declare).
 *
 * This file holds the render fields only.  It opens no class.  config.cpp
 * includes it inside the RscMapControl block, and config_mapdisplays.hpp
 * includes it inside the strategic map and Eden map blocks, so the same
 * surface reaches every map display.  It sets every reachable map-rendering
 * field the engine exposes, so the map reads as a topographic sheet and not a
 * satellite picture.
 *
 * Each value names its source.  The authorities are:
 *   USGS  USGS Topographic Map Symbols, unnumbered series GIP (2005), public
 *         domain.
 *   FM    US Army FM 21-31 Topographic Symbols (1961, Change 1 1968), public
 *         domain.
 *   DGIWG DGIWG Symbol Register (DTM50 / DGIWG 252-3), succeeding
 *         STANAG 3675.  Holds the water blue and the vegetation green.
 *   ENG   the shipped RscMapControl default, read from the engine config
 *         (`bin_raw/bin/config.cpp:20117`, `ui_f_x2/config.cpp:1272`).  Used
 *         where no topographic standard fixes the value.
 *   IDEA  adopted from the IDEAS of Enhanced Map (2467589125) and BHC Map
 *         Contour (1364777346).  No mod value, config or texture is copied.
 *
 * tools/tests/test_terrain.py pins the palette, the scalars and the fonts to
 * data/symbology/terrain_symbols.json.  Engine ceilings are in ADR-030.
 */

    // ── Paper and the void ───────────────────────────────────────────────
    // The map ground and the margin outside the world.  FM s9; USGS.
    colorBackground[] = {0.90, 0.88, 0.80, 1};
    colorOutside[] = {0.90, 0.88, 0.80, 1};
    // The inactive marker tint.  ENG.
    colorInactive[] = {1, 1, 1, 0.5};

    // ── Water shading.  DGIWG water blue. ───────────────────────────────
    colorSea[] = {0.55, 0.70, 0.85, 1};
    colorMainCountlinesWater[] = {0.00, 0.50, 0.75, 1};
    colorCountlinesWater[] = {0.30, 0.60, 0.80, 1};
    // Coordinates the sea texture density.  ENG.
    ptsPerSquareSea = 5;

    // ── Relief bands.  Hypsometric tint, relief brown.  FM s10. ─────────
    colorLevels[] = {0.70, 0.48, 0.32, 1};

    // ── Contours.  Index dark, intermediate mid.  FM s10; USGS "index
    // contours are heavier".  Both darkened so the lines read against the
    // light ground.  The published OS contour-family RGBs (Terrain 50
    // #E0945E, Zoomstack Outdoor #857660) are lighter, so these are AEE's own
    // darker brown representation of the standard's brown.
    colorMainCountlines[] = {0.45, 0.26, 0.12, 1};
    colorCountlines[] = {0.62, 0.42, 0.22, 1};
    // The contour elevation label.  ENG field, AEE label family.
    fontLevel = "RobotoCondensed";
    // The contour elevation (height) label size.  Doubled from the vanilla
    // 0.02, which the operator reports as too small to read.
    sizeExLevel = 0.04;
    // Coordinates the contour line density.  ENG.
    ptsPerSquareCLn = 10;

    // ── Vegetation and rock tints.  FM s11; DGIWG green. ────────────────
    colorForest[] = {0.55, 0.74, 0.44, 1};
    colorForestBorder[] = {0.00, 0.50, 0.00, 1};
    // The tint over the baked vegetation texture.  A green tint at 30% makes
    // the raster read as vegetation, where alpha 0 left it untinted.  OS
    // MasterMap woodland fill #cee6bd is the published reference.
    colorForestTextured[] = {0.45, 0.66, 0.34, 0.30};
    colorRocks[] = {0.75, 0.70, 0.60, 1};
    colorRocksBorder[] = {0.50, 0.45, 0.40, 1};
    // Coordinates the forest and the rock density.  ENG.
    ptsPerSquareFor = 9;
    ptsPerSquareForEdge = 9;
    // The forest density at the two coarse LODs.  The engine Eden map
    // (3den.pbo ctrlMap) sets these; AEE adopts the engine values (vanilla
    // parity).  Source: 3den.pbo.
    ptsPerSquareForLod1 = 4;
    ptsPerSquareForLod2 = 1;

    // ── Roads, rail, power, tracks and trails.  FM s13 to s18. ──────────
    colorRoads[] = {0.80, 0.10, 0.10, 1};
    colorRoadsFill[] = {0.95, 0.90, 0.80, 1};
    colorMainRoads[] = {0.70, 0.00, 0.00, 1};
    colorMainRoadsFill[] = {0.95, 0.90, 0.80, 1};
    colorRailWay[] = {0.00, 0.00, 0.00, 1};
    colorPowerLines[] = {0.00, 0.00, 0.00, 1};
    colorTracks[] = {0.40, 0.30, 0.20, 1};
    colorTracksFill[] = {0.90, 0.85, 0.75, 1};
    colorTrails[] = {0.40, 0.30, 0.20, 1};
    colorTrailsFill[] = {0.90, 0.85, 0.75, 1};
    // The rail line width and the road density.  ENG.
    widthRailWay = 4;
    ptsPerSquareRoad = 6;
    // The main-road and the simple-variant road densities.  The engine Eden
    // map (3den.pbo ctrlMap) sets these; AEE adopts the engine values.
    ptsPerSquareMainRoad = 6;
    ptsPerSquareRoadSimple = 1;
    ptsPerSquareMainRoadSimple = 1;

    // ── Labels and object icons.  FM s19, s20; USGS. ────────────────────
    colorNames[] = {0.10, 0.10, 0.10, 0.90};
    // Coordinates the label and the object icon density.  ENG.
    ptsPerSquareTxt = 20;
    ptsPerSquareObj = 9;
    // The object icon density at LOD1.  The engine minimap (ui_f.pbo) sets
    // this; AEE adopts the engine value.  Source: ui_f.pbo minimap.
    ptsPerSquareObjLod1 = 2;

    // ── Display levers.  IDEA; engrave the hillshade and the satellite. ──
    // maxSatelliteAlpha 0.5: AEE's own, between the old 0.35 and the Enhanced
    // Map 1.0, so the satellite reads while the MGRS linework stays legible.
    // drawShaded 0.15 and shadedSea 1: the Enhanced Map hillshade idea, for
    // the topographic relief.  drawShaded is a real RscMapControl field
    // (ui_f_x2/config.cpp:50344).
    maxSatelliteAlpha = 0.5;
    drawShaded = 0.15;
    shadedSea = 1;
    // The contour interval label is shown.  ENG.
    showCountourInterval = 1;
    // The satellite fade scales.  ENG.
    alphaFadeStartScale = 2;
    alphaFadeEndScale = 2;

    // ── Zoom range.  The map zooms out further. ──────────────────────────
    // scaleMax 2: AEE's own, double the vanilla zoom-out limit of 1.
    // UNSOURCED (AEE model choice; no standard fixes the limit).
    scaleMax = 2;
    // scaleDefault 0.3: the engine strategic-map scale (ui_f.pbo
    // RscDisplayStrategicMap Map), so the map opens at the overview zoom.
    scaleDefault = 0.3;
