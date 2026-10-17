class CfgPatches { class badmod_terrain { units[] = {}; weapons[] = {}; requiredVersion = 0.1; }; };
class RscMapControl;
class CfgWorlds {
    class badmod_island {
        mapSize = 12800;
        gridNumbersOverLines = 1;
        class Grid {
            offsetX = 0;
            offsetY = 0;                       // should be the map size: the Y numbers go negative (MAP001)
            class Zoom1 { zoomMax = 0.15; format = "XY"; formatX = "00"; formatY = "00"; stepX = 100; stepY = -100; };   // 128 cells need 3 digits (MAP002)
            class Zoom2 { zoomMax = 0.1; format = "XY"; formatX = "00"; formatY = "00"; stepX = 1000; stepY = -1000; };  // out of order (MAP003)
        };
    };
};
class RscDisplayBadmodMap {
    class controls {
        class Map: RscMapControl {
            colorGrid[] = {0.9, 0.9, 0.9, 0.1};     // pale grid on a pale map: nearly invisible (MAPSIM001)
            colorBackground[] = {0.93, 0.93, 0.93, 1};
            colorSea[] = {0.7, 0.8, 0.9, 1.4};      // alpha out of range (MAPUI001)
            showContourInterval = 1;                // the engine spells it showCountourInterval (MAPUI004)
            scaleMin = 1;
            scaleMax = 0.1;                         // MAPUI003
        };
    };
};
