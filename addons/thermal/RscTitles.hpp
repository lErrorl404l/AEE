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

    // ── The drawn fusion display (issue #204) ───────────────────────────────
    // The compass tape and the source's ECOTI box, ported from workshop
    // 3810296503 whale_ecoti_llll config.cpp \ RscTitles \
    // whale_ecoti_llll_overlay.  The source's box (ecoti_tint, idc 910001) is
    // restored as its four EDGES: a full panel fill tinted the sensor image
    // instead of showing the correct green phosphor, and a HUD aid must not
    // recolour the sensor image (operator report 2026-10-03).
    // The source declares style, font and sizeEx here because Arma has no
    // ctrlSetStyle command: a control created in script cannot be told to
    // centre its text, so the tape geometry only works when style = 2 is set
    // in config.  The per-frame drivers find the controls by idc and set only
    // position, text and colour.  The control base is local, so no engine
    // RscText class is needed (the same pattern as AEEFusionFrameBar).
    class GVAR(fusionHud) {
        idd = 10782;
        movingEnable = 0;
        enableSimulation = 0;
        enableDisplay = 1;
        onLoad = QUOTE(with uiNamespace do {GVAR(fusionHudDisplay) = _this select 0};);
        onUnload = QUOTE(with uiNamespace do {GVAR(fusionHudDisplay) = displayNull};);
        duration = 999999;
        fadein = 0;
        fadeout = 0;

        class controls {
            class AEEFusionHudText {
                type = 0;
                idc = -1;
                style = 0;
                shadow = 0;
                font = "EtelkaMonospaceProBold";
                sizeEx = 0.012;
                text = "";
                colorText[] = {1.00, 0.53, 0.27, 0.70};
                colorShadow[] = {0, 0, 0, 0};
                colorBackground[] = {0, 0, 0, 0};
                x = 0;
                y = 0;
                w = 0;
                h = 0.025;
            };

            // The source's ECOTI viewfinder box (whale_ecoti_llll config.cpp
            // ecoti_tint, idc 910001), drawn as its four EDGES so a full panel
            // fill cannot warm the green NVG (script_component.hpp
            // FUSION_BOX_COLOR).  FUNC(hudBoxDraw) sets each bar's position.
            class AEEFusionHudBox {
                type = 0;
                idc = -1;
                style = 0;
                shadow = 0;
                text = "";
                colorText[] = {0, 0, 0, 0};
                colorShadow[] = {0, 0, 0, 0};
                colorBackground[] = {0.55, 0.08, 0.05, 0.30};
                x = 0;
                y = 0;
                w = 0;
                h = 0;
            };
            class AEEFusionHudBoxTop: AEEFusionHudBox { idc = 910001; };
            class AEEFusionHudBoxBottom: AEEFusionHudBox { idc = 910002; };
            class AEEFusionHudBoxLeft: AEEFusionHudBox { idc = 910003; };
            class AEEFusionHudBoxRight: AEEFusionHudBox { idc = 910004; };

            // Left corner: grid and altitude.  Right corner: time.  Both are
            // repositioned inside the box by FUNC(hudTapeInfo).
            class AEEFusionHudInfo: AEEFusionHudText {
                idc = 920102;
                style = 0;
                sizeEx = 0.012;
                x = 0.02;
                y = 0.03;
                w = 0.45;
                h = 0.030;
            };
            class AEEFusionHudEnv: AEEFusionHudText {
                idc = 920103;
                style = 0;
                sizeEx = 0.012;
                x = 0.02;
                y = 0.07;
                w = 0.45;
                h = 0.030;
            };
            class AEEFusionHudClock: AEEFusionHudText {
                idc = 920101;
                style = 1;
                sizeEx = 0.012;
                x = 0.70;
                y = 0.03;
                w = 0.28;
                h = 0.030;
            };

            // Big heading number, full width and centred.
            class AEEFusionHudHeading: AEEFusionHudText {
                idc = 920001;
                style = 2;
                font = "EtelkaMonospaceProBold";
                sizeEx = 0.009;
                x = 0.0;
                y = 0.40;
                w = 1.0;
                h = 0.012;
                colorText[] = {1.00, 0.65, 0.15, 0.55};
            };
            // The fixed centre mark, a solid bar.
            class AEEFusionHudMark: AEEFusionHudText {
                idc = 920002;
                x = 0.5;
                y = 0.45;
                w = 0.0008;
                h = 0.006;
                colorText[] = {0, 0, 0, 0};
            };

            // Every 10 degrees, a three-digit label (13 of them).  Position and
            // text are set each frame by FUNC(hudTapeDraw).
            class AEEFusionHudLabel: AEEFusionHudText {
                style = 2;
                sizeEx = 0.006;
                x = 0.5;
                y = 0.44;
                w = 0.012;
                h = 0.008;
                colorText[] = {1.00, 0.65, 0.15, 0.55};
            };
            class AEEFusionHudLabel01: AEEFusionHudLabel { idc = 920011; };
            class AEEFusionHudLabel02: AEEFusionHudLabel { idc = 920012; };
            class AEEFusionHudLabel03: AEEFusionHudLabel { idc = 920013; };
            class AEEFusionHudLabel04: AEEFusionHudLabel { idc = 920014; };
            class AEEFusionHudLabel05: AEEFusionHudLabel { idc = 920015; };
            class AEEFusionHudLabel06: AEEFusionHudLabel { idc = 920016; };
            class AEEFusionHudLabel07: AEEFusionHudLabel { idc = 920017; };
            class AEEFusionHudLabel08: AEEFusionHudLabel { idc = 920018; };
            class AEEFusionHudLabel09: AEEFusionHudLabel { idc = 920019; };
            class AEEFusionHudLabel10: AEEFusionHudLabel { idc = 920020; };
            class AEEFusionHudLabel11: AEEFusionHudLabel { idc = 920021; };
            class AEEFusionHudLabel12: AEEFusionHudLabel { idc = 920022; };
            class AEEFusionHudLabel13: AEEFusionHudLabel { idc = 920023; };

            // Every 5 degrees, a tick bar (25 of them); the 10-degree ticks are
            // taller.  Position and height are set each frame.
            class AEEFusionHudTick: AEEFusionHudText {
                x = 0.5;
                y = 0.47;
                w = 0.0006;
                h = 0.003;
                colorText[] = {0, 0, 0, 0};
            };
            class AEEFusionHudTick01: AEEFusionHudTick { idc = 920031; };
            class AEEFusionHudTick02: AEEFusionHudTick { idc = 920032; };
            class AEEFusionHudTick03: AEEFusionHudTick { idc = 920033; };
            class AEEFusionHudTick04: AEEFusionHudTick { idc = 920034; };
            class AEEFusionHudTick05: AEEFusionHudTick { idc = 920035; };
            class AEEFusionHudTick06: AEEFusionHudTick { idc = 920036; };
            class AEEFusionHudTick07: AEEFusionHudTick { idc = 920037; };
            class AEEFusionHudTick08: AEEFusionHudTick { idc = 920038; };
            class AEEFusionHudTick09: AEEFusionHudTick { idc = 920039; };
            class AEEFusionHudTick10: AEEFusionHudTick { idc = 920040; };
            class AEEFusionHudTick11: AEEFusionHudTick { idc = 920041; };
            class AEEFusionHudTick12: AEEFusionHudTick { idc = 920042; };
            class AEEFusionHudTick13: AEEFusionHudTick { idc = 920043; };
            class AEEFusionHudTick14: AEEFusionHudTick { idc = 920044; };
            class AEEFusionHudTick15: AEEFusionHudTick { idc = 920045; };
            class AEEFusionHudTick16: AEEFusionHudTick { idc = 920046; };
            class AEEFusionHudTick17: AEEFusionHudTick { idc = 920047; };
            class AEEFusionHudTick18: AEEFusionHudTick { idc = 920048; };
            class AEEFusionHudTick19: AEEFusionHudTick { idc = 920049; };
            class AEEFusionHudTick20: AEEFusionHudTick { idc = 920050; };
            class AEEFusionHudTick21: AEEFusionHudTick { idc = 920051; };
            class AEEFusionHudTick22: AEEFusionHudTick { idc = 920052; };
            class AEEFusionHudTick23: AEEFusionHudTick { idc = 920053; };
            class AEEFusionHudTick24: AEEFusionHudTick { idc = 920054; };
            class AEEFusionHudTick25: AEEFusionHudTick { idc = 920055; };

            // The cardinal letters N / NE / E / SE / S / SW / W / NW, just
            // below the tick strip.  Their size and colour follow the tape.
            class AEEFusionHudDir: AEEFusionHudText {
                style = 2;
                sizeEx = 0.006;
                x = 0.5;
                y = 0.50;
                w = 0.012;
                h = 0.008;
                colorText[] = {1.00, 0.65, 0.15, 0.55};
            };
            class AEEFusionHudDir01: AEEFusionHudDir { idc = 920061; };
            class AEEFusionHudDir02: AEEFusionHudDir { idc = 920062; };
            class AEEFusionHudDir03: AEEFusionHudDir { idc = 920063; };
            class AEEFusionHudDir04: AEEFusionHudDir { idc = 920064; };
            class AEEFusionHudDir05: AEEFusionHudDir { idc = 920065; };
            class AEEFusionHudDir06: AEEFusionHudDir { idc = 920066; };
            class AEEFusionHudDir07: AEEFusionHudDir { idc = 920067; };
            class AEEFusionHudDir08: AEEFusionHudDir { idc = 920068; };
        };
    };
};
