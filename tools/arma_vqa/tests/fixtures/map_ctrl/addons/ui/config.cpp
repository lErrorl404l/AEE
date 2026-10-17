class CfgPatches { class ui { units[] = {}; }; };
class RscControlsGroup;
class RscMapControl;

// REAL-WORLD: ACE3 addons/map/config.cpp - overrides on the top-level class (must stay silent)
class RscMapControl {
    maxSatelliteAlpha = 0.5;
    colorTracks[] = {0.2,0.13,0,1};
    colorRoads[] = {0.2,0.13,0,1};
    colorMainRoads[] = {0.0,0.0,0.0,1};
    colorGrid[] = {0.05,0.1,0,0.6};
    colorGridMap[] = {0.05,0.1,0,0.4};
    colorBackground[] = {0.929412, 0.929412, 0.929412, 1.0};
    colorOutside[] = {0.929412, 0.929412, 0.929412, 1.0};
    colorLevels[] = {0.0, 0.0, 0.0, 1.0};
    sizeExLevel = 0.03;
    showCountourInterval = 1; // the engine's own (mis)spelling
    sizeExGrid = 0.032;
};

// REAL-WORLD: ACE3 microdagr mini map - scaleMax 10 and an alpha fade at 100 are shipped and fine
class RscDisplayDagr {
    class controls {
        class MapPlain: RscMapControl {
            scaleMin = 0.005;
            scaleMax = 10;
            maxSatelliteAlpha = 0;
            alphaFadeStartScale = 100;
            alphaFadeEndScale = 100;
            colorGrid[] = {0,0,0,0.15};
            colorGridMap[] = {0,0,0,0.2};
        };
    };
};

// REAL-WORLD: ACE3 fcs / laser - an invisible helper map control inside an IGUI controls group (info only)
class RscInGameUI {
    class Group_UI {
        class CA_IGUI_elements_group: RscControlsGroup {
            class controls {
                class Rangehelper: RscMapControl { idc = -1; w = 0; h = 0; };
            };
        };
    };
};

class RscDisplayBadMap {
    class controls {
        class BadColours: RscMapControl {
            colorGrid[] = {0.1, 0.1, 0.1, 1.5};
            colorGridMap[] = {0, 0, 0};
            colorSea[] = {-0.2, 0.4, 0.6, 1};
        };
        class Invisible: RscMapControl {
            colorGrid[] = {0, 0, 0, 0};
            sizeExGrid = 0;
        };
        class TinyNumbers: RscMapControl { sizeExGrid = 0.004; };
        class WrongScales: RscMapControl {
            scaleMin = 0.5;
            scaleDefault = 0.2;
            scaleMax = 0.1;
            maxSatelliteAlpha = 2;
        };
        class Typos: RscMapControl {
            showContourInterval = 1;
            colorSee[] = {0.1, 0.2, 0.3, 1};
            onDraw = "";
            idc = 51;
        };
    };
};
