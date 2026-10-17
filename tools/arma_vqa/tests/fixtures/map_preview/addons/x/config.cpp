class RscMapControl {
    colorBackground[] = {0.93, 0.93, 0.93, 1};
    colorSea[] = {0.47, 0.63, 0.85, 0.5};
    colorForest[] = {0.6, 0.8, 0.2, 0.25};
    colorGrid[] = {0.05, 0.1, 0, 0.6};
    colorGridMap[] = {0.05, 0.1, 0, 0.4};
    sizeExGrid = 0.032;
};
class PaleGrid: RscMapControl {
    colorBackground[] = {0.95, 0.95, 0.95, 1};
    colorGrid[] = {0.9, 0.9, 0.9, 0.12};
};
class CfgWorlds {
    class preview_world {
        mapSize = 5120;
        class Grid {
            offsetX = 0;
            offsetY = 5120;
            class Zoom1 { zoomMax = 0.15; format = "XY"; formatX = "000"; formatY = "000"; stepX = 100; stepY = -100; };
            class Zoom2 { zoomMax = 1; format = "XY"; formatX = "00"; formatY = "00"; stepX = 1000; stepY = -1000; };
        };
    };
};
