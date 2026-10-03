// The fusion thermal-channel frame (issue #204, Track B ENVG-B).
//
// A thin rectangular border at the resolved thermal half-angle, drawn over
// the NVG view.  It is a HUD aid and NOT optics: no mask, no border that
// implies an optical edge the renderer cannot produce, no tube geometry.
// The thermal fusion path owns this display and drives the four bars each
// tick from FUNC(fusionFrameGeometry).
//
// The control base is local to this display, so no class name clashes with
// another addon's RscText.  RscMapControl is an engine class; the forward
// declaration makes it visible to the config parser (whale_ecoti_llll does
// the same).
class RscMapControl;

class RscTitles {

    // The fusion outline canvas (issue #204).  A full-screen transparent map
    // control; the outline is drawn on it with the Draw event handler and
    // drawLine (see addons/thermal/functions/outline/fnc_outlineCanvas.sqf).
    // The technique is copied from workshop 3811605241 whale_ecoti_llll
    // config.cpp, which declares the same RscMapControl base.
    class GVAR(fusionOutline) {
        idd = 10780;
        movingEnable = 0;
        enableSimulation = 0;
        enableDisplay = 1;
        onLoad = QUOTE(with uiNamespace do {GVAR(outlineDisplay) = _this select 0};);
        duration = 999999;
        fadein = 0;
        fadeout = 0;
        class controls {
            class AEEOutlineCanvas: RscMapControl {
                idc = 1301;
                x = "safeZoneX";
                y = "safeZoneY";
                w = "safeZoneW";
                h = "safeZoneH";
                fade = 1;
                showMarkers = 0;
                drawObjects = 0;
                moveOnEdges = 0;
                maxSatelliteAlpha = 0;
                alphaFadeStartScale = 0;
                alphaFadeEndScale = 0;
                showCountourInterval = 0;
                scaleMin = 0.0001;
                scaleMax = 1;
                scaleDefault = 0.001;
                colorBackground[] = {0, 0, 0, 0};
                colorOutside[] = {0, 0, 0, 0};
                colorSea[] = {0, 0, 0, 0};
                colorText[] = {0, 0, 0, 0};
                colorLevels[] = {0, 0, 0, 0};
                colorCountlines[] = {0, 0, 0, 0};
                colorMainCountlines[] = {0, 0, 0, 0};
                colorCountlinesWater[] = {0, 0, 0, 0};
                colorMainCountlinesWater[] = {0, 0, 0, 0};
                colorForest[] = {0, 0, 0, 0};
                colorForestBorder[] = {0, 0, 0, 0};
                colorRocks[] = {0, 0, 0, 0};
                colorRocksBorder[] = {0, 0, 0, 0};
                colorPowerLines[] = {0, 0, 0, 0};
                colorRailWay[] = {0, 0, 0, 0};
                colorNames[] = {0, 0, 0, 0};
                colorInactive[] = {0, 0, 0, 0};
                colorTracks[] = {0, 0, 0, 0};
                colorTracksFill[] = {0, 0, 0, 0};
                colorRoads[] = {0, 0, 0, 0};
                colorRoadsFill[] = {0, 0, 0, 0};
                colorMainRoads[] = {0, 0, 0, 0};
                colorMainRoadsFill[] = {0, 0, 0, 0};
                colorGrid[] = {0, 0, 0, 0};
                colorGridMap[] = {0, 0, 0, 0};
                colorTrails[] = {0, 0, 0, 0};
                colorTrailsFill[] = {0, 0, 0, 0};
            };
        };
    };

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
