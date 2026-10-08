/* SPDX-License-Identifier: GPL-2.0-or-later */
/*
 * The map display reconciliation.
 *
 * One RscMapControl re-declare reaches every display that inherits it: the
 * main map (RscDisplayMainMap, IDC 51), the briefing, the GPS and minimap
 * (RscCustomInfoMiniMap, IDC 101), the airborne minimap, the Zeus map
 * (RscDisplayCurator, IDC 50), the Zeus attribute map and the spectator.
 *
 * Two displays carry their own control and are SEPARATE override targets:
 * the strategic map (RscDisplayStrategicMap >> controlsBackground >> Map,
 * an RscMapControl that re-declares its colours) and the Eden editor map
 * (Display3DEN >> Map, which is the ctrlMap class, NOT RscMapControl, so an
 * RscMapControl re-declare does not reach Eden).  This file re-declares the
 * standard palette, the label font and the display levers on those two
 * targets so the palette is consistent.
 *
 * The engine ceiling: a display that re-declares a field wins for that
 * display.  The minimap overrides maxSatelliteAlpha, alphaFade*, the
 * ptsPerSquare* densities, colorSea, colorForest and drawShaded, so the
 * minimap keeps its own sea and forest fill and its satellite fade.
 */
class RscDisplayStrategicMap {
    class controlsBackground {
        class Map {
            colorLevels[] = {0.70, 0.48, 0.32, 1};
            colorMainCountlines[] = {0.55, 0.35, 0.20, 1};
            colorCountlines[] = {0.70, 0.48, 0.32, 1};
            colorRoads[] = {0.80, 0.10, 0.10, 1};
            colorMainRoads[] = {0.70, 0.00, 0.00, 1};
            colorSea[] = {0.55, 0.70, 0.85, 1};
            colorForest[] = {0.65, 0.80, 0.60, 1};
        };
    };
};

// The Eden editor map.  ctrlMap is the Eden map class, not RscMapControl.
// ctrlMapMain and ctrlMapEmpty inherit ctrlMap, so this reaches them.
class ctrlDefault;
class ctrlMap: ctrlDefault {
    colorLevels[] = {0.70, 0.48, 0.32, 1};
    colorMainCountlines[] = {0.55, 0.35, 0.20, 1};
    colorCountlines[] = {0.70, 0.48, 0.32, 1};
    colorMainCountlinesWater[] = {0.00, 0.50, 0.75, 1};
    colorCountlinesWater[] = {0.30, 0.60, 0.80, 1};
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
    colorSea[] = {0.55, 0.70, 0.85, 1};
    colorForest[] = {0.65, 0.80, 0.60, 1};
    colorForestBorder[] = {0.00, 0.50, 0.00, 1};
    colorRocks[] = {0.75, 0.70, 0.60, 1};
    colorRocksBorder[] = {0.50, 0.45, 0.40, 1};
    colorBackground[] = {0.90, 0.88, 0.80, 1};
    fontGrid = "AEEFont";
    fontNames = "AEEFont";
    maxSatelliteAlpha = 0.35;
    showCountourInterval = 1;
};
