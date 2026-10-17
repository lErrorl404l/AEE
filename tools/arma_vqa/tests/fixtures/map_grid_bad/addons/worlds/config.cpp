class CfgWorlds {
    // offsetY forgotten: the Y numbers run from -50 at the south edge
    class no_offset {
        mapSize = 5120;
        class Grid {
            offsetX = 0;
            offsetY = 0;
            class Zoom1 { zoomMax = 0.15; format = "XY"; formatX = "000"; formatY = "000"; stepX = 100; stepY = -100; };
            class Zoom2 { zoomMax = 1; format = "XY"; formatX = "00"; formatY = "00"; stepX = 1000; stepY = -1000; };
        };
    };
    // 102400 m map with 100 m cells needs 4 digits (0..1023) but the format has 3
    class too_big {
        mapSize = 102400;
        class Grid {
            offsetX = 0;
            offsetY = 102400;
            class Zoom1 { zoomMax = 0.15; format = "XY"; formatX = "000"; formatY = "000"; stepX = 100; stepY = -100; };
            class Zoom2 { zoomMax = 1; format = "XY"; formatX = "00"; formatY = "00"; stepX = 1000; stepY = -1000; };
        };
    };
    // zoom classes in the wrong order; steps that do not nest; widest class stops short of 1
    class messy {
        mapSize = 10240;
        centerPosition[] = {20000, 20000};
        gridNumbersOverLines = 2;
        mapArea[] = {0, 0, 1, 1};
        class Grid {
            offsetX = 0;
            offsetY = 10240;
            class Zoom1 { zoomMax = 0.5; format = "XY"; formatX = "000"; formatY = "000"; stepX = 100; stepY = -100; };
            class Zoom2 { zoomMax = 0.2; format = "XY"; formatX = "00"; formatY = "00"; stepX = 250; stepY = -250; };
        };
    };
    // bad steps and an incomplete class
    class broken_steps {
        mapSize = 5120;
        class Grid {
            offsetX = 0;
            offsetY = 5120;
            class Zoom1 { zoomMax = 0.15; format = "XY"; formatX = "000"; formatY = "000"; stepX = -100; stepY = 0; };
            class Zoom2 { zoomMax = 1; formatX = "00"; stepX = 1000; stepY = 1000; };
        };
    };
};
