// The fusion thermal-channel frame (issue #204, Track B ENVG-B).
//
// A thin rectangular border at the resolved thermal half-angle, drawn over
// the NVG view.  It is a HUD aid and NOT optics: no mask, no border that
// implies an optical edge the renderer cannot produce, no tube geometry.
// The thermal fusion path owns this display and drives the four bars each
// tick from FUNC(fusionFrameGeometry).
//
// The control base is local to this display, so no class name clashes with
// another addon's RscText.
class RscTitles {
    class GVAR(fusionFrame) {
        idd = 10779;
        movingEnable = 0;
        enableSimulation = 0;
        enableDisplay = 1;
        onLoad = QUOTE(with uiNamespace do {GVAR(fusionFrameDisplay) = _this select 0};);
        duration = 999999;
        fadein = 0;
        fadeout = 0;
        class controls {
            class AEEFusionFrameBar {
                type = 0;
                idc = -1;
                style = 0;
                shadow = 0;
                font = "PuristaMedium";
                sizeEx = "0.02 * safezoneH";
                text = "";
                // White stands out on the green-phosphor NVG base.
                colorText[] = {0, 0, 0, 0};
                colorBackground[] = {1, 1, 1, 0.55};
                x = 0;
                y = 0;
                w = 0;
                h = 0;
            };
            class AEEFusionFrameTop: AEEFusionFrameBar {
                idc = 1101;
            };
            class AEEFusionFrameBottom: AEEFusionFrameBar {
                idc = 1102;
            };
            class AEEFusionFrameLeft: AEEFusionFrameBar {
                idc = 1103;
            };
            class AEEFusionFrameRight: AEEFusionFrameBar {
                idc = 1104;
            };
        };
    };
};
