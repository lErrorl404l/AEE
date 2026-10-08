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
 * data/symbology/terrain_symbols.json.  Engine ceilings are in ADR-029.
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

    // ── Contours.  Index dark, intermediate light.  FM s10. ─────────────
    colorMainCountlines[] = {0.55, 0.35, 0.20, 1};
    colorCountlines[] = {0.70, 0.48, 0.32, 1};
    // The contour elevation label.  ENG field, AEE label family.
    fontLevel = "RobotoCondensed";
    sizeExLevel = 0.02;
    // Coordinates the contour line density.  ENG.
    ptsPerSquareCLn = 10;

    // ── Vegetation and rock tints.  FM s11; DGIWG green. ────────────────
    colorForest[] = {0.65, 0.80, 0.60, 1};
    colorForestBorder[] = {0.00, 0.50, 0.00, 1};
    // The tint over the baked vegetation texture; alpha 0 lets it read.  ENG.
    colorForestTextured[] = {0.00, 0.50, 0.00, 0.00};
    colorRocks[] = {0.75, 0.70, 0.60, 1};
    colorRocksBorder[] = {0.50, 0.45, 0.40, 1};
    // Coordinates the forest and the rock density.  ENG.
    ptsPerSquareFor = 9;
    ptsPerSquareForEdge = 9;

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

    // ── Labels and object icons.  FM s19, s20; USGS. ────────────────────
    colorNames[] = {0.10, 0.10, 0.10, 0.90};
    // Coordinates the label and the object icon density.  ENG.
    ptsPerSquareTxt = 20;
    ptsPerSquareObj = 9;

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
