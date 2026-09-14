class RscPicture;

// RscText needs a FULL base definition, not a forward declaration.  An
// empty parent class gives the control no type, so it never renders (the
// focus HUD was invisible for exactly this reason).  Definition mirrors
// FPANO ECOTI's working HUD (workshop 3725008325) and the vanilla default.
class RscText {
    type = 0;
    idc = -1;
    style = 0;
    shadow = 1;
    font = "PuristaMedium";
    sizeEx = "0.02 * safezoneH";
    colorText[] = {1, 1, 1, 1};
    colorBackground[] = {0, 0, 0, 0};
};

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
            // Focus readout below the tube face (ECOTI HUD style, verified
            // from FPANO ECOTI workshop source): the focus ring position as
            // a distance in metres plus a scale bar.  Real NVGs have no
            // readout - the operator reads the ring markings - but a game
            // needs to show the value the physics is using.  The bar spans
            // 0-100 m (log display, dominated by the 0-25 m patrol band)
            // with a tick at the current focus.
            class NVGFocusText: RscText {
                idc = 1002;
                text = "FOCUS 15m";
                style = 2;   // centre-aligned
                shadow = 1;
                font = "PuristaMedium";
                sizeEx = "0.014 * safezoneH";
                // WHITE, not green: the engine tints the whole NVG view
                // green (phosphor screen), so a green readout is invisible
                // against it.  White stands out on the dark tube face.
                colorText[] = {1, 1, 1, 1};
                // Inside the tube face, bottom CENTRE of the screen.  The
                // mask occupies safeZoneY..safeZoneY+safeZoneH centred on
                // the screen width, so a control spanning the tube width
                // with centre style sits unambiguously at the bottom-centre.
                x = "safeZoneX + (safeZoneW - safeZoneH) / 2 - safeZoneH * 0.17";
                y = "safeZoneY + safeZoneH * 0.88";
                w = "safeZoneH * 0.34";
                h = "0.020 * safezoneH";
            };
            class NVGFocusBar: RscText {
                idc = 1003;
                text = "|----o----------------------|";
                style = 2;   // centre-aligned
                shadow = 1;
                font = "PuristaMedium";
                sizeEx = "0.012 * safezoneH";
                colorText[] = {1, 1, 1, 0.8};
                x = "safeZoneX + (safeZoneW - safeZoneH) / 2 - safeZoneH * 0.17";
                y = "safeZoneY + safeZoneH * 0.90";
                w = "safeZoneH * 0.34";
                h = "0.018 * safezoneH";
            };
        };
    };
};
