/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * The AEE topographic surface for the minimap controls.  The engine minimap
 * (RscCustomInfoMiniMap) and the airborne minimap (RscCustomInfoAirborneMiniMap)
 * each declare their own CA_MiniMap and OVERRIDE part of the palette, so AEE
 * re-declares the fields the engine does not force, in config_mapdisplays.hpp.
 * Every value is the same as config_mapcolors.hpp, so the minimap and the main
 * map read one source; tools/tests/test_map_qa.py pins the two files together.
 *
 * The engine forces these fields on the minimap; AEE cannot reach them and the
 * engine override wins (a ceiling, read from the derapified ui_f config):
 *   colorBackground, colorSea, colorForest, colorForestBorder, colorRocks,
 *   colorRocksBorder, colorLevels, colorMainCountlines, colorCountlines,
 *   colorMainCountlinesWater, colorCountlinesWater, colorPowerLines,
 *   colorRailWay, colorTracks, colorTracksFill, colorRoads, colorRoadsFill,
 *   colorMainRoads, colorMainRoadsFill, colorGrid, colorGridMap,
 *   maxSatelliteAlpha, alphaFadeStartScale, alphaFadeEndScale, drawShaded,
 *   showCountourInterval, moveOnEdges, textureCompass, compassPos,
 *   compassSize, ptsPerSquareTxt, ptsPerSquareFor, ptsPerSquareForEdge,
 *   ptsPerSquareRoad, ptsPerSquareMainRoad, ptsPerSquareObj,
 *   ptsPerSquareObjLod1, ptsPerSquareForLod1, ptsPerSquareForLod2,
 *   ptsPerSquareRoadSimple, ptsPerSquareMainRoadSimple.
 * The airborne minimap additionally forces drawShaded, colorSea, colorForest,
 * colorPowerLines, widthPowerLines and the altitude ramp.  AEE does not force
 * the zoom range (scaleMax, scaleDefault) on the minimap.
 */

    colorOutside[] = {0.90, 0.88, 0.80, 1};
    colorInactive[] = {1, 1, 1, 0.5};
    fontLevel = "RobotoCondensed";
    // Doubled from the vanilla 0.02, which the operator reports as too small.
    sizeExLevel = 0.04;
    ptsPerSquareCLn = 10;
    ptsPerSquareSea = 5;
    // OS MasterMap woodland fill #cee6bd is the published reference.
    colorForestTextured[] = {0.45, 0.66, 0.34, 0.30};
    colorTrails[] = {0.40, 0.30, 0.20, 1};
    colorTrailsFill[] = {0.90, 0.85, 0.75, 1};
    widthRailWay = 4;
    colorNames[] = {0.10, 0.10, 0.10, 1};
    shadedSea = 1;
