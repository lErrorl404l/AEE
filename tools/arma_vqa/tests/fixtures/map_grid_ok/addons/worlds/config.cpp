// Grid classes copied in structure from real, working community configs:
//  * "abc_sample"  - BI forum 'config.cpp' terrain thread / pastebin EDBYDjjL (zoomMax 1e+030.0 on the last class)
//  * "vr_like"     - VR values from the BIS_fnc_gridToPos thread (offsetY 8192)
//  * "pmc_40k"     - PMC editing wiki real-world-data tutorial (4096 x 10 m = 40960 m, four zoom levels, 4-digit finest)
class CfgPatches { class worlds { units[] = {}; }; };
class CfgWorlds {
    class abc_sample {
        mapSize = 5120;
        centerPosition[] = {2560, 2560, 500};
        class Grid {
            offsetX = 0;
            offsetY = 5120;
            class Zoom1 { zoomMax = 0.15; format = "XY"; formatX = "000"; formatY = "000"; stepX = 100; stepY = -100; };
            class Zoom2 { zoomMax = 0.85; format = "XY"; formatX = "00"; formatY = "00"; stepX = 1000; stepY = -1000; };
            class Zoom3 { zoomMax = 1e+030.0; format = "XY"; formatX = "0"; formatY = "0"; stepX = 10000; stepY = -10000; };
        };
    };
    class vr_like {
        mapSize = 8192;
        class Grid {
            offsetX = 0;
            offsetY = 8192;
            class Zoom1 { zoomMax = 0.15; format = "XY"; formatX = "000"; formatY = "000"; stepX = 100; stepY = -100; };
            class Zoom2 { zoomMax = 0.85; format = "XY"; formatX = "00"; formatY = "00"; stepX = 1000; stepY = -1000; };
            class Zoom3 { zoomMax = 1; format = "XY"; formatX = "0"; formatY = "0"; stepX = 10000; stepY = -10000; };
        };
    };
    class pmc_40k {
        mapSize = 40960;
        centerPosition[] = {20480, 20480};
        gridNumbersOverLines = 1;
        class Grid {
            offsetX = 0;
            offsetY = 40960; // Grid * Cell
            class Zoom1 { zoomMax = 0.015; format = "XY"; formatX = "0000"; formatY = "0000"; stepX = 10; stepY = -10; };
            class Zoom2 { zoomMax = 0.2; format = "XY"; formatX = "000"; formatY = "000"; stepX = 100; stepY = -100; };
            class Zoom3 { zoomMax = 0.8; format = "XY"; formatX = "00"; formatY = "00"; stepX = 1000; stepY = -1000; };
            class Zoom4 { zoomMax = 1; format = "XY"; formatX = "0"; formatY = "0"; stepX = 10000; stepY = -10000; };
        };
    };
    // REAL-WORLD (Kunduz in the BI forum thread): inherits everything, only moves the origin
    class kunduz_like: abc_sample {
        mapSize = 5120;
        class Grid: Grid {
            offsetX = 0;
            offsetY = 5120;
            class Zoom1: Zoom1 {};
            class Zoom2: Zoom2 {};
            class Zoom3: Zoom3 {};
        };
    };
};
