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
 * the strategic map (RscDisplayStrategicMap >> controlsBackground >> Map) and
 * the Eden editor map (Display3DEN >> Map, the ctrlMap class, NOT
 * RscMapControl).  Each re-declares the SAME topographic surface as
 * RscMapControl, from config_mapcolors.hpp, so the palette, the shading
 * levers and the grid contract reach the main map, the strategic map and the
 * Eden map alike.  A target that re-declares a field wins for that display.
 *
 * Engine ceiling: the minimap overrides maxSatelliteAlpha, alphaFade*, the
 * ptsPerSquare* densities, colorSea, colorForest and drawShaded, so the
 * minimap keeps its own sea and forest fill and its satellite fade.
 */
class RscDisplayStrategicMap {
    class controlsBackground {
        class Map {
#include "config_mapcolors.hpp"
            // Engine numeric LINES off, engine NUMBERS on (ADR-029).
            colorGrid[] = {0, 0, 0, 0};
            colorGridMap[] = {0, 0, 0, 0};
            sizeExGrid = 0.02;
        };
    };
};

// The Eden editor map.  ctrlMap is the Eden map class, not RscMapControl.
// ctrlMapMain and ctrlMapEmpty inherit ctrlMap, so this reaches them.
class ctrlDefault;
class ctrlMap: ctrlDefault {
#include "config_mapcolors.hpp"
    // Engine numeric LINES off, engine NUMBERS on (ADR-029).
    colorGrid[] = {0, 0, 0, 0};
    colorGridMap[] = {0, 0, 0, 0};
    sizeExGrid = 0.02;
};
