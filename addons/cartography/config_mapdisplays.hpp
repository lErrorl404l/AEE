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
 * minimap keeps its own sea and forest fill and its satellite fade.  AEE
 * re-declares the minimap CA_MiniMap below for the fields the engine does not
 * force, from config_mapminimap.hpp; that file names every unreachable field.
 */
class RscDisplayStrategicMap {
    class controlsBackground {
        class Map {
#include "config_mapcolors.hpp"
            // The engine grid fields are off.  The engine edge ruler clips its
            // left and right numbers at close zoom and cannot be kept without
            // doubling the AEE ruler, so the AEE MGRS overlay is the single
            // complete ruler: lines and four-edge numbers.
            colorGrid[] = {0, 0, 0, 0};
            colorGridMap[] = {0, 0, 0, 0};
            sizeExGrid = 0.04;
        };
    };
};

// The Eden editor map.  ctrlMap is the Eden map class, not RscMapControl.
// ctrlMapMain and ctrlMapEmpty inherit ctrlMap, so this reaches them.
class ctrlDefault;
class ctrlMap: ctrlDefault {
#include "config_mapcolors.hpp"
    // The engine grid fields are off; the AEE MGRS overlay is the single
    // complete ruler (see config.cpp).
    colorGrid[] = {0, 0, 0, 0};
    colorGridMap[] = {0, 0, 0, 0};
    sizeExGrid = 0.04;
};

// The minimap control.  The engine ui_f CA_MiniMap forces part of the palette
// (config_mapminimap.hpp names every unreachable field), so AEE re-declares the
// control for the fields the engine does not force.  The airborne minimap
// inherits this control and adds its own forced overrides.
class RscCustomInfoMiniMap {
    class controls {
        class MiniMap: RscControlsGroupNoScrollbars {
            class Controls {
                class CA_MiniMap: RscMapControl {
#include "config_mapminimap.hpp"
                };
            };
        };
    };
};
class RscCustomInfoAirborneMiniMap: RscCustomInfoMiniMap {
    class controls: controls {
        class MiniMap: MiniMap {
            class Controls: Controls {
                class CA_MiniMap: CA_MiniMap {
#include "config_mapminimap.hpp"
                };
            };
        };
    };
};
