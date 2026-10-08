/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * The map colour palette (RscMapControl re-declare).
 *
 * This file is included INSIDE the RscMapControl block in config.cpp.  It does
 * not open a second RscMapControl class.
 *
 * The palette follows the USGS and FM 21-31 standard: relief brown, water
 * blue, vegetation green, roads red and white, built-up areas black.  Each
 * value is generated from data/symbology/terrain_symbols.json and locked by
 * tools/tests/test_terrain.py.
 *
 * Engine ceiling: the contour geometry and interval are engine-derived.  The
 * interval is not a config field.  showCountourInterval toggles the interval
 * label.  The road, rail and satellite geometry is terrain data, so the
 * colours are the only surface.  maxSatelliteAlpha fades the baked satellite
 * texture so the vector linework reads; the value is a model choice with no
 * standard.
 */

    // Contours.  Relief prints brown.  FM 21-31 s10.
    colorLevels[] = {0.70, 0.48, 0.32, 1};
    colorMainCountlines[] = {0.55, 0.35, 0.20, 1};
    colorCountlines[] = {0.70, 0.48, 0.32, 1};
    colorMainCountlinesWater[] = {0.00, 0.50, 0.75, 1};
    colorCountlinesWater[] = {0.30, 0.60, 0.80, 1};

    // Roads, rail, power, tracks and trails.  FM 21-31 s13 to s18.
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

    // Ground and water fills.  FM 21-31 s9 to s12.
    colorSea[] = {0.55, 0.70, 0.85, 1};
    colorForest[] = {0.65, 0.80, 0.60, 1};
    colorForestBorder[] = {0.00, 0.50, 0.00, 1};
    colorRocks[] = {0.75, 0.70, 0.60, 1};
    colorRocksBorder[] = {0.50, 0.45, 0.40, 1};
    colorBackground[] = {0.90, 0.88, 0.80, 1};

    // Display levers.  maxSatelliteAlpha fades the satellite; the contour
    // interval label is shown.  Both are model choices with no standard.
    maxSatelliteAlpha = 0.35;
    showCountourInterval = 1;
