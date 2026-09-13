class RscPicture;

class RscTitles {
    class GVAR(nvgTitle) {
        idd = 10778;
        movingEnable = 0;
        enableSimulation = 1;
        enableDisplay = 1;
        onLoad = QUOTE(with uiNamespace do {GVAR(titleDisplay) = _this select 0};);
        duration = 999999;
        fadein = 0;
        fadeout = 0;
        class controls {
            // Fiber-optic bundle faceplate ("chicken wire") for Gen 1/2.
            // Same square geometry as the mask; texture + alpha set per
            // tier in SQF.  Cell size is measurement-based: Gen 1 bundles
            // ~3.6 % of tube, Gen 2 ~2.4 % (SCHOTT faceplate datasheets,
            // multi-fiber bundle boundaries 0.5-1 mm on an 18 mm tube).
            // Defined BEFORE the mask so the mask renders on top: its
            // transparent centre reveals the fibers inside the tube, its
            // opaque ring covers them outside.
            class NVGFibers: RscPicture {
                idc = 1001;
                text = QPATHTOF(data\nvg_fibers_gen1_1024.paa);
                x = "safeZoneX + (safeZoneW - safeZoneH) / 2";
                y = "safeZoneY";
                w = "safeZoneH";
                h = "safeZoneH";
            };
            // Circular tube face: opaque black outside the circle hides the
            // scene; transparent inside lets the engine's NVG render show
            // through.  The overlay is a SQUARE sized to safeZoneH — the
            // tube face is round, not stretched to the full screen.  X is
            // centred so the circle is not elliptical.
            class NVGMask: RscPicture {
                idc = 1000;
                text = QPATHTOF(data\nvg_mask_2048.paa);
                x = "safeZoneX + (safeZoneW - safeZoneH) / 2";
                y = "safeZoneY";
                w = "safeZoneH";
                h = "safeZoneH";
            };
        };
    };
};
